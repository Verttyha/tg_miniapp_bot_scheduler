from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.deps import get_current_user, get_session, get_settings, get_cipher
from scheduler_app.models import User
from scheduler_app.schemas import CalendarConnectionRead, IntegrationLinkResponse, IntegrationUpdateRequest
from scheduler_app.security import SecurityError, TokenCipher
from scheduler_app.services.common import NotFoundError, PermissionDeniedError
from scheduler_app.services.integrations import IntegrationService
from scheduler_app.services.presenters import connection_read
from scheduler_app.settings import Settings


router = APIRouter(prefix="/integrations")
oauth_router = APIRouter()


@router.get("", response_model=list[CalendarConnectionRead])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> list[CalendarConnectionRead]:
    service = IntegrationService(session, settings, cipher)
    connections = await service.list_connections(current_user)
    return [connection_read(connection, calendars=calendars) for connection, calendars in connections]


@router.post("/google/connect", response_model=IntegrationLinkResponse)
async def connect_google(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> IntegrationLinkResponse:
    service = IntegrationService(session, settings, cipher)
    url = await service.build_connect_link(current_user, "google")
    return IntegrationLinkResponse(authorize_url=url, provider="google")


@router.post("/yandex/connect", response_model=IntegrationLinkResponse)
async def connect_yandex(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> IntegrationLinkResponse:
    service = IntegrationService(session, settings, cipher)
    url = await service.build_connect_link(current_user, "yandex")
    return IntegrationLinkResponse(authorize_url=url, provider="yandex")


@router.patch("/{connection_id}", response_model=CalendarConnectionRead)
async def update_integration(
    connection_id: int,
    payload: IntegrationUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> CalendarConnectionRead:
    service = IntegrationService(session, settings, cipher)
    try:
        connection = await service.update_connection(current_user, connection_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    calendars = await service.get_provider(connection.provider).list_calendars(connection)
    return connection_read(connection, calendars=calendars)


@oauth_router.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> HTMLResponse:
    service = IntegrationService(session, settings, cipher)
    try:
        connection = await service.handle_callback("google", code, state)
    except (SecurityError, PermissionDeniedError, NotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return HTMLResponse(
        f"<html><body><h1>Google Calendar connected</h1><p>{connection.account_email or 'Account'} is ready.</p></body></html>"
    )


@oauth_router.get("/oauth/yandex/callback", response_class=HTMLResponse)
async def yandex_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> HTMLResponse:
    service = IntegrationService(session, settings, cipher)
    try:
        connection = await service.handle_callback("yandex", code, state)
    except (SecurityError, PermissionDeniedError, NotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return HTMLResponse(
        f"<html><body><h1>Yandex Calendar connected</h1><p>{connection.account_email or 'Account'} is ready.</p></body></html>"
    )
