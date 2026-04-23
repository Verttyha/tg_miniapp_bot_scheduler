from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.core.security import TokenCipher
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import (
    AttendanceRecord,
    AttendanceStatus,
    Event,
    EventParticipant,
    EventStatus,
    ExternalEventMapping,
    NotificationKind,
    SyncStatus,
    User,
    WorkspaceMember,
)
from scheduler_app.domain.schemas import AttendanceUpdateRequest, EventCreateRequest, EventUpdateRequest
from scheduler_app.services.common import ConflictError, NotFoundError, ensure_admin, get_workspace_member
from scheduler_app.services.integrations import IntegrationService
from scheduler_app.services.notifications import NotificationService


class EventService:
    def __init__(self, session: AsyncSession, settings: Settings, cipher: TokenCipher):
        self.session = session
        self.settings = settings
        self.integration_service = IntegrationService(session, settings, cipher)
        self.notification_service = NotificationService(session, settings)

    async def list_events(self, user: User, workspace_id: int) -> list[Event]:
        membership = await get_workspace_member(self.session, workspace_id, user.id)
        if not membership:
            raise NotFoundError("Workspace not found")
        result = await self.session.scalars(
            select(Event)
            .where(
                Event.workspace_id == workspace_id,
                Event.status != EventStatus.CANCELLED.value,
            )
            .options(selectinload(Event.participants).selectinload(EventParticipant.user))
            .order_by(Event.start_at)
        )
        return list(result)

    async def get_event(self, user: User, event_id: int) -> Event:
        event = await self._load_event(event_id)
        membership = await get_workspace_member(self.session, event.workspace_id, user.id)
        if not membership:
            raise NotFoundError("Event not found")
        return event

    async def create_event(
        self,
        actor: User,
        workspace_id: int,
        payload: EventCreateRequest,
        *,
        source: str = "manual",
        poll_id: int | None = None,
    ) -> Event:
        membership = await get_workspace_member(self.session, workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Workspace not found")
        ensure_admin(membership)
        workspace_members = await self._workspace_members_map(workspace_id)
        participants = self._resolve_participants(workspace_members, payload.participant_ids)

        event = Event(
            workspace_id=workspace_id,
            created_by_user_id=actor.id,
            title=payload.title,
            description=payload.description,
            location=payload.location,
            start_at=payload.start_at,
            end_at=payload.end_at,
            timezone_name=payload.timezone_name,
            source=source,
            poll_id=poll_id,
        )
        self.session.add(event)
        await self.session.flush()
        self.session.add_all(
            [
                EventParticipant(
                    event_id=event.id,
                    user_id=participant.id,
                    attendance_status=AttendanceStatus.INVITED.value,
                )
                for participant in participants
            ]
        )
        await self.session.flush()
        event = await self._load_event(event.id)
        await self._sync_event_to_connections(event, participants)
        await self.notification_service.rebuild_reminder_jobs(event)
        await self.notification_service.send_to_users(participants, self._added_to_event_message(event))
        return await self._load_event(event.id)

    async def update_event(self, actor: User, event_id: int, payload: EventUpdateRequest) -> Event:
        event = await self._load_event(event_id)
        membership = await get_workspace_member(self.session, event.workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Event not found")
        ensure_admin(membership)

        original_participants = {participant.user_id: participant for participant in event.participants}
        removed_users: list[User] = []
        added_users: list[User] = []
        kept_user_ids = set(original_participants)

        next_start = payload.start_at or event.start_at
        next_end = payload.end_at or event.end_at
        if next_end <= next_start:
            raise ConflictError("end_at must be greater than start_at")

        if payload.title is not None:
            event.title = payload.title
        if payload.description is not None:
            event.description = payload.description
        if payload.location is not None:
            event.location = payload.location
        if payload.start_at is not None:
            event.start_at = payload.start_at
        if payload.end_at is not None:
            event.end_at = payload.end_at
        if payload.timezone_name is not None:
            event.timezone_name = payload.timezone_name

        workspace_members = await self._workspace_members_map(event.workspace_id)
        if payload.participant_ids is not None:
            desired = self._resolve_participants(workspace_members, payload.participant_ids)
            desired_ids = {user.id for user in desired}
            kept_user_ids = desired_ids
            for user_id, participant in list(original_participants.items()):
                if user_id not in desired_ids:
                    removed_users.append(participant.user)
                    await self._delete_participant_mapping(event, user_id)
                    await self.session.delete(participant)
            for desired_user in desired:
                if desired_user.id not in original_participants:
                    added_users.append(desired_user)
                    event.participants.append(
                        EventParticipant(
                            user_id=desired_user.id,
                            attendance_status=AttendanceStatus.INVITED.value,
                        )
                    )
            await self.session.flush()

        current_users = [workspace_members[user_id] for user_id in kept_user_ids]
        sync_users = current_users + added_users
        await self._sync_event_to_connections(event, sync_users, update_existing=True)
        await self.notification_service.rebuild_reminder_jobs(event)
        if current_users:
            await self.notification_service.send_to_users(current_users, self._event_updated_message(event))
        if added_users:
            await self.notification_service.send_to_users(added_users, self._added_to_event_message(event))
        if removed_users:
            await self.notification_service.send_to_users(removed_users, self._removed_from_event_message(event))
        return await self._load_event(event.id)

    async def delete_event(self, actor: User, event_id: int) -> Event:
        event = await self._load_event(event_id)
        membership = await get_workspace_member(self.session, event.workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Event not found")
        ensure_admin(membership)

        users = [participant.user for participant in event.participants]
        for mapping in list(event.mappings):
            connection = await self.integration_service.ensure_fresh_connection(mapping.connection)
            provider = self.integration_service.get_provider(connection.provider)
            try:
                await provider.delete_event(connection, mapping)
                mapping.sync_status = SyncStatus.DELETED.value
            except Exception as exc:  # pragma: no cover - defensive fallback
                mapping.sync_status = SyncStatus.ERROR.value
                mapping.last_error = str(exc)

        event.status = EventStatus.CANCELLED.value
        for job in event.notification_jobs:
            await self.session.delete(job)
        await self.notification_service.send_to_users(users, self._event_cancelled_message(event))
        return event

    async def complete_event(self, actor: User, event_id: int) -> Event:
        event = await self._load_event(event_id)
        membership = await get_workspace_member(self.session, event.workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Event not found")
        ensure_admin(membership)
        if event.status == EventStatus.CANCELLED.value:
            raise ConflictError("Cancelled event cannot be completed")
        if event.status == EventStatus.COMPLETED.value:
            return event

        event.status = EventStatus.COMPLETED.value
        users = [participant.user for participant in event.participants]
        for job in event.notification_jobs:
            await self.session.delete(job)
        await self.notification_service.send_to_users(users, self._event_completed_message(event))
        await self.session.flush()
        return await self._load_event(event.id)

    async def mark_attendance(
        self,
        actor: User,
        event_id: int,
        payload: AttendanceUpdateRequest,
    ) -> Event:
        event = await self._load_event(event_id)
        membership = await get_workspace_member(self.session, event.workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Event not found")
        ensure_admin(membership)

        participant_map = {participant.user_id: participant for participant in event.participants}
        for record in payload.records:
            participant = participant_map.get(record.user_id)
            if not participant:
                continue
            participant.attendance_status = record.status
            attendance = await self.session.scalar(
                select(AttendanceRecord).where(
                    AttendanceRecord.event_id == event.id,
                    AttendanceRecord.user_id == record.user_id,
                )
            )
            if not attendance:
                attendance = AttendanceRecord(
                    event_id=event.id,
                    user_id=record.user_id,
                    marked_by_user_id=actor.id,
                    status=record.status,
                    notes=record.notes,
                )
                self.session.add(attendance)
            else:
                attendance.status = record.status
                attendance.notes = record.notes
                attendance.marked_by_user_id = actor.id
                attendance.marked_at = datetime.now(timezone.utc)
        await self.session.flush()
        return await self._load_event(event.id)

    async def _sync_event_to_connections(
        self,
        event: Event,
        participants: list[User],
        *,
        update_existing: bool = False,
    ) -> None:
        mapping_by_user = {mapping.user_id: mapping for mapping in event.mappings}
        for participant in participants:
            connection = await self.integration_service.get_active_connection_for_user(participant.id)
            if not connection:
                continue
            provider = self.integration_service.get_provider(connection.provider)
            mapping = mapping_by_user.get(participant.id)
            try:
                if mapping and update_existing:
                    ref = await provider.update_event(connection, mapping, event, participant)
                    mapping.external_calendar_id = ref.external_calendar_id
                    mapping.external_event_id = ref.external_event_id
                    mapping.sync_status = SyncStatus.SYNCED.value
                    mapping.last_synced_at = datetime.now(timezone.utc)
                    mapping.last_error = None
                elif not mapping:
                    ref = await provider.create_event(connection, event, participant)
                    self.session.add(
                        ExternalEventMapping(
                            event_id=event.id,
                            user_id=participant.id,
                            calendar_connection_id=connection.id,
                            provider=connection.provider,
                            external_calendar_id=ref.external_calendar_id,
                            external_event_id=ref.external_event_id,
                            sync_status=SyncStatus.SYNCED.value,
                            last_synced_at=datetime.now(timezone.utc),
                        )
                    )
            except Exception as exc:  # pragma: no cover - external API fallback
                if mapping:
                    mapping.sync_status = SyncStatus.ERROR.value
                    mapping.last_error = str(exc)

    async def _delete_participant_mapping(self, event: Event, user_id: int) -> None:
        mapping = next((item for item in event.mappings if item.user_id == user_id), None)
        if not mapping:
            return
        connection = await self.integration_service.ensure_fresh_connection(mapping.connection)
        provider = self.integration_service.get_provider(connection.provider)
        try:
            await provider.delete_event(connection, mapping)
        except Exception as exc:  # pragma: no cover - external API fallback
            mapping.sync_status = SyncStatus.ERROR.value
            mapping.last_error = str(exc)
        else:
            await self.session.delete(mapping)

    async def _workspace_members_map(self, workspace_id: int) -> dict[int, User]:
        members = await self.session.scalars(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMember.user))
        )
        return {member.user_id: member.user for member in members}

    def _resolve_participants(self, workspace_members: dict[int, User], participant_ids: list[int]) -> list[User]:
        participants: list[User] = []
        for participant_id in participant_ids:
            participant = workspace_members.get(participant_id)
            if not participant:
                raise NotFoundError(f"Participant {participant_id} is not in workspace")
            participants.append(participant)
        return participants

    async def _load_event(self, event_id: int) -> Event:
        event = await self.session.scalar(
            select(Event)
            .where(Event.id == event_id)
            .options(
                selectinload(Event.participants).selectinload(EventParticipant.user),
                selectinload(Event.mappings).selectinload(ExternalEventMapping.connection),
                selectinload(Event.notification_jobs),
                selectinload(Event.workspace),
            )
        )
        if not event:
            raise NotFoundError("Event not found")
        return event

    def _event_updated_message(self, event: Event) -> str:
        details = self._event_details(event)
        return f"ОБНОВЛЕНИЕ события «{event.title}» из группы «{event.workspace.name}». Детали: {details}"

    def _added_to_event_message(self, event: Event) -> str:
        details = self._event_details(event)
        return f"Вас добавили в событие «{event.title}» из группы «{event.workspace.name}». Детали: {details}"

    def _removed_from_event_message(self, event: Event) -> str:
        details = self._event_details(event)
        return f"Вас удалили из события «{event.title}» из группы «{event.workspace.name}». Детали: {details}"

    def _event_cancelled_message(self, event: Event) -> str:
        details = self._event_details(event)
        return f"ОТМЕНА события «{event.title}» из группы «{event.workspace.name}». Детали: {details}"

    def _event_completed_message(self, event: Event) -> str:
        details = self._event_details(event)
        return f"ЗАВЕРШЕНИЕ события «{event.title}» из группы «{event.workspace.name}». Детали: {details}"

    def _event_details(self, event: Event) -> str:
        timezone_info = self._resolve_timezone(event.timezone_name)
        start_at = self._ensure_utc(event.start_at).astimezone(timezone_info)
        return f"«{start_at:%d.%m.%Y}» «{start_at:%H:%M}»"

    def _resolve_timezone(self, timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
