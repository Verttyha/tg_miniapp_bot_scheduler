from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.models import TelegramChat, User, Workspace, WorkspaceMember, WorkspaceRole
from scheduler_app.services.common import ConflictError, NotFoundError, PermissionDeniedError


class WorkspaceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _normalize_owner_memberships(self, workspace: Workspace) -> Workspace:
        memberships = (
            await self.session.scalars(
                select(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace.id)
                .options(selectinload(WorkspaceMember.user))
            )
        ).all()
        changed = False
        for member in memberships:
            if member.role == WorkspaceRole.OWNER.value and member.user_id != workspace.owner_user_id:
                member.role = WorkspaceRole.ADMIN.value
                changed = True
        if changed:
            await self.session.flush()
        refreshed = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace.id)
            .options(
                selectinload(Workspace.members).selectinload(WorkspaceMember.user),
                selectinload(Workspace.telegram_chat),
            )
        )
        return refreshed or workspace

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

    async def auto_join_single_workspace(self, user: User) -> Workspace | None:
        existing_membership = await self.session.scalar(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        )
        if existing_membership:
            return None

        workspaces = (
            await self.session.scalars(
                select(Workspace).options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
            )
        ).all()
        if len(workspaces) != 1:
            return None

        workspace = workspaces[0]
        self.session.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.MEMBER.value,
            )
        )
        await self.session.flush()
        refreshed = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace.id)
            .options(selectinload(Workspace.members).selectinload(WorkspaceMember.user))
        )
        return refreshed or workspace

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

    async def list_owned_workspaces(self, user: User) -> list[Workspace]:
        workspaces = (
            await self.session.scalars(
                select(Workspace)
                .where(Workspace.owner_user_id == user.id)
                .options(
                    selectinload(Workspace.members).selectinload(WorkspaceMember.user),
                    selectinload(Workspace.telegram_chat),
                )
            )
        ).all()
        normalized_workspaces: list[Workspace] = []
        for workspace in workspaces:
            normalized_workspaces.append(await self._normalize_owner_memberships(workspace))
        return normalized_workspaces

    async def get_workspace_for_admin_management(
        self,
        *,
        actor: User,
        workspace_id: int,
    ) -> Workspace:
        workspace = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(
                selectinload(Workspace.members).selectinload(WorkspaceMember.user),
                selectinload(Workspace.telegram_chat),
            )
        )
        if not workspace:
            raise NotFoundError("Workspace not found")
        workspace = await self._normalize_owner_memberships(workspace)
        if workspace.owner_user_id != actor.id:
            raise PermissionDeniedError("Only the chat owner can manage admins")
        return workspace

    async def set_member_role(
        self,
        *,
        actor: User,
        workspace_id: int,
        target_user_id: int,
        role: str,
    ) -> Workspace:
        if role not in {WorkspaceRole.ADMIN.value, WorkspaceRole.MEMBER.value}:
            raise ConflictError("Unsupported role")

        workspace = await self.get_workspace_for_admin_management(actor=actor, workspace_id=workspace_id)
        target_membership = await self.session.scalar(
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
            )
            .options(selectinload(WorkspaceMember.user))
        )
        if not target_membership:
            raise NotFoundError("Participant not found")
        if target_membership.role == WorkspaceRole.OWNER.value:
            raise PermissionDeniedError("The chat owner role cannot be changed")

        target_membership.role = role
        await self.session.flush()
        refreshed = await self.session.scalar(
            select(Workspace)
            .where(Workspace.id == workspace.id)
            .options(
                selectinload(Workspace.members).selectinload(WorkspaceMember.user),
                selectinload(Workspace.telegram_chat),
            )
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
        created_workspace = False
        if not workspace:
            workspace = Workspace(name=title, owner_user_id=actor.id, telegram_chat_id=chat.id)
            self.session.add(workspace)
            await self.session.flush()
            created_workspace = True

        membership = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == actor.id,
            )
        )
        if not membership:
            role = (
                WorkspaceRole.OWNER.value
                if created_workspace or workspace.owner_user_id == actor.id
                else WorkspaceRole.MEMBER.value
            )
            self.session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=actor.id,
                    role=role,
                )
            )
            await self.session.flush()
        return await self._normalize_owner_memberships(workspace)
