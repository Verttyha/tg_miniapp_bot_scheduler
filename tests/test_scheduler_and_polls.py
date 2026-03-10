from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import authenticate, seed_workspace


async def test_scheduler_resolves_due_poll(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111201, "owner")
    participant = await authenticate(client, settings, 111202, "member")
    seeded = await seed_workspace(app, 111201, 111202)

    now = datetime.now(timezone.utc)
    create_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/polls",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Pick a slot",
            "description": "Vote for the best time",
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

    vote_response = await client.post(
        f"/api/polls/{poll_id}/vote",
        headers={"Authorization": f"Bearer {participant['access_token']}"},
        json={"option_id": first_option_id},
    )
    vote_response.raise_for_status()

    await app.state.scheduler.tick()

    poll_response = await client.get(
        f"/api/polls/{poll_id}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    poll_response.raise_for_status()
    payload = poll_response.json()

    assert payload["status"] == "finalized"
    assert payload["resulting_event_id"] is not None
