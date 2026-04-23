from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from scheduler_app.domain.models import CalendarConnection, Event, ExternalEventMapping, User


@dataclass(slots=True)
class ProviderTokens:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    account_email: str | None = None
    provider_metadata: dict | None = None


@dataclass(slots=True)
class ProviderEventRef:
    external_calendar_id: str
    external_event_id: str


class CalendarProvider(Protocol):
    provider_name: str

    async def build_authorize_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str) -> ProviderTokens: ...
    async def refresh_tokens(self, connection: CalendarConnection) -> ProviderTokens | None: ...
    async def list_calendars(self, connection: CalendarConnection) -> list[dict[str, str]]: ...
    async def create_event(self, connection: CalendarConnection, event: Event, participant: User) -> ProviderEventRef: ...
    async def update_event(
        self,
        connection: CalendarConnection,
        mapping: ExternalEventMapping,
        event: Event,
        participant: User,
    ) -> ProviderEventRef: ...
    async def delete_event(self, connection: CalendarConnection, mapping: ExternalEventMapping) -> None: ...
