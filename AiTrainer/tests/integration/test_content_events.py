import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ai_trainer.infrastructure.datasets.content_events import read_content_events
from data_collector.infrastructure.persistence.models import (
    DataCollectorBase,
    NewsEventModel,
    SocialEventModel,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_database_export_both_sources_excludes_not_yet_processed_content():
    asyncio.run(roundtrip())


async def roundtrip():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(DataCollectorBase.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    cutoff = start + timedelta(days=1)
    async with sessions.begin() as session:
        session.add(
            NewsEventModel(
                news_event_id=uuid4(),
                raw_item_id=uuid4(),
                source_id="rss",
                source_name="RSS",
                title="ETH announcement",
                summary="Details",
                url="https://example.test/story",
                published_at=start,
                received_at=start,
                processed_at=start,
                mentioned_assets=["ETH"],
                asset_relevance={"ETH": "1"},
                language="en",
            )
        )
        for provider, processed in (
            ("x", start),
            ("x", cutoff + timedelta(hours=1)),
            ("other", start),
        ):
            session.add(
                SocialEventModel(
                    social_event_id=uuid4(),
                    raw_post_id=uuid4(),
                    provider=provider,
                    source_account_id=uuid4(),
                    external_post_id=str(uuid4()),
                    username="author",
                    text="ETH post",
                    created_at=start,
                    received_at=start,
                    processed_at=processed,
                    language="en",
                    mentioned_assets=["ETH"],
                    asset_relevance={"ETH": "1"},
                    post_type="original",
                )
            )
    events = await read_content_events(sessions, start, cutoff, cutoff)
    assert len(events) == 2
    assert {event.source_type for event in events} == {"news", "x"}
    assert events[0].text == "ETH announcement\nDetails"
    assert events[1].text == "ETH post"
    assert all(event.available_at == start for event in events)
    assert not await read_content_events(sessions, cutoff, cutoff + timedelta(days=1), cutoff)
    await engine.dispose()
