from __future__ import annotations

from tests.conftest import authenticate, future_iso, seed_workspace


async def test_event_creation_and_stats(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111101, "owner")
    participant = await authenticate(client, settings, 111102, "member")
    seeded = await seed_workspace(app, 111101, 111102)

    event_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Team sync",
            "description": "Status review",
            "location": "Telegram voice chat",
            "start_at": future_iso(2),
            "end_at": future_iso(3),
            "timezone_name": "UTC",
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
        },
    )
    event_response.raise_for_status()
    event_id = event_response.json()["id"]

    attendance_response = await client.post(
        f"/api/events/{event_id}/attendance",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "records": [
                {"user_id": seeded["owner_id"], "status": "present"},
                {"user_id": seeded["participant_id"], "status": "absent"},
            ]
        },
    )
    attendance_response.raise_for_status()

    stats_response = await client.get(
        f"/api/workspaces/{seeded['workspace_id']}/stats",
        headers={"Authorization": f"Bearer {participant['access_token']}"},
    )
    stats_response.raise_for_status()
    entries = stats_response.json()["entries"]

    assert len(entries) == 2
    assert any(entry["attended"] == 1 for entry in entries)
    assert any(entry["missed"] == 1 for entry in entries)
