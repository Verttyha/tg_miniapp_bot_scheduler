from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.core.deps import get_bot, get_current_user, get_session, get_settings, get_cipher
from scheduler_app.core.security import TokenCipher
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import User
from scheduler_app.domain.schemas import PollCreateRequest, PollRead, PollResolveRequest, VoteRequest
from scheduler_app.services.common import NotFoundError, PermissionDeniedError, ServiceError
from scheduler_app.services.polls import PollService
from scheduler_app.services.presenters import poll_read


router = APIRouter()


@router.get("/workspaces/{workspace_id}/polls", response_model=list[PollRead])
async def list_polls(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> list[PollRead]:
    service = PollService(session, settings, cipher)
    try:
        polls = await service.list_polls(current_user, workspace_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [poll_read(poll) for poll in polls]


@router.post("/workspaces/{workspace_id}/polls", response_model=PollRead)
async def create_poll(
    workspace_id: int,
    payload: PollCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
    bot: Bot = Depends(get_bot),
) -> PollRead:
    service = PollService(session, settings, cipher, bot=bot)
    try:
        poll = await service.create_poll(current_user, workspace_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await session.commit()
    return poll_read(poll)


@router.get("/polls/{poll_id}", response_model=PollRead)
async def get_poll(
    poll_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> PollRead:
    service = PollService(session, settings, cipher)
    try:
        poll, user_vote = await service.get_poll(current_user, poll_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return poll_read(poll, user_vote_option_id=user_vote)


@router.post("/polls/{poll_id}/vote", response_model=PollRead)
async def vote_on_poll(
    poll_id: int,
    payload: VoteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
) -> PollRead:
    service = PollService(session, settings, cipher)
    try:
        poll = await service.vote(current_user, poll_id, payload)
        _, user_vote = await service.get_poll(current_user, poll_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    await session.commit()
    return poll_read(poll, user_vote_option_id=user_vote)


@router.post("/polls/{poll_id}/resolve", response_model=PollRead)
async def resolve_poll(
    poll_id: int,
    payload: PollResolveRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    cipher: TokenCipher = Depends(get_cipher),
    bot: Bot = Depends(get_bot),
) -> PollRead:
    service = PollService(session, settings, cipher, bot=bot)
    try:
        poll = await service.resolve(current_user, poll_id, payload)
        _, user_vote = await service.get_poll(current_user, poll_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await session.commit()
    return poll_read(poll, user_vote_option_id=user_vote)
