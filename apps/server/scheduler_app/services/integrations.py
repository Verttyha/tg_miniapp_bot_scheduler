from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.core.security import TokenCipher, build_oauth_state, read_oauth_state
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import CalendarConnection, ConnectionStatus, User
from scheduler_app.domain.schemas import IntegrationUpdateRequest
from scheduler_app.integrations.google import GoogleCalendarProvider
from scheduler_app.integrations.yandex import YandexCalendarProvider
from scheduler_app.services.common import NotFoundError, PermissionDeniedError


class IntegrationService:
    def __init__(self, session: AsyncSession, settings: Settings, cipher: TokenCipher):
        self.session = session
        self.settings = settings
        self.cipher = cipher
        self.providers = {
            "google": GoogleCalendarProvider(settings, cipher),
            "yandex": YandexCalendarProvider(settings, cipher),
        }

    def get_provider(self, provider: str):
        if provider not in self.providers:
            raise NotFoundError("Unknown calendar provider")
        return self.providers[provider]

    async def build_connect_link(self, user: User, provider: str) -> str:
        state = build_oauth_state(user.id, provider, self.settings.app_secret)
        return await self.get_provider(provider).build_authorize_url(state)

    async def handle_callback(self, provider: str, code: str, state: str) -> CalendarConnection:
        decoded = read_oauth_state(state, self.settings.app_secret)
        if decoded["provider"] != provider:
            raise PermissionDeniedError("OAuth state provider mismatch")
        user_id = int(decoded["sub"])
        provider_impl = self.get_provider(provider)
        tokens = await provider_impl.exchange_code(code)

        connection = await self.session.scalar(
            select(CalendarConnection).where(
                CalendarConnection.user_id == user_id,
                CalendarConnection.provider == provider,
            )
        )
        if not connection:
            connection = CalendarConnection(user_id=user_id, provider=provider)
            self.session.add(connection)

        connection.status = ConnectionStatus.ACTIVE.value
        connection.account_email = tokens.account_email
        connection.access_token_encrypted = self.cipher.encrypt(tokens.access_token)
        connection.refresh_token_encrypted = self.cipher.encrypt(tokens.refresh_token)
        connection.token_expires_at = tokens.expires_at
        connection.provider_metadata = tokens.provider_metadata
        await self.session.flush()

        calendars = await provider_impl.list_calendars(connection)
        if calendars and not connection.calendar_id:
            connection.calendar_id = calendars[0]["id"]
            connection.calendar_name = calendars[0]["name"]
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def list_connections(self, user: User) -> list[tuple[CalendarConnection, list[dict[str, str]]]]:
        records = await self.session.scalars(
            select(CalendarConnection).where(CalendarConnection.user_id == user.id)
        )
        result = []
        for connection in records:
            calendars = []
            if connection.status == ConnectionStatus.ACTIVE.value:
                calendars = await self.get_provider(connection.provider).list_calendars(connection)
            result.append((connection, calendars))
        return result

    async def update_connection(
        self,
        user: User,
        connection_id: int,
        payload: IntegrationUpdateRequest,
    ) -> CalendarConnection:
        connection = await self.session.scalar(
            select(CalendarConnection).where(CalendarConnection.id == connection_id)
        )
        if not connection or connection.user_id != user.id:
            raise NotFoundError("Calendar connection not found")
        if payload.calendar_id is not None:
            connection.calendar_id = payload.calendar_id
        if payload.calendar_name is not None:
            connection.calendar_name = payload.calendar_name
        if payload.status is not None:
            connection.status = payload.status
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def ensure_fresh_connection(self, connection: CalendarConnection) -> CalendarConnection:
        if connection.token_expires_at and connection.token_expires_at <= datetime.now(timezone.utc):
            refreshed = await self.get_provider(connection.provider).refresh_tokens(connection)
            if refreshed:
                connection.access_token_encrypted = self.cipher.encrypt(refreshed.access_token)
                connection.refresh_token_encrypted = self.cipher.encrypt(refreshed.refresh_token)
                connection.token_expires_at = refreshed.expires_at
                connection.account_email = refreshed.account_email or connection.account_email
                connection.provider_metadata = refreshed.provider_metadata or connection.provider_metadata
                await self.session.flush()
        return connection

    async def get_active_connection_for_user(self, user_id: int) -> CalendarConnection | None:
        connection = await self.session.scalar(
            select(CalendarConnection).where(
                CalendarConnection.user_id == user_id,
                CalendarConnection.status == ConnectionStatus.ACTIVE.value,
            )
        )
        if connection:
            await self.ensure_fresh_connection(connection)
        return connection
