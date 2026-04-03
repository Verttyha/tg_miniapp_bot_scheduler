from __future__ import annotations

from unittest.mock import AsyncMock

from scheduler_app.main import create_app
from scheduler_app.core.settings import Settings


def build_settings(tmp_path, **overrides) -> Settings:
    base = {
        "APP_ENV": "test",
        "BASE_URL": "http://localhost:8000",
        "APP_SECRET": "test-secret",
        "BOT_TOKEN": "123456:TESTTOKEN",
        "BOT_USERNAME": "test_scheduler_bot",
        "ALLOW_INSECURE_DEV_AUTH": False,
        "DATABASE_URL": f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        "SQLITE_PATH": str(tmp_path / "unused.db"),
    }
    base.update(overrides)
    return Settings(**base)


async def test_startup_syncs_webhook_for_public_https_base_url(tmp_path):
    settings = build_settings(tmp_path, BASE_URL="https://scheduler.example.com")
    app = create_app(settings)
    app.state.bot.set_webhook = AsyncMock()

    async with app.router.lifespan_context(app):
        assert app.state.scheduler._task is None
        pass

    app.state.bot.set_webhook.assert_awaited_once()
    assert (
        app.state.bot.set_webhook.await_args.kwargs["url"]
        == "https://scheduler.example.com/webhooks/telegram"
    )


async def test_startup_skips_webhook_sync_for_local_base_url(tmp_path):
    settings = build_settings(tmp_path)
    app = create_app(settings)
    app.state.bot.set_webhook = AsyncMock()

    async with app.router.lifespan_context(app):
        assert app.state.scheduler._task is None
        pass

    app.state.bot.set_webhook.assert_not_awaited()
