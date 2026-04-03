from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scheduler_app.core.security import SecurityError, build_session_token, validate_telegram_init_data
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import User, Workspace, WorkspaceMember
from scheduler_app.domain.schemas import AuthResponse
from scheduler_app.services.common import ServiceError
from scheduler_app.services.presenters import user_read, workspace_read
from scheduler_app.services.workspaces import WorkspaceService


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings

    async def bootstrap_from_init_data(self, raw_init_data: str | None) -> AuthResponse:
        if raw_init_data:
            init_data = validate_telegram_init_data(
                raw_init_data,
                self.settings.bot_token,
                self.settings.telegram_init_data_ttl_seconds,
            )
            user = await self._upsert_user(init_data.user)
        elif self.settings.allow_insecure_dev_auth and self.settings.app_env == "development":
            user = await self._upsert_user(
                {
                    "id": 999000,
                    "username": "dev_user",
                    "first_name": "Local",
                    "last_name": "Dev",
                    "language_code": "en",
                }
            )
        else:
            raise SecurityError("Telegram init data required")

        await self.session.commit()
        await self.session.refresh(user)
        workspaces = await self._load_workspaces_for_user(user.id)
        if not workspaces:
            joined_workspace = await WorkspaceService(self.session).auto_join_single_workspace(user)
            if joined_workspace:
                await self.session.commit()
                workspaces = await self._load_workspaces_for_user(user.id)
        token = build_session_token(user.id, self.settings.app_secret)
        return AuthResponse(access_token=token, user=user_read(user), workspaces=[workspace_read(item) for item in workspaces])

    async def _upsert_user(self, user_payload: dict) -> User:
        telegram_user_id = int(user_payload["id"])
        user = await self.session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
        if not user:
            user = User(telegram_user_id=telegram_user_id)
            self.session.add(user)

        user.username = user_payload.get("username")
        user.first_name = user_payload.get("first_name")
        user.last_name = user_payload.get("last_name")
        user.language_code = user_payload.get("language_code")
        await self.session.flush()
        return user

    async def _load_workspaces_for_user(self, user_id: int) -> list[Workspace]:
        memberships = await self.session.scalars(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .options(
                selectinload(WorkspaceMember.workspace)
                .selectinload(Workspace.members)
                .selectinload(WorkspaceMember.user),
            )
        )
        return [item.workspace for item in memberships]
