from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scheduler_app.domain.models import User


async def ensure_telegram_user(session: AsyncSession, telegram_user: TelegramUser) -> User:
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_user.id))
    if not user:
        user = User(telegram_user_id=telegram_user.id)
        session.add(user)
    user.username = telegram_user.username
    user.first_name = telegram_user.first_name
    user.last_name = telegram_user.last_name
    user.language_code = telegram_user.language_code
    await session.flush()
    return user
