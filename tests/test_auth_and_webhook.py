from __future__ import annotations

import json

from sqlalchemy import select

from scheduler_app.domain.models import TelegramChat, User, Workspace, WorkspaceMember, WorkspaceRole

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
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.role == WorkspaceRole.OWNER.value,
            )
        )
        user = await session.scalar(select(User).where(User.telegram_user_id == 111002))

    assert workspace is not None
    assert membership is not None
    assert user is not None
    assert membership.user_id == user.id


async def test_group_start_webhook_creates_workspace(client, app, settings, telegram_mock):
    await authenticate(client, settings, 111003, "calendaradmin")

    payload = {
        "update_id": 11,
        "message": {
            "message_id": 11,
            "date": 1_700_000_050,
            "chat": {"id": -100203, "type": "group", "title": "History club"},
            "from": {
                "id": 111003,
                "is_bot": False,
                "first_name": "Calendar",
                "username": "calendaradmin",
            },
            "text": "/start setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }

    response = await client.post("/webhooks/telegram", json=payload)
    response.raise_for_status()

    async with app.state.session_factory() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "History club"))
        membership = await session.scalar(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
        )

    assert workspace is not None
    assert membership is not None


async def test_existing_group_setup_keeps_first_connector_as_owner(client, app, settings, telegram_mock):
    await authenticate(client, settings, 111004, "firstowner")
    await authenticate(client, settings, 111005, "seconduser")

    initial_payload = {
        "update_id": 21,
        "message": {
            "message_id": 21,
            "date": 1_700_000_060,
            "chat": {"id": -100204, "type": "group", "title": "Book club"},
            "from": {
                "id": 111004,
                "is_bot": False,
                "first_name": "First",
                "username": "firstowner",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }
    second_payload = {
        "update_id": 22,
        "message": {
            "message_id": 22,
            "date": 1_700_000_061,
            "chat": {"id": -100204, "type": "group", "title": "Book club"},
            "from": {
                "id": 111005,
                "is_bot": False,
                "first_name": "Second",
                "username": "seconduser",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }

    initial_response = await client.post("/webhooks/telegram", json=initial_payload)
    initial_response.raise_for_status()
    second_response = await client.post("/webhooks/telegram", json=second_payload)
    second_response.raise_for_status()

    async with app.state.session_factory() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "Book club"))
        first_user = await session.scalar(select(User).where(User.telegram_user_id == 111004))
        second_user = await session.scalar(select(User).where(User.telegram_user_id == 111005))
        first_membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == first_user.id,
            )
        )
        second_membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == second_user.id,
            )
        )

    assert workspace is not None
    assert first_user is not None
    assert second_user is not None
    assert workspace.owner_user_id == first_user.id
    assert first_membership is not None
    assert second_membership is not None
    assert first_membership.role == WorkspaceRole.OWNER.value
    assert second_membership.role == WorkspaceRole.MEMBER.value


