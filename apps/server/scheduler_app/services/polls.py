from __future__ import annotations

from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import PollAnswer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.bot.service import ensure_telegram_user
from scheduler_app.core.security import TokenCipher
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import Poll, PollOption, PollStatus, TelegramChatPoll, User, Vote, Workspace, WorkspaceMember
from scheduler_app.domain.schemas import EventCreateRequest, PollCreateRequest, PollResolveRequest, VoteRequest
from scheduler_app.services.common import NotFoundError, PermissionDeniedError, ServiceError, ensure_admin, get_workspace_member
from scheduler_app.services.events import EventService
from scheduler_app.services.notifications import NotificationService


logger = logging.getLogger(__name__)


class PollService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        cipher: TokenCipher,
        *,
        bot: Bot | None = None,
    ):
        self.session = session
        self.settings = settings
        self.cipher = cipher
        self.bot = bot
        self.notification_service = NotificationService(session, settings)

    async def list_polls(self, user: User, workspace_id: int) -> list[Poll]:
        membership = await get_workspace_member(self.session, workspace_id, user.id)
        if not membership:
            raise NotFoundError("Workspace not found")
        polls = await self.session.scalars(
            select(Poll)
            .where(Poll.workspace_id == workspace_id)
            .options(
                selectinload(Poll.options),
                selectinload(Poll.votes),
                selectinload(Poll.telegram_chat_poll),
            )
            .order_by(Poll.deadline_at.desc())
        )
        return list(polls)

    async def create_poll(self, actor: User, workspace_id: int, payload: PollCreateRequest) -> Poll:
        membership = await get_workspace_member(self.session, workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Workspace not found")
        ensure_admin(membership)

        workspace = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.telegram_chat))
        )
        if not workspace:
            raise NotFoundError("Workspace not found")

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

        option_records = [
            PollOption(
                poll_id=poll.id,
                label=option.label,
                start_at=option.start_at,
                end_at=option.end_at,
            )
            for option in payload.options
        ]
        self.session.add_all(option_records)
        await self.session.flush()

        if workspace.telegram_chat:
            await self._publish_telegram_chat_poll(
                workspace=workspace,
                poll=poll,
                options=option_records,
            )

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
        if poll.telegram_chat_poll:
            raise PermissionDeniedError("Vote in the Telegram chat poll")
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

    async def sync_telegram_poll_answer(self, answer: PollAnswer) -> Poll | None:
        if not answer.user:
            return None

        chat_poll = await self.session.scalar(
            select(TelegramChatPoll)
            .where(TelegramChatPoll.telegram_poll_id == answer.poll_id)
            .options(
                selectinload(TelegramChatPoll.poll).selectinload(Poll.options),
                selectinload(TelegramChatPoll.poll).selectinload(Poll.votes),
                selectinload(TelegramChatPoll.poll).selectinload(Poll.telegram_chat_poll),
            )
        )
        if not chat_poll:
            return None

        poll = chat_poll.poll
        if poll.status != PollStatus.OPEN.value:
            return poll

        user = await ensure_telegram_user(self.session, answer.user)
        if user.id not in poll.participant_ids:
            return poll

        existing_vote = await self.session.scalar(
            select(Vote).where(Vote.poll_id == poll.id, Vote.user_id == user.id)
        )

        if not answer.option_ids:
            if existing_vote:
                await self.session.delete(existing_vote)
                await self.session.flush()
            return await self._load_poll(poll.id)

        ordered_options = self._ordered_poll_options(poll)
        selected_index = answer.option_ids[0]
        if selected_index < 0 or selected_index >= len(ordered_options):
            logger.warning("Ignoring invalid Telegram poll option index %s for poll %s", selected_index, poll.id)
            return await self._load_poll(poll.id)

        selected_option = ordered_options[selected_index]
        if not existing_vote:
            self.session.add(Vote(poll_id=poll.id, user_id=user.id, option_id=selected_option.id))
        else:
            existing_vote.option_id = selected_option.id
        await self.session.flush()
        return await self._load_poll(poll.id)

    async def resolve(self, actor: User, poll_id: int, payload: PollResolveRequest) -> Poll:
        poll = await self._load_poll(poll_id)
        membership = await get_workspace_member(self.session, poll.workspace_id, actor.id)
        if not membership:
            raise NotFoundError("Poll not found")
        ensure_admin(membership)
        await self._close_telegram_chat_poll(poll, raise_on_error=False)
        return await self._resolve_poll(poll, selected_option_id=payload.selected_option_id)

    async def resolve_due_polls(self) -> list[Poll]:
        due = await self.session.scalars(
            select(Poll)
            .where(Poll.status == PollStatus.OPEN.value, Poll.deadline_at <= datetime.now(timezone.utc))
            .options(
                selectinload(Poll.options),
                selectinload(Poll.votes),
                selectinload(Poll.telegram_chat_poll),
            )
        )
        resolved: list[Poll] = []
        for poll in due:
            await self._close_telegram_chat_poll(poll, raise_on_error=False)
            resolved.append(await self._resolve_poll(poll))
        return resolved

    async def _resolve_poll(self, poll: Poll, *, selected_option_id: int | None = None) -> Poll:
        option = None
        if selected_option_id is not None:
            option = next((item for item in poll.options if item.id == selected_option_id), None)
            if not option:
                raise NotFoundError("Selected poll option not found")
        else:
            option = self._pick_winning_option(poll)

        if not option:
            poll.status = PollStatus.NEEDS_ADMIN_RESOLUTION.value
            users = await self._poll_participants(poll)
            await self.notification_service.send_to_users(
                users,
                f"Poll '{poll.title}' needs admin resolution before an event can be created.",
            )
            await self._send_chat_message(
                poll,
                f"Голосование «{poll.title}» завершено без победителя. Нужен выбор администратора в Mini App.",
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
        await self._send_chat_message(
            poll,
            f"Голосование «{poll.title}» завершено. Победил вариант: {self._build_option_label(poll, option)}. Событие создано.",
        )
        return await self._load_poll(poll.id)

    async def _publish_telegram_chat_poll(
        self,
        *,
        workspace: Workspace,
        poll: Poll,
        options: list[PollOption],
    ) -> None:
        if not workspace.telegram_chat:
            return
        if not self.bot or self.settings.bot_token.endswith(":CHANGE_ME"):
            raise ServiceError("Telegram bot is not configured to publish chat polls")

        try:
            sent_message = await self.bot.send_poll(
                chat_id=workspace.telegram_chat.telegram_chat_id,
                question=self._build_question(poll),
                options=[self._build_option_label(poll, option) for option in self._ordered_poll_options_from_list(options)],
                is_anonymous=False,
                allows_multiple_answers=False,
            )
        except TelegramAPIError as exc:
            raise ServiceError(f"Unable to publish Telegram poll to the chat: {exc}") from exc

        if not sent_message.poll:
            raise ServiceError("Telegram did not return poll details for the created chat poll")

        self.session.add(
            TelegramChatPoll(
                poll_id=poll.id,
                telegram_poll_id=sent_message.poll.id,
                telegram_chat_id=workspace.telegram_chat.telegram_chat_id,
                telegram_message_id=sent_message.message_id,
            )
        )
        await self.session.flush()

    async def _close_telegram_chat_poll(self, poll: Poll, *, raise_on_error: bool) -> None:
        chat_poll = poll.telegram_chat_poll
        if not chat_poll or chat_poll.closed_at:
            return
        if not self.bot or self.settings.bot_token.endswith(":CHANGE_ME"):
            if raise_on_error:
                raise ServiceError("Telegram bot is not configured to close chat polls")
            return

        try:
            await self.bot.stop_poll(
                chat_id=chat_poll.telegram_chat_id,
                message_id=chat_poll.telegram_message_id,
            )
        except TelegramAPIError:
            if raise_on_error:
                raise
            logger.exception("Failed to close Telegram chat poll for poll %s", poll.id)
            return

        chat_poll.closed_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def _send_chat_message(self, poll: Poll, text: str) -> None:
        chat_poll = poll.telegram_chat_poll
        if not chat_poll or not self.bot or self.settings.bot_token.endswith(":CHANGE_ME"):
            return
        try:
            await self.bot.send_message(chat_id=chat_poll.telegram_chat_id, text=text)
        except TelegramAPIError:
            logger.exception("Failed to send Telegram chat message for poll %s", poll.id)

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
            .options(
                selectinload(Poll.options),
                selectinload(Poll.votes),
                selectinload(Poll.telegram_chat_poll),
            )
        )
        if not poll:
            raise NotFoundError("Poll not found")
        return poll

    def _pick_winning_option(self, poll: Poll) -> PollOption | None:
        vote_totals: dict[int, int] = {}
        for vote in poll.votes:
            vote_totals[vote.option_id] = vote_totals.get(vote.option_id, 0) + 1
        if not vote_totals:
            return None

        ordered = sorted(vote_totals.items(), key=lambda item: item[1], reverse=True)
        top_option_id, top_votes = ordered[0]
        tied = [option_id for option_id, total in ordered if total == top_votes]
        if len(tied) != 1:
            return None
        return next((item for item in poll.options if item.id == top_option_id), None)

    def _build_question(self, poll: Poll) -> str:
        return poll.title.strip()[:300] or "Выберите время"

    def _build_option_label(self, poll: Poll, option: PollOption) -> str:
        timezone_info = self._resolve_timezone(poll.timezone_name)
        start_at = option.start_at.astimezone(timezone_info)
        end_at = option.end_at.astimezone(timezone_info)
        timing = f"{start_at:%d.%m %H:%M}-{end_at:%H:%M}"
        prefix = f"{option.label.strip()} " if option.label and option.label.strip() else ""
        return f"{prefix}{timing}"[:100]

    def _ordered_poll_options(self, poll: Poll) -> list[PollOption]:
        return sorted(poll.options, key=lambda option: option.id)

    def _ordered_poll_options_from_list(self, options: list[PollOption]) -> list[PollOption]:
        return sorted(options, key=lambda option: option.id)

    def _resolve_timezone(self, timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")
