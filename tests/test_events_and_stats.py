from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


async def test_event_creation_requires_at_least_one_participant(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111103, "owner-empty")
    await authenticate(client, settings, 111104, "member-empty")
    seeded = await seed_workspace(app, 111103, 111104)

    response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Empty participants",
            "start_at": future_iso(2),
            "end_at": future_iso(3),
            "timezone_name": "UTC",
            "participant_ids": [],
        },
    )

    assert response.status_code == 422


async def test_event_update_keeps_time_without_timezone_shift(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111105, "owner-time")
    await authenticate(client, settings, 111106, "member-time")
    seeded = await seed_workspace(app, 111105, 111106)
    start_at = datetime(2026, 4, 23, 18, 0, tzinfo=timezone.utc)
    end_at = start_at + timedelta(hours=1)

    create_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Timezone check",
            "description": "Before update",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "timezone_name": "Europe/Moscow",
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
        },
    )
    create_response.raise_for_status()
    event_id = create_response.json()["id"]
    original_start = create_response.json()["start_at"]
    original_end = create_response.json()["end_at"]

    update_response = await client.patch(
        f"/api/events/{event_id}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={"title": "Timezone check updated"},
    )
    update_response.raise_for_status()
    payload = update_response.json()

    assert payload["start_at"] == original_start
    assert payload["end_at"] == original_end


async def test_event_update_rejects_empty_participants(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111107, "owner-update")
    await authenticate(client, settings, 111108, "member-update")
    seeded = await seed_workspace(app, 111107, 111108)

    create_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Cannot remove all",
            "start_at": future_iso(2),
            "end_at": future_iso(3),
            "timezone_name": "UTC",
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
        },
    )
    create_response.raise_for_status()
    event_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/events/{event_id}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={"participant_ids": []},
    )

    assert update_response.status_code == 422


async def test_delete_event_is_soft_and_not_listed(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111109, "owner-delete")
    await authenticate(client, settings, 111110, "member-delete")
    seeded = await seed_workspace(app, 111109, 111110)

    create_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Soft delete me",
            "start_at": future_iso(2),
            "end_at": future_iso(3),
            "timezone_name": "UTC",
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
        },
    )
    create_response.raise_for_status()
    event_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/events/{event_id}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    delete_response.raise_for_status()
    assert delete_response.json()["status"] == "cancelled"

    list_response = await client.get(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    list_response.raise_for_status()
    event_ids = {item["id"] for item in list_response.json()}
    assert event_id not in event_ids


async def test_complete_event_marks_status_and_keeps_event_in_list(client, app, settings, telegram_mock):
    owner = await authenticate(client, settings, 111111, "owner-complete")
    await authenticate(client, settings, 111112, "member-complete")
    seeded = await seed_workspace(app, 111111, 111112)

    create_response = await client.post(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={
            "title": "Complete me",
            "start_at": future_iso(2),
            "end_at": future_iso(3),
            "timezone_name": "UTC",
            "participant_ids": [seeded["owner_id"], seeded["participant_id"]],
        },
    )
    create_response.raise_for_status()
    event_id = create_response.json()["id"]

    complete_response = await client.post(
        f"/api/events/{event_id}/complete",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    complete_response.raise_for_status()
    assert complete_response.json()["status"] == "completed"

    list_response = await client.get(
        f"/api/workspaces/{seeded['workspace_id']}/events",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    list_response.raise_for_status()
    statuses = {item["id"]: item["status"] for item in list_response.json()}
    assert statuses[event_id] == "completed"
