from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import re

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramAPIError
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, Update
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from scheduler_app.api.router import api_router
from scheduler_app.api.routes.integrations import oauth_router
from scheduler_app.bot.handlers import build_router as build_bot_router
from scheduler_app.core.database import build_engine
from scheduler_app.core.deps import get_current_user, get_session
from scheduler_app.core.security import TokenCipher
from scheduler_app.core.settings import Settings, get_settings
from scheduler_app.domain.models import Base, User
from scheduler_app.services.presenters import user_read, workspace_read
from scheduler_app.services.scheduler import SchedulerRunner
from scheduler_app.services.workspaces import WorkspaceService

logger = logging.getLogger(__name__)


async def sync_telegram_webhook(bot: Bot, dispatcher: Dispatcher, settings: Settings) -> None:
    if not settings.should_sync_telegram_webhook:
        return

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="connect", description="Подключиться к календарю чата"),
                BotCommand(command="setup", description="Подключить календарь чата"),
            ],
            scope=BotCommandScopeAllGroupChats(),
        )
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Открыть Mini App"),
                BotCommand(command="admins", description="Управление администраторами"),
            ],
            scope=BotCommandScopeAllPrivateChats(),
        )
    except TelegramAPIError as exc:
        logger.warning("Telegram commands sync failed: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram commands sync failed with unexpected error: %s", exc)
    try:
        await bot.set_webhook(
            url=settings.telegram_webhook_url,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        logger.info("Telegram webhook synced to %s", settings.telegram_webhook_url)
    except TelegramAPIError as exc:
        logger.warning("Telegram webhook sync failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 - webhook sync must never crash startup
        logger.warning("Telegram webhook sync failed with unexpected error: %s", exc)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    engine = build_engine(runtime_settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    cipher = TokenCipher(runtime_settings.app_secret)
    bot_session = None
    if runtime_settings.telegram_proxy_url:
        try:
            bot_session = AiohttpSession(
                proxy=runtime_settings.telegram_proxy_url,
                timeout=runtime_settings.telegram_request_timeout_seconds,
            )
        except RuntimeError as exc:
            logger.warning("Telegram proxy is configured but unavailable: %s", exc)
    bot = Bot(
        runtime_settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=bot_session,
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(build_bot_router(session_factory, runtime_settings))
    scheduler = SchedulerRunner(session_factory, runtime_settings, cipher, bot)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await sync_telegram_webhook(bot, dispatcher, runtime_settings)
        try:
            yield
        finally:
            await scheduler.stop()
            await bot.session.close()
            await engine.dispose()

    app = FastAPI(title=runtime_settings.app_name, lifespan=lifespan)
    app.state.settings = runtime_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.cipher = cipher
    app.state.bot = bot
    app.state.dispatcher = dispatcher
    app.state.scheduler = scheduler

    def should_skip_post_trigger(path: str, method: str) -> bool:
        if method != "POST":
            return False
        return bool(re.fullmatch(rf"{runtime_settings.api_prefix}/workspaces/\d+/polls", path))

    @app.middleware("http")
    async def trigger_scheduler_on_activity(request: Request, call_next):
        path = request.url.path
        is_api_request = path.startswith(runtime_settings.api_prefix)
        is_telegram_webhook = path.startswith("/webhooks/telegram")
        is_read_request = request.method in {"GET", "HEAD", "OPTIONS"}

        if is_api_request and is_read_request:
            await scheduler.trigger()

        response = await call_next(request)

        if is_telegram_webhook or (
            is_api_request and not is_read_request and not should_skip_post_trigger(path, request.method)
        ):
            await scheduler.trigger()

        return response

    app.include_router(api_router, prefix=runtime_settings.api_prefix)
    app.include_router(oauth_router)

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/app")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/me")
    async def current_session(
        current_user: User = Depends(get_current_user),
        session=Depends(get_session),
    ) -> dict:
        service = WorkspaceService(session)
        workspaces = await service.list_for_user(current_user)
        return {
            "user": user_read(current_user).model_dump(),
            "workspaces": [workspace_read(workspace).model_dump() for workspace in workspaces],
        }

    @app.post("/webhooks/telegram")
    async def telegram_webhook(request: Request) -> dict[str, bool]:
        update = Update.model_validate(await request.json())
        try:
            await dispatcher.feed_update(bot, update)
        except Exception:
            logger.exception("Telegram update handling failed")
        return {"ok": True}

    @app.get("/app")
    @app.get("/app/{path:path}")
    async def serve_miniapp(path: str = ""):
        dist_dir = runtime_settings.frontend_dist_dir
        requested_path = dist_dir / path if path else dist_dir / "index.html"
        if path and requested_path.exists() and requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(dist_dir / "index.html")

    return app


app = create_app()


def run() -> None:
    uvicorn.run("scheduler_app.main:app", host="0.0.0.0", port=8000, reload=True)
