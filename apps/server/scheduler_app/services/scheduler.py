from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker

from scheduler_app.security import TokenCipher
from scheduler_app.services.notifications import NotificationService
from scheduler_app.services.polls import PollService
from scheduler_app.settings import Settings


logger = logging.getLogger(__name__)


class SchedulerRunner:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        settings: Settings,
        cipher: TokenCipher,
        bot: Bot,
    ):
        self.session_factory = session_factory
        self.settings = settings
        self.cipher = cipher
        self.bot = bot
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def tick(self) -> None:
        async with self.session_factory() as session:
            poll_service = PollService(session, self.settings, self.cipher, bot=self.bot)
            notification_service = NotificationService(session, self.settings)
            await poll_service.resolve_due_polls()
            await notification_service.dispatch_due_jobs()
            await session.commit()

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.tick()
            except Exception:  # pragma: no cover - defensive background logging
                logger.exception("Scheduler tick failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.settings.scheduler_interval_seconds,
                )
            except asyncio.TimeoutError:
                continue
