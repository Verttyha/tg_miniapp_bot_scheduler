from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.models import Workspace, WorkspaceMember, WorkspaceRole


class ServiceError(Exception):
    pass


class NotFoundError(ServiceError):
    pass


class PermissionDeniedError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


async def get_workspace_member(
    session: AsyncSession,
    workspace_id: int,
    user_id: int,
) -> WorkspaceMember | None:
    return await session.scalar(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
        .options(selectinload(WorkspaceMember.workspace), selectinload(WorkspaceMember.user))
    )


async def get_workspace_for_user(
    session: AsyncSession,
    workspace_id: int,
    user_id: int,
) -> Workspace:
    membership = await get_workspace_member(session, workspace_id, user_id)
    if not membership:
        raise NotFoundError("Workspace not found for current user")
    return membership.workspace


def ensure_admin(member: WorkspaceMember) -> None:
    if member.role not in {WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value}:
        raise PermissionDeniedError("Admin access required")
