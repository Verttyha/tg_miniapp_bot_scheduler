from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.core.deps import get_current_user, get_session, get_settings, get_cipher
from scheduler_app.core.security import TokenCipher
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import User
from scheduler_app.domain.schemas import AttendanceUpdateRequest, EventCreateRequest, EventRead, EventUpdateRequest
from scheduler_app.services.common import ConflictError, NotFoundError, PermissionDeniedError
from scheduler_app.services.events import EventService
from scheduler_app.services.presenters import event_read


router = APIRouter()


@router.get("/workspaces/{workspace_id}/events", response_model=list[EventRead])
async def list_events(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> list[EventRead]:
    service = EventService(session, settings, cipher)
    try:
        events = await service.list_events(current_user, workspace_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [event_read(event) for event in events]


@router.post("/workspaces/{workspace_id}/events", response_model=EventRead)
async def create_event(
    workspace_id: int,
    payload: EventCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> EventRead:
    service = EventService(session, settings, cipher)
    try:
        event = await service.create_event(current_user, workspace_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return event_read(event)


@router.get("/events/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> EventRead:
    service = EventService(session, settings, cipher)
    try:
        event = await service.get_event(current_user, event_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return event_read(event)


@router.patch("/events/{event_id}", response_model=EventRead)
async def update_event(
    event_id: int,
    payload: EventUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> EventRead:
    service = EventService(session, settings, cipher)
    try:
        event = await service.update_event(current_user, event_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return event_read(event)


@router.delete("/events/{event_id}", response_model=EventRead)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> EventRead:
    service = EventService(session, settings, cipher)
    try:
        event = await service.delete_event(current_user, event_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await session.commit()
    return event_read(event)


@router.post("/events/{event_id}/complete", response_model=EventRead)
async def complete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> EventRead:
    service = EventService(session, settings, cipher)
    try:
        event = await service.complete_event(current_user, event_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return event_read(event)


@router.post("/events/{event_id}/attendance", response_model=EventRead)
async def update_attendance(
    event_id: int,
    payload: AttendanceUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> EventRead:
    service = EventService(session, settings, cipher)
    try:
        event = await service.mark_attendance(current_user, event_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await session.commit()
    return event_read(event)
