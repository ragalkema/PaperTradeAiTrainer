import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from data_operations.domain.entities import (
    CollectionCheckpoint,
    CollectorHealthObservation,
    HealthStatus,
)
from data_operations.infrastructure.models import OperationsBase
from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
from shared.contracts import Candle, MarketSymbol
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_idempotent_candles_checkpoints_and_downtime() -> None:
    asyncio.run(_round_trip())


async def _round_trip() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(OperationsBase.metadata.create_all)
    repository = SqlAlchemyOperationsRepository(async_sessionmaker(engine, expire_on_commit=False))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    candle = Candle(
        MarketSymbol("BTC-EUR"),
        "1h",
        now,
        Decimal(1),
        Decimal(2),
        Decimal(1),
        Decimal(2),
        Decimal(3),
    )
    assert await repository.save_candles([candle]) == 1
    assert await repository.save_candles([candle]) == 0
    checkpoint = CollectionCheckpoint("market:BTC-EUR:1h", now, now)
    await repository.save_checkpoint(checkpoint)
    await repository.save_checkpoint(checkpoint)
    assert await repository.checkpoint(checkpoint.source) == checkpoint
    await repository.save_health(CollectorHealthObservation("news", now, HealthStatus.HEALTHY))
    await repository.save_health(
        CollectorHealthObservation(
            "news", now + timedelta(hours=1), HealthStatus.OFFLINE, error_category="shutdown"
        )
    )
    intervals = await repository.health_intervals("news", now, now + timedelta(hours=2))
    assert [x.status for x in intervals] == [HealthStatus.HEALTHY, HealthStatus.OFFLINE]
    await engine.dispose()
