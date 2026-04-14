from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters.chat_member_updated import ADMINISTRATOR, ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message, PollAnswer, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import async_sessionmaker

from scheduler_app.bot.service import ensure_telegram_user
from scheduler_app.core.security import TokenCipher
from scheduler_app.core.settings import Settings
from scheduler_app.domain.models import Workspace, WorkspaceMember, WorkspaceRole
from scheduler_app.services.common import ConflictError, NotFoundError, PermissionDeniedError
from scheduler_app.services.polls import PollService
from scheduler_app.services.workspaces import WorkspaceService

TELEGRAM_ANONYMOUS_ADMIN_ID = 1087968824
GROUP_CONNECT_CALLBACK_DATA = "workspace:connect"


def build_router(session_factory: async_sessionmaker, settings: Settings) -> Router:
    router = Router()
    mini_app_url = f"{settings.base_url.rstrip('/')}/app"
    cipher = TokenCipher(settings.app_secret)

    async def resolve_bot_username(message: Message) -> str | None:
        configured_username = settings.bot_username.strip().lstrip("@")
        if configured_username and configured_username.lower() != "replace-me":
            return configured_username
        try:
            me = await message.bot.get_me()
        except TelegramAPIError:
            return None
        return me.username

    async def safe_answer_callback(
        callback: CallbackQuery,
        text: str | None = None,
        *,
        show_alert: bool = False,
    ) -> None:
        try:
            await callback.answer(text, show_alert=show_alert)
        except TelegramAPIError:
            return

    def format_user_name(member: WorkspaceMember) -> str:
        user = member.user
        if user.first_name:
            full_name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
            if full_name:
                return full_name
        if user.username:
            return f"@{user.username}"
        return f"User {user.id}"

    def member_role_rank(member: WorkspaceMember) -> int:
        if member.role == WorkspaceRole.OWNER.value:
            return 0
        if member.role == WorkspaceRole.ADMIN.value:
            return 1
        return 2

    def sort_members(members: list[WorkspaceMember]) -> list[WorkspaceMember]:
        return sorted(
            members,
            key=lambda member: (
                member_role_rank(member),
                format_user_name(member).casefold(),
            ),
        )

    def build_start_markup(bot_username: str | None) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Открыть календарь",
                        web_app=WebAppInfo(url=mini_app_url),
                    )
                ],
                *(
                    [
                        [
                            InlineKeyboardButton(
                                text="Добавить в чат",
                                url=f"https://t.me/{bot_username}?startgroup=setup",
                            )
                        ]
                    ]
                    if bot_username
                    else []
                ),
                [InlineKeyboardButton(text="Админы чатов", callback_data="admins:menu")],
            ]
        )

    def build_group_connect_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Подключиться",
                        callback_data=GROUP_CONNECT_CALLBACK_DATA,
                    ),
                    InlineKeyboardButton(
                        text="Вступить",
                        callback_data=GROUP_CONNECT_CALLBACK_DATA,
                    ),
                ]
            ]
        )

    def build_group_welcome_text(chat_title: str | None) -> str:
        if chat_title:
            intro = f"Привет! Я помогу вести общий календарь чата «{chat_title}»."
        else:
            intro = "Привет! Я помогу вести общий календарь этого чата."
        return (
            f"{intro}\n"
            "Нажмите «Подключиться» или «Вступить», чтобы присоединиться к календарю."
        )

    def build_group_connected_text(workspace_name: str, *, is_owner: bool) -> str:
        if is_owner:
            return (
                f"Чат «{workspace_name}» подключён. "
                "Вы стали владельцем календаря и можете назначать администраторов через /admins в личке бота."
            )
        return (
            f"Вы вступили в календарь чата «{workspace_name}». "
            "Теперь события и голосования будут доступны в Mini App."
        )

    def build_owned_workspaces_markup(workspaces: list[Workspace]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for workspace in workspaces:
            builder.button(
                text=workspace.name,
                callback_data=f"admins:ws:{workspace.id}",
            )
        builder.adjust(1)
        return builder.as_markup()

    def build_workspace_admin_markup(workspace: Workspace) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for member in sort_members(workspace.members):
            if member.role == WorkspaceRole.OWNER.value:
                continue
            next_role = (
                WorkspaceRole.MEMBER.value
                if member.role == WorkspaceRole.ADMIN.value
                else WorkspaceRole.ADMIN.value
            )
            action = "Снять админа" if member.role == WorkspaceRole.ADMIN.value else "Сделать админом"
            builder.button(
                text=f"{action}: {format_user_name(member)}",
                callback_data=f"admins:set:{workspace.id}:{member.user.id}:{next_role}",
            )
        builder.button(text="К списку чатов", callback_data="admins:menu")
        builder.adjust(1)
        return builder.as_markup()

    def build_owned_workspaces_text() -> str:
        return (
            "Выберите чат, где хотите настроить администраторов.\n\n"
            "Назначать админов может тот, кто первым подключил бота к чату."
        )

    def build_workspace_admin_text(workspace: Workspace) -> str:
        sorted_members = sort_members(workspace.members)
        owner = next((member for member in sorted_members if member.role == WorkspaceRole.OWNER.value), None)
        admins = [format_user_name(member) for member in sorted_members if member.role == WorkspaceRole.ADMIN.value]
        managed_members = [member for member in sorted_members if member.role != WorkspaceRole.OWNER.value]

        lines = [f"Управление администраторами чата «{workspace.name}»", ""]
        if owner:
            lines.append(f"Владелец: {format_user_name(owner)}")
        lines.append(f"Админы: {', '.join(admins) if admins else 'пока нет'}")
        lines.append("")
        lines.append("Ниже можно назначить или снять администраторов.")
        lines.append("В списке видны участники, которые уже открывали бота или Mini App.")
        if not managed_members:
            lines.extend(
                [
                    "",
                    "Пока нет участников, доступных для настройки ролей.",
                ]
            )
        return "\n".join(lines)

    async def load_owned_workspaces(message_user) -> list[Workspace]:
        async with session_factory() as session:
            actor = await ensure_telegram_user(session, message_user)
            workspaces = await WorkspaceService(session).list_owned_workspaces(actor)
            await session.commit()
        return workspaces

    async def load_workspace_for_management(message_user, workspace_id: int) -> Workspace:
        async with session_factory() as session:
            actor = await ensure_telegram_user(session, message_user)
            workspace = await WorkspaceService(session).get_workspace_for_admin_management(
                actor=actor,
                workspace_id=workspace_id,
            )
            await session.commit()
        return workspace

    async def update_workspace_member_role(message_user, workspace_id: int, target_user_id: int, role: str) -> Workspace:
        async with session_factory() as session:
            actor = await ensure_telegram_user(session, message_user)
            workspace = await WorkspaceService(session).set_member_role(
                actor=actor,
                workspace_id=workspace_id,
                target_user_id=target_user_id,
                role=role,
            )
            await session.commit()
        return workspace

    async def send_owned_workspaces_menu(target: Message, message_user) -> None:
        workspaces = await load_owned_workspaces(message_user)
        if not workspaces:
            await target.answer(
                "Пока нет чатов, где вы являетесь владельцем календаря. "
                "Подключите бота в нужный чат первым, и здесь появится управление администраторами."
            )
            return
        await target.answer(
            build_owned_workspaces_text(),
            reply_markup=build_owned_workspaces_markup(workspaces),
        )

    async def send_workspace_admin_panel(target: Message, message_user, workspace_id: int) -> None:
        workspace = await load_workspace_for_management(message_user, workspace_id)
        await target.answer(
            build_workspace_admin_text(workspace),
            reply_markup=build_workspace_admin_markup(workspace),
        )

    async def ensure_group_workspace_for_actor(
        *,
        actor_user,
        chat_id: int,
        chat_title: str | None,
        chat_type: str,
    ) -> tuple[Workspace, bool]:
        async with session_factory() as session:
            actor = await ensure_telegram_user(session, actor_user)
            workspace = await WorkspaceService(session).ensure_group_workspace(
                actor=actor,
                telegram_chat_id=chat_id,
                title=chat_title or "Group workspace",
                chat_type=chat_type,
            )
            is_owner = workspace.owner_user_id == actor.id
            await session.commit()
        return workspace, is_owner

    async def ensure_group_workspace(message: Message) -> None:
        if (
            not message.from_user
            or message.from_user.is_bot
            or message.from_user.id == TELEGRAM_ANONYMOUS_ADMIN_ID
        ):
            try:
                await message.answer(
                    "Не удалось назначить владельца календаря автоматически. "
                    "Нажмите кнопку «Подключиться» или «Вступить» ниже с обычного аккаунта администратора.",
                    reply_markup=build_group_connect_markup(),
                )
            except TelegramAPIError:
                return
            return

        workspace, is_owner = await ensure_group_workspace_for_actor(
            actor_user=message.from_user,
            chat_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
        )

        try:
            await message.answer(
                build_group_connected_text(workspace.name, is_owner=is_owner)
            )
        except TelegramAPIError:
            return

    @router.message(CommandStart(), F.chat.type == "private")
    async def start_handler(message: Message) -> None:
        if not message.from_user:
            return
        async with session_factory() as session:
            await ensure_telegram_user(session, message.from_user)
            await session.commit()
        bot_username = await resolve_bot_username(message)
        try:
            await message.answer(
                "Открой календарь, чтобы подключить календари и управлять общим расписанием. "
                "Если нужен календарь для группы, добавь бота в чат — первый подключивший участник "
                "станет владельцем и сможет назначать администраторов через /admins.",
                reply_markup=build_start_markup(bot_username),
            )
        except TelegramAPIError:
            return

    @router.message(Command("admins"), F.chat.type == "private")
    async def admins_command_handler(message: Message) -> None:
        if not message.from_user:
            return
        try:
            await send_owned_workspaces_menu(message, message.from_user)
        except TelegramAPIError:
            return

    @router.callback_query(F.data == "admins:menu")
    async def admins_menu_callback(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message:
            return
        await safe_answer_callback(callback)
        try:
            await send_owned_workspaces_menu(callback.message, callback.from_user)
        except TelegramAPIError:
            return

    @router.callback_query(F.data.startswith("admins:ws:"))
    async def admins_workspace_callback(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message or not callback.data:
            return
        try:
            workspace_id = int(callback.data.split(":")[2])
        except (IndexError, ValueError):
            await safe_answer_callback(callback, "Не удалось открыть чат", show_alert=True)
            return

        try:
            await send_workspace_admin_panel(callback.message, callback.from_user, workspace_id)
        except NotFoundError:
            await safe_answer_callback(callback, "Чат не найден", show_alert=True)
            return
        except PermissionDeniedError:
            await safe_answer_callback(callback, "Только владелец чата может назначать админов", show_alert=True)
            return
        except TelegramAPIError:
            return

        await safe_answer_callback(callback)

    @router.callback_query(F.data.startswith("admins:set:"))
    async def admins_set_role_callback(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message or not callback.data:
            return
        try:
            _, _, workspace_id_text, target_user_id_text, role = callback.data.split(":")
            workspace_id = int(workspace_id_text)
            target_user_id = int(target_user_id_text)
        except (ValueError, IndexError):
            await safe_answer_callback(callback, "Не удалось изменить роль", show_alert=True)
            return

        try:
            workspace = await update_workspace_member_role(
                callback.from_user,
                workspace_id,
                target_user_id,
                role,
            )
        except NotFoundError:
            await safe_answer_callback(callback, "Участник или чат не найден", show_alert=True)
            return
        except PermissionDeniedError as exc:
            await safe_answer_callback(callback, str(exc), show_alert=True)
            return
        except ConflictError:
            await safe_answer_callback(callback, "Неподдерживаемая роль", show_alert=True)
            return
        except TelegramAPIError:
            return

        notice = "Администратор назначен" if role == WorkspaceRole.ADMIN.value else "Права администратора сняты"
        await safe_answer_callback(callback, notice)
        try:
            await callback.message.answer(
                build_workspace_admin_text(workspace),
                reply_markup=build_workspace_admin_markup(workspace),
            )
        except TelegramAPIError:
            return

    @router.callback_query(F.data == GROUP_CONNECT_CALLBACK_DATA)
    async def group_connect_callback(callback: CallbackQuery) -> None:
        if not callback.from_user:
            return
        if callback.from_user.is_bot or callback.from_user.id == TELEGRAM_ANONYMOUS_ADMIN_ID:
            await safe_answer_callback(callback, "Подключение доступно только для обычных пользователей", show_alert=True)
            return
        if not callback.message:
            await safe_answer_callback(callback, "Не удалось определить чат", show_alert=True)
            return
        if callback.message.chat.type not in {"group", "supergroup"}:
            await safe_answer_callback(callback, "Эта кнопка работает только в группах", show_alert=True)
            return

        workspace, is_owner = await ensure_group_workspace_for_actor(
            actor_user=callback.from_user,
            chat_id=callback.message.chat.id,
            chat_title=callback.message.chat.title,
            chat_type=callback.message.chat.type,
        )
        await safe_answer_callback(
            callback,
            "Чат подключён" if is_owner else "Вы подключились к чату",
        )
        try:
            await callback.message.answer(
                build_group_connected_text(workspace.name, is_owner=is_owner)
            )
        except TelegramAPIError:
            return

    @router.message(CommandStart(), F.chat.type.in_({"group", "supergroup"}))
    async def start_group_handler(message: Message) -> None:
        await ensure_group_workspace(message)

    @router.message(Command("setup"), F.chat.type.in_({"group", "supergroup"}))
    async def setup_workspace(message: Message) -> None:
        await ensure_group_workspace(message)

    @router.poll_answer()
    async def poll_answer_handler(answer: PollAnswer) -> None:
        if not answer.user:
            return
        async with session_factory() as session:
            service = PollService(session, settings, cipher)
            await service.sync_telegram_poll_answer(answer)
            await session.commit()

    @router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
    async def bot_removed_from_chat_handler(update: ChatMemberUpdated) -> None:
        if update.chat.type not in {"group", "supergroup"}:
            return
        async with session_factory() as session:
            await WorkspaceService(session).detach_workspace_for_chat(
                telegram_chat_id=update.chat.id
            )
            await session.commit()

    @router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER | ADMINISTRATOR))
    async def bot_added_to_chat_handler(update: ChatMemberUpdated) -> None:
        if update.chat.type not in {"group", "supergroup"}:
            return

        if (
            update.from_user
            and not update.from_user.is_bot
            and update.from_user.id != TELEGRAM_ANONYMOUS_ADMIN_ID
        ):
            async with session_factory() as session:
                actor = await ensure_telegram_user(session, update.from_user)
                await WorkspaceService(session).ensure_group_workspace(
                    actor=actor,
                    telegram_chat_id=update.chat.id,
                    title=update.chat.title or "Group workspace",
                    chat_type=update.chat.type,
                )
                await session.commit()

        try:
            await update.bot.send_message(
                chat_id=update.chat.id,
                text=build_group_welcome_text(update.chat.title),
                reply_markup=build_group_connect_markup(),
            )
        except TelegramAPIError:
            return

    return router
