from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select

from scheduler_app.main import create_app
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import TelegramChat, User, Workspace, WorkspaceMember, WorkspaceRole


def build_init_data(bot_token: str, user_payload: dict) -> str:
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "query-id",
        "user": json.dumps(user_payload, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(params)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        APP_ENV="test",
        BASE_URL="http://testserver",
        APP_SECRET="test-secret",
        BOT_TOKEN="123456:TESTTOKEN",
        BOT_USERNAME="test_scheduler_bot",
        ALLOW_INSECURE_DEV_AUTH=False,
        DATABASE_URL=f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        SQLITE_PATH=str(tmp_path / "unused.db"),
    )


@pytest.fixture
async def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            yield test_client


@pytest.fixture
def telegram_mock():
    with respx.mock(base_url="https://api.telegram.org", assert_all_called=False) as mock_router:
        mock_router.post(path__regex=r"/bot.*/sendMessage").mock(
            return_value=Response(200, json={"ok": True, "result": {"message_id": 1}})
        )
        mock_router.post(path__regex=r"/bot.*/answerCallbackQuery").mock(
            return_value=Response(200, json={"ok": True, "result": True})
        )
        yield mock_router


async def authenticate(client: AsyncClient, settings: Settings, telegram_user_id: int, username: str):
    payload = {
        "id": telegram_user_id,
        "first_name": username.capitalize(),
        "username": username,
        "language_code": "en",
    }
    response = await client.post(
        "/api/auth/telegram/init-data",
        json={"init_data": build_init_data(settings.bot_token, payload)},
    )
    response.raise_for_status()
    return response.json()


async def seed_workspace(app, owner_telegram_id: int, participant_telegram_id: int):
    async with app.state.session_factory() as session:
        owner = await session.scalar(select(User).where(User.telegram_user_id == owner_telegram_id))
        participant = await session.scalar(select(User).where(User.telegram_user_id == participant_telegram_id))
        chat = TelegramChat(telegram_chat_id=-100100, title="Study group", chat_type="group")
        session.add(chat)
        await session.flush()
        workspace = Workspace(name="Study group", owner_user_id=owner.id, telegram_chat_id=chat.id)
        session.add(workspace)
        await session.flush()
        session.add_all(
            [
                WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER.value),
                WorkspaceMember(workspace_id=workspace.id, user_id=participant.id, role=WorkspaceRole.MEMBER.value),
            ]
        )
        await session.commit()
        return {"workspace_id": workspace.id, "owner_id": owner.id, "participant_id": participant.id}


def future_iso(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