async def test_owner_can_promote_member_to_admin_from_private_bot(client, app, settings, telegram_mock):
    await authenticate(client, settings, 111030, "owner3")

    setup_payload = {
        "update_id": 31,
        "message": {
            "message_id": 31,
            "date": 1_700_000_300,
            "chat": {"id": -100230, "type": "group", "title": "Cinema club"},
            "from": {
                "id": 111030,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner3",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }
    setup_response = await client.post("/webhooks/telegram", json=setup_payload)
    setup_response.raise_for_status()

    await authenticate(client, settings, 111031, "member3")

    async with app.state.session_factory() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "Cinema club"))
        member = await session.scalar(select(User).where(User.telegram_user_id == 111031))
        owner = await session.scalar(select(User).where(User.telegram_user_id == 111030))
        membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == member.id,
            )
        )

    assert workspace is not None
    assert member is not None
    assert owner is not None
    assert membership is not None
    assert membership.role == WorkspaceRole.MEMBER.value

    admins_command_payload = {
        "update_id": 32,
        "message": {
            "message_id": 32,
            "date": 1_700_000_301,
            "chat": {"id": 111030, "type": "private", "first_name": "Owner", "username": "owner3"},
            "from": {
                "id": 111030,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner3",
            },
            "text": "/admins",
            "entities": [{"offset": 0, "length": 7, "type": "bot_command"}],
        },
    }
    admins_command_response = await client.post("/webhooks/telegram", json=admins_command_payload)
    admins_command_response.raise_for_status()

    workspace_callback_payload = {
        "update_id": 33,
        "callback_query": {
            "id": "cbq-workspace",
            "from": {
                "id": 111030,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner3",
            },
            "message": {
                "message_id": 320,
                "date": 1_700_000_302,
                "chat": {"id": 111030, "type": "private", "first_name": "Owner", "username": "owner3"},
                "text": "Админы чатов",
            },
            "chat_instance": "chat-instance-1",
            "data": f"admins:ws:{workspace.id}",
        },
    }
    workspace_callback_response = await client.post("/webhooks/telegram", json=workspace_callback_payload)
    workspace_callback_response.raise_for_status()

    promote_callback_payload = {
        "update_id": 34,
        "callback_query": {
            "id": "cbq-promote",
            "from": {
                "id": 111030,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner3",
            },
            "message": {
                "message_id": 321,
                "date": 1_700_000_303,
                "chat": {"id": 111030, "type": "private", "first_name": "Owner", "username": "owner3"},
                "text": "Управление администраторами",
            },
            "chat_instance": "chat-instance-2",
            "data": f"admins:set:{workspace.id}:{member.id}:admin",
        },
    }
    promote_callback_response = await client.post("/webhooks/telegram", json=promote_callback_payload)
    promote_callback_response.raise_for_status()

    async with app.state.session_factory() as session:
        promoted_membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == member.id,
            )
        )

    assert promoted_membership is not None
    assert promoted_membership.role == WorkspaceRole.ADMIN.value


async def test_bootstrap_auth_does_not_auto_join_single_workspace(client, app, settings, telegram_mock):
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
    assert second_payload["workspaces"] == []

    async with app.state.session_factory() as session:
        participant = await session.scalar(select(User).where(User.telegram_user_id == 111011))
        membership = await session.scalar(select(WorkspaceMember).where(WorkspaceMember.user_id == participant.id))

    assert membership is None


async def test_current_session_does_not_auto_join_single_workspace(client, app, settings, telegram_mock):
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

    assert current_payload["workspaces"] == []


async def test_group_setup_from_human_repairs_anonymous_owner(client, app, settings, telegram_mock):
    await authenticate(client, settings, 111050, "realowner")

    added_payload = {
        "update_id": 51,
        "my_chat_member": {
            "chat": {"id": -100250, "type": "group", "title": "Anonymous club"},
            "from": {
                "id": 1087968824,
                "is_bot": True,
                "first_name": "GroupAnonymousBot",
                "username": "GroupAnonymousBot",
            },
            "date": 1_700_000_500,
            "old_chat_member": {
                "user": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "SchedulerBot",
                    "username": "test_scheduler_bot",
                },
                "status": "left",
            },
            "new_chat_member": {
                "user": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "SchedulerBot",
                    "username": "test_scheduler_bot",
                },
                "status": "member",
            },
        },
    }
    added_response = await client.post("/webhooks/telegram", json=added_payload)
    added_response.raise_for_status()

    setup_payload = {
        "update_id": 52,
        "message": {
            "message_id": 52,
            "date": 1_700_000_501,
            "chat": {"id": -100250, "type": "group", "title": "Anonymous club"},
            "from": {
                "id": 111050,
                "is_bot": False,
                "first_name": "Real",
                "username": "realowner",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }
    setup_response = await client.post("/webhooks/telegram", json=setup_payload)
    setup_response.raise_for_status()

    async with app.state.session_factory() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "Anonymous club"))
        owner = await session.scalar(select(User).where(User.telegram_user_id == 111050))
        owner_membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == owner.id,
            )
        )

    assert workspace is not None
    assert owner is not None
    assert workspace.owner_user_id == owner.id
    assert owner_membership is not None
    assert owner_membership.role == WorkspaceRole.OWNER.value


