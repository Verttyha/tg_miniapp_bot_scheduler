from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import caldav
import httpx
from icalendar import Calendar, Event as IcsEvent

from scheduler_app.integrations.base import ProviderEventRef, ProviderTokens
from scheduler_app.models import CalendarConnection, Event, ExternalEventMapping, User
from scheduler_app.security import TokenCipher
from scheduler_app.settings import Settings


class YandexCalendarProvider:
    provider_name = "yandex"

    def __init__(self, settings: Settings, cipher: TokenCipher):
        self.settings = settings
        self.cipher = cipher

    async def build_authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.yandex_client_id,
                "redirect_uri": self.settings.yandex_redirect_uri,
                "state": state,
                "scope": self.settings.yandex_scopes,
                "force_confirm": "yes",
            }
        )
        return f"https://oauth.yandex.com/authorize?{query}"

    async def exchange_code(self, code: str) -> ProviderTokens:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://oauth.yandex.com/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.settings.yandex_client_id,
                    "client_secret": self.settings.yandex_client_secret,
                },
            )
            response.raise_for_status()
            payload = response.json()
            info = await client.get(
                "https://login.yandex.ru/info",
                params={"format": "json"},
                headers={"Authorization": f"OAuth {payload['access_token']}"},
            )
            info.raise_for_status()
            account = info.json()
        expires_at = None
        if payload.get("expires_in"):
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload["expires_in"]))
        email = account.get("default_email")
        emails = account.get("emails") or []
        return ProviderTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            account_email=email or (emails[0] if emails else None),
            provider_metadata={"login": account.get("login")},
        )

    async def refresh_tokens(self, connection: CalendarConnection) -> ProviderTokens | None:
        refresh_token = self.cipher.decrypt(connection.refresh_token_encrypted)
        if not refresh_token:
            return None
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://oauth.yandex.com/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.settings.yandex_client_id,
                    "client_secret": self.settings.yandex_client_secret,
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
        client = self._client(connection)
        principal = client.principal()
        calendars = []
        for calendar in principal.calendars():
            label = calendar.get_display_name() if hasattr(calendar, "get_display_name") else None
            calendars.append({"id": str(calendar.url), "name": label or str(calendar.url)})
        return calendars

    async def create_event(self, connection: CalendarConnection, event: Event, participant: User) -> ProviderEventRef:
        calendar = self._resolve_calendar(connection)
        saved = calendar.save_event(self._build_ics(event, participant))
        return ProviderEventRef(external_calendar_id=str(calendar.url), external_event_id=str(saved.url))

    async def update_event(
        self,
        connection: CalendarConnection,
        mapping: ExternalEventMapping,
        event: Event,
        participant: User,
    ) -> ProviderEventRef:
        calendar = self._resolve_calendar(connection, calendar_url=mapping.external_calendar_id)
        resource = calendar.event_by_url(mapping.external_event_id)
        resource.data = self._build_ics(event, participant)
        resource.save()
        return ProviderEventRef(external_calendar_id=str(calendar.url), external_event_id=str(resource.url))

    async def delete_event(self, connection: CalendarConnection, mapping: ExternalEventMapping) -> None:
        calendar = self._resolve_calendar(connection, calendar_url=mapping.external_calendar_id)
        resource = calendar.event_by_url(mapping.external_event_id)
        resource.delete()

    def _client(self, connection: CalendarConnection) -> caldav.DAVClient:
        token = self.cipher.decrypt(connection.access_token_encrypted)
        return caldav.DAVClient(
            url="https://caldav.yandex.ru/",
            username=connection.account_email,
            password=token,
        )

    def _resolve_calendar(self, connection: CalendarConnection, *, calendar_url: str | None = None):
        client = self._client(connection)
        principal = client.principal()
        if calendar_url:
            return principal.calendar(url=calendar_url)
        if connection.calendar_id:
            return principal.calendar(url=connection.calendar_id)
        calendars = principal.calendars()
        if not calendars:
            raise RuntimeError("No Yandex calendars available")
        return calendars[0]

    def _build_ics(self, event: Event, participant: User) -> str:
        calendar = Calendar()
        calendar.add("prodid", "-//Telegram Scheduler//EN")
        calendar.add("version", "2.0")

        component = IcsEvent()
        component.add("uid", f"workspace-event-{event.id}-user-{participant.id}")
        component.add("summary", event.title)
        component.add("description", event.description or "")
        component.add("location", event.location or "")
        component.add("dtstart", event.start_at)
        component.add("dtend", event.end_at)
        component.add("dtstamp", datetime.now(timezone.utc))
        calendar.add_component(component)
        return calendar.to_ical().decode("utf-8")
