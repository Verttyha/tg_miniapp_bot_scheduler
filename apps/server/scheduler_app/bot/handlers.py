from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.ext.asyncio import async_sessionmaker

from scheduler_app.bot.service import ensure_telegram_user
from scheduler_app.services.workspaces import WorkspaceService
from scheduler_app.settings import Settings


def build_router(session_factory: async_sessionmaker, settings: Settings) -> Router:
    router = Router()

    @router.message(CommandStart(), F.chat.type == "private")
    async def start_handler(message: Message) -> None:
        if not message.from_user:
            return
        async with session_factory() as session:
            await ensure_telegram_user(session, message.from_user)
            await session.commit()
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Open Scheduler",
                        web_app=WebAppInfo(url=f"{settings.base_url.rstrip('/')}/app"),
                    )
                ]
            ]
        )
        try:
            await message.answer(
                "Open the Mini App to join workspaces, connect calendars, and manage shared schedules.",
                reply_markup=markup,
            )
        except TelegramAPIError:
            return

    @router.message(Command("setup"), F.chat.type.in_({"group", "supergroup"}))
    async def setup_workspace(message: Message) -> None:
        if not message.from_user:
            return
        async with session_factory() as session:
            actor = await ensure_telegram_user(session, message.from_user)
            workspace = await WorkspaceService(session).ensure_group_workspace(
                actor=actor,
                telegram_chat_id=message.chat.id,
                title=message.chat.title or "Group workspace",
                chat_type=message.chat.type,
            )
            await session.commit()
        try:
            await message.answer(
                f"Workspace '{workspace.name}' is ready. Ask participants to open the bot in private and join from the Mini App."
            )
        except TelegramAPIError:
            return

    return router
