from paper_trading.infrastructure.configuration import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

operations_engine = create_async_engine(
    get_settings().database_url, pool_pre_ping=True, poolclass=NullPool
)
operations_session_factory = async_sessionmaker(
    operations_engine, class_=AsyncSession, expire_on_commit=False
)
