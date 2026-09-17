"""Tests that the asynchronous persistence foundation is importable."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base
from app.database.session import async_session_factory, engine


def test_database_uses_async_components() -> None:
    assert Base.metadata.tables == {}
    assert async_session_factory.class_ is AsyncSession
    assert engine.url.drivername == "postgresql+asyncpg"
