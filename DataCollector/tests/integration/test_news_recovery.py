import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from data_collector.application.services.normalization import NewsNormalizer
from data_collector.domain.entities import NewsSource, NewsSourceKind, RawNewsItem
from data_collector.infrastructure.persistence import DataCollectorBase, SqlAlchemyNewsRepository
from data_collector.infrastructure.persistence.models import NewsEventModel, RawNewsItemModel
from data_collector.infrastructure.persistence.recovery import recover_pending_news
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_recovery_preserves_original_times_handles_partial_commit_and_is_idempotent():
    asyncio.run(recovery_roundtrip())


async def recovery_roundtrip():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(DataCollectorBase.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repo = SqlAlchemyNewsRepository(sessions)
    await repo.register_source(
        NewsSource("test", "Test", NewsSourceKind.RSS, True, 1, 60, "https://example.test/feed")
    )
    old = datetime(2026, 1, 1, tzinfo=UTC)
    now = old + timedelta(days=5)
    items = []
    for i, title in enumerate(
        ("BTC original", "ETH recovered", "BTC original", "SOL future", "Recent BTC")
    ):
        received = now if i == 4 else old
        published = now if i == 3 else received
        raw = RawNewsItem(
            uuid4(), "test", title, f"https://example.test/{i}", published, received, str(i) * 64
        )
        await repo.add_raw(raw)
        items.append(raw)
    # Event commit succeeded, but raw status update was interrupted.
    first = NewsNormalizer().normalize(items[0], "Test", old + timedelta(hours=1))
    await repo.add_event(first)
    preview = await recover_pending_news(sessions, now=now)
    assert len(preview) == 4
    async with sessions() as session:
        assert all(
            r.status == "received" for r in (await session.scalars(select(RawNewsItemModel)))
        )
    result = await recover_pending_news(sessions, now=now, apply=True)
    assert [r["status"] for r in sorted(result, key=lambda r: r["status"])] == [
        "duplicate",
        "processed",
        "processed",
        "quarantined",
    ]
    assert await recover_pending_news(sessions, now=now, apply=True) == []
    async with sessions() as session:
        events = (await session.scalars(select(NewsEventModel))).all()
        assert len(events) == 2
        for event in events:
            assert event.received_at.replace(tzinfo=UTC) == old
            expected = first.processed_at if event.raw_item_id == items[0].raw_item_id else now
            assert event.processed_at.replace(tzinfo=UTC) == expected
        for item in items:
            raw = await session.get(RawNewsItemModel, item.raw_item_id)
            assert raw.received_at.replace(tzinfo=UTC) == item.received_at
            assert raw.published_at.replace(tzinfo=UTC) == item.published_at
            assert raw.content_hash == item.content_hash
    await engine.dispose()
