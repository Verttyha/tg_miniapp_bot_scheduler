from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx

from scheduler_app.integrations.base import ProviderEventRef, ProviderTokens
from scheduler_app.models import CalendarConnection, Event, ExternalEventMapping, User
from scheduler_app.security import TokenCipher
from scheduler_app.settings import Settings


class GoogleCalendarProvider:
    provider_name = "google"

    def __init__(self, settings: Settings, cipher: TokenCipher):
        self.settings = settings
        self.cipher = cipher

    async def build_authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_redirect_uri,
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
                "scope": self.settings.google_scopes,
                "state": state,
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code(self, code: str) -> ProviderTokens:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            payload = response.json()
            userinfo = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {payload['access_token']}"},
            )
            userinfo.raise_for_status()
            email = userinfo.json().get("email")

        expires_at = None
        if payload.get("expires_in"):
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload["expires_in"]))
        return ProviderTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            account_email=email,
            provider_metadata={"scope": payload.get("scope")},
        )

    async def refresh_tokens(self, connection: CalendarConnection) -> ProviderTokens | None:
        refresh_token = self.cipher.decrypt(connection.refresh_token_encrypted)
        if not refresh_token:
            return None
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            payload = response.json()
        expires_at = None
        if payload.get("expires_in"):
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload["expires_in"]))
        return ProviderTokens(
            access_token=payload["access_token"],
            refresh_token=refresh_token,
            expires_at=expires_at,
            account_email=connection.account_email,
            provider_metadata=connection.provider_metadata,
        )

    async def list_calendars(self, connection: CalendarConnection) -> list[dict[str, str]]:
        token = self.cipher.decrypt(connection.access_token_encrypted)
        if not token:
            return []
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            items = response.json().get("items", [])
        return [{"id": item["id"], "name": item.get("summary", item["id"])} for item in items]

    async def create_event(self, connection: CalendarConnection, event: Event, participant: User) -> ProviderEventRef:
        token = self.cipher.decrypt(connection.access_token_encrypted)
        calendar_id = quote(connection.calendar_id or "primary", safe="")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                json=self._event_body(event, participant),
            )
            response.raise_for_status()
            payload = response.json()
        return ProviderEventRef(
            external_calendar_id=connection.calendar_id or "primary",
            external_event_id=payload["id"],
        )

    async def update_event(
        self,
        connection: CalendarConnection,
        mapping: ExternalEventMapping,
        event: Event,
        participant: User,
    ) -> ProviderEventRef:
        token = self.cipher.decrypt(connection.access_token_encrypted)
        calendar_id = quote(mapping.external_calendar_id, safe="")
        event_id = quote(mapping.external_event_id, safe="")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=self._event_body(event, participant),
            )
            response.raise_for_status()
            payload = response.json()
        return ProviderEventRef(
            external_calendar_id=mapping.external_calendar_id,
            external_event_id=payload["id"],
        )

    async def delete_event(self, connection: CalendarConnection, mapping: ExternalEventMapping) -> None:
        token = self.cipher.decrypt(connection.access_token_encrypted)
        calendar_id = quote(mapping.external_calendar_id, safe="")
        event_id = quote(mapping.external_event_id, safe="")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()

    def _event_body(self, event: Event, participant: User) -> dict:
        return {
            "summary": event.title,
            "description": event.description or "",
            "location": event.location or "",
            "start": {"dateTime": event.start_at.isoformat(), "timeZone": event.timezone_name},
            "end": {"dateTime": event.end_at.isoformat(), "timeZone": event.timezone_name},
            "extendedProperties": {
                "private": {
                    "participant_telegram_user_id": str(participant.telegram_user_id or ""),
                    "workspace_event_id": str(event.id),
                }
            },
        }
