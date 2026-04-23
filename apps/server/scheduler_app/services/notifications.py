from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import Event, NotificationJob, NotificationKind, NotificationStatus, User

logger = logging.getLogger(__name__)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class NotificationService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings

    def _telegram_api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.settings.bot_token}/{method}"

    def _telegram_client(self) -> httpx.AsyncClient:
        timeout = self.settings.telegram_request_timeout_seconds
        if self.settings.telegram_proxy_url:
            try:
                return httpx.AsyncClient(timeout=timeout, proxy=self.settings.telegram_proxy_url)
            except (ImportError, RuntimeError) as exc:
                logger.warning("Telegram proxy is configured but unavailable for httpx: %s", exc)
        return httpx.AsyncClient(timeout=timeout)

    def _can_send_telegram_messages(self) -> bool:
        return bool(self.settings.bot_token) and not self.settings.bot_token.endswith(":CHANGE_ME")

    async def send_to_users(self, users: list[User], text: str) -> None:
        if not self._can_send_telegram_messages():
            return
        async with self._telegram_client() as client:
            for user in users:
                if not user.telegram_user_id:
                    continue
                try:
                    response = await client.post(
                        self._telegram_api_url("sendMessage"),
                        json={"chat_id": user.telegram_user_id, "text": text},
                    )
                    if not response.is_success:
                        logger.warning(
                            "Failed to send Telegram notification to %s: %s %s",
                            user.telegram_user_id,
                            response.status_code,
                            response.text,
                        )
                except httpx.HTTPError as exc:
                    logger.warning("Telegram notification request failed for %s: %s", user.telegram_user_id, exc)

    async def rebuild_reminder_jobs(self, event: Event) -> None:
        due_at = ensure_utc(event.start_at) - timedelta(minutes=self.settings.reminder_minutes_before)
        if due_at <= datetime.now(timezone.utc):
            return
        current_jobs = await self.session.scalars(
            select(NotificationJob).where(
                NotificationJob.event_id == event.id,
                NotificationJob.kind == NotificationKind.REMINDER.value,
            )
        )
        for job in current_jobs:
            await self.session.delete(job)
        for participant in event.participants:
            self.session.add(
                NotificationJob(
                    user_id=participant.user_id,
                    event_id=event.id,
                    kind=NotificationKind.REMINDER.value,
                    due_at=due_at,
                    payload={"event_title": event.title},
                )
            )
        await self.session.flush()

    async def dispatch_due_jobs(self) -> None:
        due_jobs = await self.session.scalars(
            select(NotificationJob)
            .where(
                NotificationJob.status == NotificationStatus.PENDING.value,
                NotificationJob.due_at <= datetime.now(timezone.utc),
            )
            .options(selectinload(NotificationJob.user), selectinload(NotificationJob.event))
        )
        async with self._telegram_client() as client:
            for job in due_jobs:
                if not job.user.telegram_user_id or not self._can_send_telegram_messages():
                    job.status = NotificationStatus.FAILED.value
                    job.error_message = "Bot token or user chat unavailable"
                    continue
                message = self._render_job(job)
                try:
                    response = await client.post(
                        self._telegram_api_url("sendMessage"),
                        json={"chat_id": job.user.telegram_user_id, "text": message},
                    )
                except httpx.HTTPError as exc:
                    job.status = NotificationStatus.FAILED.value
                    job.error_message = str(exc)
                    continue
                if response.is_success:
                    job.status = NotificationStatus.SENT.value
                    job.sent_at = datetime.now(timezone.utc)
                    job.error_message = None
                else:
                    job.status = NotificationStatus.FAILED.value
                    job.error_message = response.text

    def _render_job(self, job: NotificationJob) -> str:
        if job.kind == NotificationKind.REMINDER.value and job.event:
            return f"Reminder: '{job.event.title}' starts at {ensure_utc(job.event.start_at).isoformat()}."
        return f"Notification: {job.kind}"
