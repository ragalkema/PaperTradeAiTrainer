"""Asynchronous SQLAlchemy session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from paper_trading.infrastructure.configuration import get_settings

# NullPool keeps the shared factory safe for CLI calls and Dashboard worker event loops.
engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
