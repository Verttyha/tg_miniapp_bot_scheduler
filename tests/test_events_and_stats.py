from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from scheduler_app.domain.models import CalendarConnection, ConnectionStatus, User
from scheduler_app.integrations.base import ProviderTokens
from scheduler_app.integrations.google import GoogleCalendarProvider
from scheduler_app.services.integrations import IntegrationService
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


async def test_calendar_connection_accepts_naive_token_expiry(client, app, settings):
    await authenticate(client, settings, 111113, "calendar-owner")

    async with app.state.session_factory() as session:
        user = await session.scalar(select(User).where(User.telegram_user_id == 111113))
        connection = CalendarConnection(
            user_id=user.id,
            provider="google",
            status=ConnectionStatus.ACTIVE.value,
            token_expires_at=datetime.now() + timedelta(hours=1),
        )
        session.add(connection)
        await session.flush()

        service = IntegrationService(session, settings, app.state.cipher)
        await service.ensure_fresh_connection(connection)


async def test_integrations_list_refreshes_expired_google_token(client, app, settings, monkeypatch):
    owner = await authenticate(client, settings, 111114, "calendar-refresh")
    refreshed_until = datetime.now(timezone.utc) + timedelta(hours=1)

    async def fake_refresh(self, connection):
        return ProviderTokens(
            access_token="fresh-access",
            refresh_token="existing-refresh",
            expires_at=refreshed_until,
            account_email="calendar@example.com",
        )

    async def fake_list_calendars(self, connection):
        assert app.state.cipher.decrypt(connection.access_token_encrypted) == "fresh-access"
        return [{"id": "primary", "name": "Primary"}]

    monkeypatch.setattr(GoogleCalendarProvider, "refresh_tokens", fake_refresh)
    monkeypatch.setattr(GoogleCalendarProvider, "list_calendars", fake_list_calendars)

    async with app.state.session_factory() as session:
        user = await session.scalar(select(User).where(User.telegram_user_id == 111114))
        session.add(
            CalendarConnection(
                user_id=user.id,
                provider="google",
                status=ConnectionStatus.ACTIVE.value,
                account_email="calendar@example.com",
                access_token_encrypted=app.state.cipher.encrypt("expired-access"),
                refresh_token_encrypted=app.state.cipher.encrypt("existing-refresh"),
                token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        await session.commit()

    response = await client.get(
        "/api/integrations",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )

    response.raise_for_status()
    [connection] = response.json()
    assert connection["status"] == "active"
    assert connection["calendars"] == [{"id": "primary", "name": "Primary"}]
