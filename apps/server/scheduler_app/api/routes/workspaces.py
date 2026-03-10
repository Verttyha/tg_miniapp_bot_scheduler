from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.deps import get_current_user, get_session
from scheduler_app.models import User
from scheduler_app.schemas import WorkspaceRead
from scheduler_app.services.common import NotFoundError
from scheduler_app.services.presenters import workspace_read
from scheduler_app.services.workspaces import WorkspaceService


router = APIRouter()


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[WorkspaceRead]:
    service = WorkspaceService(session)
    workspaces = await service.list_for_user(current_user)
    return [workspace_read(workspace) for workspace in workspaces]


@router.post("/{workspace_id}/join", response_model=WorkspaceRead)
async def join_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceRead:
    service = WorkspaceService(session)
    try:
        workspace = await service.join_workspace(current_user, workspace_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return workspace_read(workspace)
