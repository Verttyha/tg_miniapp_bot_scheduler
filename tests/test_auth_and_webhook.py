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


async def test_bootstrap_auth_auto_joins_single_workspace(client, app, settings, telegram_mock):
    await authenticate(client, settings, 111010, "owner")

    payload = {
        "update_id": 2,
        "message": {
            "message_id": 20,
            "date": 1_700_000_100,
            "chat": {"id": -100201, "type": "group", "title": "Math club"},
            "from": {
                "id": 111010,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }

    response = await client.post("/webhooks/telegram", json=payload)
    response.raise_for_status()

    second_payload = await authenticate(client, settings, 111011, "participant")
    assert len(second_payload["workspaces"]) == 1
    assert second_payload["workspaces"][0]["name"] == "Math club"

    async with app.state.session_factory() as session:
        participant = await session.scalar(select(User).where(User.telegram_user_id == 111011))
        membership = await session.scalar(select(WorkspaceMember).where(WorkspaceMember.user_id == participant.id))

    assert membership is not None


async def test_current_session_auto_joins_single_workspace(client, app, settings, telegram_mock):
    owner_payload = await authenticate(client, settings, 111020, "owner2")
    participant_payload = await authenticate(client, settings, 111021, "viewer")
    assert participant_payload["workspaces"] == []

    setup_payload = {
        "update_id": 3,
        "message": {
            "message_id": 30,
            "date": 1_700_000_200,
            "chat": {"id": -100202, "type": "group", "title": "Chem club"},
            "from": {
                "id": 111020,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner2",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }

    setup_response = await client.post("/webhooks/telegram", json=setup_payload)
    setup_response.raise_for_status()

    current_response = await client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {participant_payload['access_token']}"},
    )
    current_response.raise_for_status()
    current_payload = current_response.json()

    assert len(current_payload["workspaces"]) == 1
    assert current_payload["workspaces"][0]["name"] == "Chem club"
