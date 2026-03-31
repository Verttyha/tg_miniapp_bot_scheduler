from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select

from scheduler_app.models import TelegramChatPoll
from tests.conftest import authenticate, seed_workspace


async def test_create_poll_publishes_telegram_chat_poll(client, app, settings):
    owner = await authenticate(client, settings, 111201, "owner")
    participant = await authenticate(client, settings, 111202, "member")
    seeded = await seed_workspace(app, 111201, 111202)

    app.state.bot.send_poll = AsyncMock(
        return_value=SimpleNamespace(
            message_id=501,
            poll=SimpleNamespace(id="tg-poll-1"),
        )
    )

    now = datetime.now(timezone.utc)
    response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/polls",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Pick a slot",
            "description": "Vote for the best time",
            "timezone_name": "UTC",
            "deadline_at": (now + timedelta(hours=2)).isoformat(),
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
            "options": [
                {
                    "label": "Morning",
                    "start_at": (now + timedelta(hours=3)).isoformat(),
                    "end_at": (now + timedelta(hours=4)).isoformat(),
                },
                {
                    "label": "Evening",
                    "start_at": (now + timedelta(hours=6)).isoformat(),
                    "end_at": (now + timedelta(hours=7)).isoformat(),
                },
            ],
        },
    )
    response.raise_for_status()
    payload = response.json()

    assert payload["has_chat_poll"] is True
    app.state.bot.send_poll.assert_awaited_once()

    async with app.state.session_factory() as session:
        chat_poll = await session.scalar(
            select(TelegramChatPoll).where(TelegramChatPoll.poll_id == payload["id"])
        )

    assert chat_poll is not None
    assert chat_poll.telegram_poll_id == "tg-poll-1"
    assert chat_poll.telegram_message_id == 501


async def test_scheduler_resolves_due_chat_poll_from_telegram_answers(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111211, "owner2")
    await authenticate(client, settings, 111212, "member2")
    seeded = await seed_workspace(app, 111211, 111212)

    app.state.bot.send_poll = AsyncMock(
        return_value=SimpleNamespace(
            message_id=777,
            poll=SimpleNamespace(id="tg-poll-2"),
        )
    )
    app.state.bot.stop_poll = AsyncMock(return_value=SimpleNamespace(id="tg-poll-2"))
    app.state.bot.send_message = AsyncMock(return_value=None)

    now = datetime.now(timezone.utc)
    create_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/polls",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Choose the meetup time",
            "description": "Final slot will become the event",
            "timezone_name": "UTC",
            "deadline_at": (now - timedelta(minutes=5)).isoformat(),
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
            "options": [
                {
                    "label": "Morning",
                    "start_at": (now + timedelta(hours=2)).isoformat(),
                    "end_at": (now + timedelta(hours=3)).isoformat(),
                },
                {
                    "label": "Evening",
                    "start_at": (now + timedelta(hours=6)).isoformat(),
                    "end_at": (now + timedelta(hours=7)).isoformat(),
                },
            ],
        },
    )
    create_response.raise_for_status()
    poll_id = create_response.json()["id"]
    first_option_id = create_response.json()["options"][0]["id"]

    poll_answer_response = await client.post(
        "/webhooks/telegram",
        json={
            "update_id": 100500,
            "poll_answer": {
                "poll_id": "tg-poll-2",
                "option_ids": [0],
                "user": {
                    "id": 111212,
                    "is_bot": False,
                    "first_name": "Member2",
                    "username": "member2",
                    "language_code": "en",
                },
            },
        },
    )
    poll_answer_response.raise_for_status()

    vote_response = await client.post(
        f"/api/polls/{poll_id}/vote",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={"option_id": first_option_id},
    )
    assert vote_response.status_code == 403
    assert vote_response.json()["detail"] == "Vote in the Telegram chat poll"

    poll_response = await client.get(
        f"/api/polls/{poll_id}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    poll_response.raise_for_status()
    payload = poll_response.json()

    assert payload["status"] == "finalized"
    assert payload["resulting_event_id"] is not None
    assert payload["selected_option_id"] == first_option_id
    app.state.bot.stop_poll.assert_awaited_once()
    assert app.state.bot.send_message.await_count >= 1
