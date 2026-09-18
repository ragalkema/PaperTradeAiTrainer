"""Async DataCollector database session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from data_collector.infrastructure.configuration import get_data_collector_settings

engine = create_async_engine(
    get_data_collector_settings().database_url, pool_pre_ping=True, poolclass=NullPool
)
data_collector_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
