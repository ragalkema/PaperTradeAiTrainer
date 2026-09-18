import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.domain.entities import (
    NewsEvent,
    NewsEventType,
    NewsIntelligence,
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
    intelligence = NewsIntelligence(
        uuid4(),
        event.news_event_id,
        "BTC",
        Decimal("0.8"),
        Decimal("0.4"),
        Decimal("0.7"),
        Decimal("0.9"),
        Decimal("0.8"),
        NewsEventType.ETF,
        Decimal("0.8"),
        (),
        Decimal("1"),
        Decimal("0.8"),
        uuid4(),
        "sent-v1",
        "imp-v1",
        "class-v1",
        "nov-v1",
        now,
    )
    assert await repository.add_intelligence(intelligence)
    assert not await repository.add_intelligence(intelligence)
    later_time = now + timedelta(minutes=5)
    later_raw = RawNewsItem(
        uuid4(),
        "test",
        "Later BTC news",
        "https://test/b",
        now - timedelta(hours=1),
        later_time,
        "b" * 64,
    )
    later_event = NewsEvent(
        uuid4(),
        later_raw.raw_item_id,
        "test",
        "Test",
        later_raw.title,
        later_raw.url,
        later_raw.published_at,
        later_time,
        later_time,
        ("BTC",),
        {"BTC": Decimal("0.8")},
        "en",
        duplicate_group_id=uuid4(),
    )
    await repository.add_raw(later_raw)
    await repository.add_event(later_event)
    await repository.add_intelligence(
        NewsIntelligence(
            uuid4(),
            later_event.news_event_id,
            "BTC",
            Decimal("0.8"),
            Decimal("0.1"),
            Decimal("0.7"),
            Decimal("0.5"),
            Decimal("0.7"),
            NewsEventType.OTHER,
            Decimal("0.5"),
            (),
            Decimal("1"),
            Decimal("0.8"),
            uuid4(),
            "sent-v1",
            "imp-v1",
            "class-v1",
            "nov-v1",
            later_time,
        )
    )
    visible = await repository.get_news_available_at("BTC-EUR", now, timedelta(hours=1))
    hidden = await repository.get_news_available_at(
        "BTC-EUR", now - timedelta(seconds=1), timedelta(hours=1)
    )
    assert visible[0].event.news_event_id == event.news_event_id
    assert len(visible) == 1  # Later receipt stays hidden despite its earlier published_at.
    assert hidden == ()
    await engine.dispose()
