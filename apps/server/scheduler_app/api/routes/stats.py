from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.core.deps import get_current_user, get_session
from scheduler_app.domain.models import User
from scheduler_app.domain.schemas import StatsSummaryRead
from scheduler_app.services.common import NotFoundError
from scheduler_app.services.stats import StatsService


router = APIRouter()


@router.get("/{workspace_id}/stats", response_model=StatsSummaryRead)
async def workspace_stats(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StatsSummaryRead:
    service = StatsService(session)
    try:
        return await service.build_workspace_stats(current_user, workspace_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
