import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.domain.entities import (
    NewsEvent,
    NewsSource,
    NewsSourceKind,
    RawNewsItem,
    RawNewsStatus,
)
from data_collector.infrastructure.persistence import DataCollectorBase, SqlAlchemyNewsRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.integration
def test_repository_persists_and_queries_normalized_news() -> None:
    asyncio.run(_repository_round_trip())


async def _repository_round_trip() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(DataCollectorBase.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repository = SqlAlchemyNewsRepository(sessions)
    now = datetime(2026, 9, 18, 12, tzinfo=UTC)
    source = NewsSource("test", "Test", NewsSourceKind.RSS, True, 1, 60, "https://test/rss")
    raw = RawNewsItem(uuid4(), "test", "BTC news", "https://test/a", now, now, "a" * 64)
    event = NewsEvent(
        uuid4(),
        raw.raw_item_id,
        "test",
        "Test",
        raw.title,
        raw.url,
        now,
        now,
        now,
        ("BTC",),
        {"BTC": Decimal("0.8")},
        "en",
        duplicate_group_id=uuid4(),
    )
    await repository.register_source(source)
    assert await repository.add_raw(raw)
    assert not await repository.add_raw(raw)
    assert await repository.add_event(event)
    await repository.set_raw_status(raw.raw_item_id, RawNewsStatus.PROCESSED)
    assert await repository.recent_news(since=now, asset="BTC") == (event,)
    assert await repository.recent_news(since=now, asset="ETH") == ()
    assert (await repository.sources())[0].source_id == "test"
    await engine.dispose()
