from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from scheduler_app.core.settings import Settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


def build_engine(settings: Settings):
    settings.resolved_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(settings.resolved_database_url, future=True, echo=False)


def build_sessionmaker(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = build_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
