from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.deps import get_session, get_settings
from scheduler_app.schemas import AuthInitDataRequest, AuthResponse
from scheduler_app.security import SecurityError
from scheduler_app.services.auth import AuthService
from scheduler_app.settings import Settings


router = APIRouter()


@router.post("/telegram/init-data", response_model=AuthResponse)
async def bootstrap_auth(
    payload: AuthInitDataRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    service = AuthService(session, settings)
    try:
        return await service.bootstrap_from_init_data(payload.init_data)
    except SecurityError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