async def test_bot_removed_from_group_detaches_workspace(client, app, settings, telegram_mock):
    owner_payload = await authenticate(client, settings, 111040, "chatowner")

    setup_payload = {
        "update_id": 41,
        "message": {
            "message_id": 41,
            "date": 1_700_000_400,
            "chat": {"id": -100240, "type": "group", "title": "Music club"},
            "from": {
                "id": 111040,
                "is_bot": False,
                "first_name": "Owner",
                "username": "chatowner",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }
    setup_response = await client.post("/webhooks/telegram", json=setup_payload)
    setup_response.raise_for_status()

    removed_payload = {
        "update_id": 42,
        "my_chat_member": {
            "chat": {"id": -100240, "type": "group", "title": "Music club"},
            "from": {
                "id": 111040,
                "is_bot": False,
                "first_name": "Owner",
                "username": "chatowner",
            },
            "date": 1_700_000_401,
            "old_chat_member": {
                "user": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "SchedulerBot",
                    "username": "test_scheduler_bot",
                },
                "status": "member",
            },
            "new_chat_member": {
                "user": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "SchedulerBot",
                    "username": "test_scheduler_bot",
                },
                "status": "left",
            },
        },
    }
    removed_response = await client.post("/webhooks/telegram", json=removed_payload)
    removed_response.raise_for_status()

    async with app.state.session_factory() as session:
        chat = await session.scalar(select(TelegramChat).where(TelegramChat.telegram_chat_id == -100240))
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "Music club"))

    current_response = await client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {owner_payload['access_token']}"},
    )
    current_response.raise_for_status()
    current_payload = current_response.json()

    assert chat is None
    assert workspace is not None
    assert workspace.telegram_chat_id is None
    assert current_payload["workspaces"] == []


async def test_bot_added_to_group_sends_welcome_with_connect_buttons(client, settings, telegram_mock):
    added_payload = {
        "update_id": 61,
        "my_chat_member": {
            "chat": {"id": -100260, "type": "group", "title": "Travel club"},
            "from": {
                "id": 111060,
                "is_bot": False,
                "first_name": "Admin",
                "username": "traveladmin",
            },
            "date": 1_700_000_600,
            "old_chat_member": {
                "user": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "SchedulerBot",
                    "username": "test_scheduler_bot",
                },
                "status": "left",
            },
            "new_chat_member": {
                "user": {
                    "id": 123456,
                    "is_bot": True,
                    "first_name": "SchedulerBot",
                    "username": "test_scheduler_bot",
                },
                "status": "member",
            },
        },
    }

    response = await client.post("/webhooks/telegram", json=added_payload)
    response.raise_for_status()

    send_message_calls = [call for call in telegram_mock.calls if "/sendMessage" in call.request.url.path]
    assert send_message_calls

    request_payload = json.loads(send_message_calls[-1].request.content.decode("utf-8"))
    keyboard = request_payload["reply_markup"]["inline_keyboard"][0]
    button_texts = {button["text"] for button in keyboard}

    assert request_payload["chat_id"] == -100260
    assert "Подключиться" in button_texts
    assert "Вступить" in button_texts


async def test_group_connect_callback_adds_pressing_user_to_workspace(client, app, settings, telegram_mock):
    setup_payload = {
        "update_id": 71,
        "message": {
            "message_id": 71,
            "date": 1_700_000_700,
            "chat": {"id": -100270, "type": "group", "title": "Chess club"},
            "from": {
                "id": 111070,
                "is_bot": False,
                "first_name": "Owner",
                "username": "owner70",
            },
            "text": "/setup",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }
    setup_response = await client.post("/webhooks/telegram", json=setup_payload)
    setup_response.raise_for_status()

    connect_payload = {
        "update_id": 72,
        "callback_query": {
            "id": "cbq-group-connect",
            "from": {
                "id": 111071,
                "is_bot": False,
                "first_name": "Member",
                "username": "member71",
            },
            "message": {
                "message_id": 720,
                "date": 1_700_000_701,
                "chat": {"id": -100270, "type": "group", "title": "Chess club"},
                "text": "Привет! Я помогу вести общий календарь.",
            },
            "chat_instance": "group-connect-instance",
            "data": "workspace:connect",
        },
    }
    connect_response = await client.post("/webhooks/telegram", json=connect_payload)
    connect_response.raise_for_status()

    async with app.state.session_factory() as session:
        workspace = await session.scalar(select(Workspace).where(Workspace.name == "Chess club"))
        member = await session.scalar(select(User).where(User.telegram_user_id == 111071))
        membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == member.id,
            )
        )

    assert workspace is not None
    assert member is not None
    assert membership is not None
    assert membership.role == WorkspaceRole.MEMBER.value
