from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.core.security import SecurityError, TokenCipher, build_oauth_state, read_oauth_state
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import CalendarConnection, ConnectionStatus, User
from scheduler_app.domain.schemas import IntegrationUpdateRequest
from scheduler_app.integrations.google import GoogleCalendarProvider
from scheduler_app.integrations.yandex import YandexCalendarProvider
from scheduler_app.services.common import NotFoundError, PermissionDeniedError, ServiceError


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
            raise NotFoundError("Неизвестный провайдер календаря")
        return self.providers[provider]

    async def build_connect_link(self, user: User, provider: str) -> str:
        if provider == "google" and (not self.settings.google_client_id or not self.settings.google_client_secret):
            raise ServiceError("Интеграция Google не настроена. Укажите GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET.")
        if provider == "yandex" and (not self.settings.yandex_client_id or not self.settings.yandex_client_secret):
            raise ServiceError("Интеграция Yandex не настроена. Укажите YANDEX_CLIENT_ID и YANDEX_CLIENT_SECRET.")
        state = build_oauth_state(user.id, provider, self.settings.app_secret)
        return await self.get_provider(provider).build_authorize_url(state)

    async def handle_callback(self, provider: str, code: str, state: str) -> CalendarConnection:
        decoded = read_oauth_state(state, self.settings.app_secret)
        if decoded["provider"] != provider:
            raise PermissionDeniedError("Провайдер OAuth не совпадает с сохраненным состоянием")
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
        if tokens.refresh_token:
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
                try:
                    await self.ensure_fresh_connection(connection)
                    if connection.status == ConnectionStatus.ACTIVE.value:
                        calendars = await self.get_provider(connection.provider).list_calendars(connection)
                        if not calendars:
                            connection.status = ConnectionStatus.ERROR.value
                            await self.session.flush()
                except (httpx.HTTPError, SecurityError):
                    connection.status = ConnectionStatus.ERROR.value
                    await self.session.flush()
            result.append((connection, calendars))
        await self.session.commit()
        return result

    async def list_google_events(self, user: User) -> list[dict]:
        connection = await self.session.scalar(
            select(CalendarConnection).where(
                CalendarConnection.user_id == user.id,
                CalendarConnection.provider == "google",
            )
        )
        if not connection or connection.status != ConnectionStatus.ACTIVE.value:
            return []
        await self.ensure_fresh_connection(connection)
        if connection.status != ConnectionStatus.ACTIVE.value:
            await self.session.commit()
            return []
        try:
            events = await self.get_provider("google").list_events(connection)
        except (httpx.HTTPError, SecurityError) as exc:
            connection.status = ConnectionStatus.ERROR.value
            await self.session.commit()
            raise ServiceError("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u044f Google Calendar") from exc
        await self.session.commit()
        return events

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
            raise NotFoundError("Подключение календаря не найдено")
        if payload.calendar_id is not None:
            connection.calendar_id = payload.calendar_id
        if payload.calendar_name is not None:
            connection.calendar_name = payload.calendar_name
        if payload.status is not None:
            allowed_statuses = {status.value for status in ConnectionStatus}
            if payload.status not in allowed_statuses:
                raise PermissionDeniedError("Неподдерживаемый статус подключения календаря")
            connection.status = payload.status
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def ensure_fresh_connection(self, connection: CalendarConnection) -> CalendarConnection:
        if connection.token_expires_at and as_utc(connection.token_expires_at) <= datetime.now(timezone.utc):
            try:
                refreshed = await self.get_provider(connection.provider).refresh_tokens(connection)
            except (httpx.HTTPError, SecurityError):
                connection.status = ConnectionStatus.ERROR.value
                await self.session.flush()
                return connection
            if refreshed:
                connection.access_token_encrypted = self.cipher.encrypt(refreshed.access_token)
                if refreshed.refresh_token:
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
