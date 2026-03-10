from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.models import TelegramChat, User, Workspace, WorkspaceMember, WorkspaceRole
from scheduler_app.services.common import NotFoundError


class WorkspaceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user: User) -> list[Workspace]:
        memberships = await self.session.scalars(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == user.id)
            .options(
                selectinload(WorkspaceMember.workspace)
                .selectinload(Workspace.members)
                .selectinload(WorkspaceMember.user),
                selectinload(WorkspaceMember.workspace).selectinload(Workspace.telegram_chat),
            )
        )
        return [item.workspace for item in memberships]

    async def join_workspace(self, user: User, workspace_id: int) -> Workspace:
        workspace = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        )
        if not workspace:
            raise NotFoundError("Workspace not found")
        membership = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
        if not membership:
            membership = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.MEMBER.value,
            )
            self.session.add(membership)
            await self.session.flush()
        refreshed = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace.id)
            .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        )
        return refreshed or workspace

    async def ensure_group_workspace(
        self,
        *,
        actor: User,
        telegram_chat_id: int,
        title: str,
        chat_type: str,
    ) -> Workspace:
        chat = await self.session.scalar(
            select(TelegramChat).where(TelegramChat.telegram_chat_id == telegram_chat_id)
        )
        if not chat:
            chat = TelegramChat(
                telegram_chat_id=telegram_chat_id,
                title=title,
                chat_type=chat_type,
            )
            self.session.add(chat)
            await self.session.flush()
        else:
            chat.title = title
            chat.chat_type = chat_type

        workspace = await self.session.scalar(
            select(Workspace)
            .where(Workspace.telegram_chat_id == chat.id)
            .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        )
        if not workspace:
            workspace = Workspace(name=title, owner_user_id=actor.id, telegram_chat_id=chat.id)
            self.session.add(workspace)
            await self.session.flush()

        owner_membership = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == actor.id,
            )
        )
        if not owner_membership:
            self.session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=actor.id,
                    role=WorkspaceRole.OWNER.value,
                )
            )
            await self.session.flush()
        return workspace
