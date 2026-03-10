from __future__ import annotations

from sqlalchemy import select

from scheduler_app.models import User, Workspace, WorkspaceMember

from tests.conftest import authenticate


async def test_bootstrap_auth_creates_user(client, settings):
    payload = await authenticate(client, settings, 111001, "owner")

    assert payload["access_token"]
    assert payload["user"]["telegram_user_id"] == 111001
    assert payload["workspaces"] == []


async def test_group_setup_webhook_creates_workspace(client, app, settings, telegram_mock):
    await authenticate(client, settings, 111002, "groupadmin")

    payload = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "date": 1_700_000_000,
            "chat": {"id": -100200, "type": "group", "title": "Physics club"},
            "from": {
                "id": 111002,
                "is_bot": False,
                "first_name": "Group",
                "username": "groupadmin",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }

    response = await client.post("/webhooks/telegram", json=payload)
    response.raise_for_status()

    async with app.state.session_factory() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "Physics club"))
        membership = await session.scalar(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
        )
        user = await session.scalar(select(User).where(User.telegram_user_id == 111002))

    assert workspace is not None
    assert membership is not None
    assert user is not None
