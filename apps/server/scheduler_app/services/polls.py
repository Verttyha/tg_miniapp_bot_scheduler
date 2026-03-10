from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.models import Poll, PollOption, PollStatus, User, Vote, WorkspaceMember
from scheduler_app.schemas import EventCreateRequest, PollCreateRequest, PollResolveRequest, VoteRequest
from scheduler_app.security import TokenCipher
from scheduler_app.services.common import NotFoundError, PermissionDeniedError, ensure_admin, get_workspace_member
from scheduler_app.services.events import EventService
from scheduler_app.services.notifications import NotificationService
from scheduler_app.settings import Settings


class PollService:
    def __init__(self, session: AsyncSession, settings: Settings, cipher: TokenCipher):
        self.session = session
        self.settings = settings
        self.cipher = cipher
        self.notification_service = NotificationService(session, settings)

    async def list_polls(self, user: User, workspace_id: int) -> list[Poll]:
        membership = await get_workspace_member(self.session, workspace_id, user.id)
        if not membership:
            raise NotFoundError("Workspace not found")
        polls = await self.session.scalars(
            select(Poll)
            .where(Poll.workspace_id == workspace_id)
            .options(selectinload(Poll.options), selectinload(Poll.votes))
            .order_by(Poll.deadline_at.desc())
        )
        return list(polls)

    async def create_poll(self, actor: User, workspace_id: int, payload: PollCreateRequest) -> Poll:
        membership = await get_workspace_member(self.session, workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Workspace not found")
        ensure_admin(membership)
        poll = Poll(
            workspace_id=workspace_id,
            created_by_user_id=actor.id,
            title=payload.title,
            description=payload.description,
            timezone_name=payload.timezone_name,
            deadline_at=payload.deadline_at,
            participant_ids=payload.participant_ids,
        )
        self.session.add(poll)
        await self.session.flush()
        self.session.add_all(
            [
                PollOption(
                    poll_id=poll.id,
                    label=option.label,
                    start_at=option.start_at,
                    end_at=option.end_at,
                )
                for option in payload.options
            ]
        )
        await self.session.flush()
        return await self._load_poll(poll.id)

    async def get_poll(self, user: User, poll_id: int) -> tuple[Poll, int | None]:
        poll = await self._load_poll(poll_id)
        membership = await get_workspace_member(self.session, poll.workspace_id, user.id)
        if not membership:
            raise NotFoundError("Poll not found")
        user_vote = next((vote.option_id for vote in poll.votes if vote.user_id == user.id), None)
        return poll, user_vote

    async def vote(self, user: User, poll_id: int, payload: VoteRequest) -> Poll:
        poll, _ = await self.get_poll(user, poll_id)
        if poll.status != PollStatus.OPEN.value:
            raise PermissionDeniedError("Voting is closed")
        if user.id not in poll.participant_ids:
            raise PermissionDeniedError("User is not included in this poll")
        option = next((item for item in poll.options if item.id == payload.option_id), None)
        if not option:
            raise NotFoundError("Poll option not found")

        vote = await self.session.scalar(
            select(Vote).where(Vote.poll_id == poll.id, Vote.user_id == user.id)
        )
        if not vote:
            vote = Vote(poll_id=poll.id, user_id=user.id, option_id=payload.option_id)
            self.session.add(vote)
        else:
            vote.option_id = payload.option_id
        await self.session.flush()
        return await self._load_poll(poll.id)

    async def resolve(self, actor: User, poll_id: int, payload: PollResolveRequest) -> Poll:
        poll = await self._load_poll(poll_id)
        membership = await get_workspace_member(self.session, poll.workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Poll not found")
        ensure_admin(membership)
        return await self._resolve_poll(poll, selected_option_id=payload.selected_option_id)

    async def resolve_due_polls(self) -> list[Poll]:
        due = await self.session.scalars(
            select(Poll)
            .where(Poll.status == PollStatus.OPEN.value, Poll.deadline_at <= datetime.now(timezone.utc))
            .options(selectinload(Poll.options), selectinload(Poll.votes))
        )
        resolved: list[Poll] = []
        for poll in due:
            resolved.append(await self._resolve_poll(poll))
        return resolved

    async def _resolve_poll(self, poll: Poll, *, selected_option_id: int | None = None) -> Poll:
        option = None
        if selected_option_id is not None:
            option = next((item for item in poll.options if item.id == selected_option_id), None)
            if not option:
                raise NotFoundError("Selected poll option not found")
        else:
            vote_totals: dict[int, int] = {}
            for vote in poll.votes:
                vote_totals[vote.option_id] = vote_totals.get(vote.option_id, 0) + 1
            if vote_totals:
                ordered = sorted(vote_totals.items(), key=lambda item: item[1], reverse=True)
                top_option_id, top_votes = ordered[0]
                tied = [option_id for option_id, total in ordered if total == top_votes]
                if len(tied) == 1:
                    option = next(item for item in poll.options if item.id == top_option_id)

        if not option:
            poll.status = PollStatus.NEEDS_ADMIN_RESOLUTION.value
            users = await self._poll_participants(poll)
            await self.notification_service.send_to_users(
                users,
                f"Poll '{poll.title}' needs admin resolution before an event can be created.",
            )
            return await self._load_poll(poll.id)

        event_service = EventService(self.session, self.settings, self.cipher)
        payload = EventCreateRequest(
            title=poll.title,
            description=poll.description,
            start_at=option.start_at,
            end_at=option.end_at,
            timezone_name=poll.timezone_name,
            participant_ids=poll.participant_ids,
        )
        creator = await self.session.scalar(select(User).where(User.id == poll.created_by_user_id))
        event = await event_service.create_event(
            creator,
            poll.workspace_id,
            payload,
            source="poll",
            poll_id=poll.id,
        )
        poll.selected_option_id = option.id
        poll.resulting_event_id = event.id
        poll.status = PollStatus.FINALIZED.value
        await self.notification_service.send_to_users(
            await self._poll_participants(poll),
            f"Poll '{poll.title}' has been finalized. Event starts at {option.start_at.isoformat()}",
        )
        return await self._load_poll(poll.id)

    async def _poll_participants(self, poll: Poll) -> list[User]:
        members = await self.session.scalars(
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == poll.workspace_id,
                WorkspaceMember.user_id.in_(poll.participant_ids),
            )
            .options(selectinload(WorkspaceMember.user))
        )
        return [member.user for member in members]

    async def _load_poll(self, poll_id: int) -> Poll:
        poll = await self.session.scalar(
            select(Poll)
            .where(Poll.id == poll_id)
            .options(selectinload(Poll.options), selectinload(Poll.votes))
        )
        if not poll:
            raise NotFoundError("Poll not found")
        return poll
