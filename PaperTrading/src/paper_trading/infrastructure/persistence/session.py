"""Asynchronous SQLAlchemy session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from paper_trading.infrastructure.configuration import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
