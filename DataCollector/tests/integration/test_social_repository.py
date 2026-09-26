import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.domain.entities import (
    RawSocialPost,
    SocialAccountCategory,
    SocialEngagementSnapshot,
    SocialEvent,
    SocialEventType,
    SocialIntelligence,
    SocialPostType,
    TrackedSocialAccount,
    VerificationStatus,
)
from data_collector.infrastructure.persistence import DataCollectorBase, SqlAlchemySocialRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.integration
def test_social_point_in_time_and_engagement_are_leakage_safe() -> None:
    asyncio.run(_roundtrip())


async def _roundtrip() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(DataCollectorBase.metadata.create_all)
    repo = SqlAlchemySocialRepository(async_sessionmaker(engine, expire_on_commit=False))
    created = datetime(2026, 9, 18, 13, 50, tzinfo=UTC)
    received = datetime(2026, 9, 18, 14, 5, tzinfo=UTC)
    account = TrackedSocialAccount(
        uuid4(),
        "x",
        "1",
        "alice",
        "Alice",
        True,
        SocialAccountCategory.ANALYST,
        1,
        created,
        created,
    )
    await repo.add_account(account)
    await repo.add_account(account)
    assert await repo.tracked_accounts() == (account,)
    raw = RawSocialPost(
        uuid4(), "x", "10", "1", "alice", "$BTC bullish", created, received, "a" * 64
    )
    event = SocialEvent(
        uuid4(),
        raw.raw_post_id,
        "x",
        account.account_id,
        "10",
        "alice",
        raw.text,
        created,
        received,
        received,
        "en",
        ("BTC",),
        {"BTC": Decimal(".95")},
        SocialPostType.ORIGINAL,
    )
    await repo.add_raw_social(raw)
    await repo.add_social_event(event)
    intel = SocialIntelligence(
        uuid4(),
        event.social_event_id,
        "BTC",
        Decimal(".95"),
        Decimal(".5"),
        Decimal(".8"),
        Decimal(".7"),
        SocialEventType.MARKET_OPINION,
        Decimal(".8"),
        Decimal("1"),
        Decimal(".5"),
        VerificationStatus.UNKNOWN,
        "s",
        "r",
        "i",
        "c",
        "n",
        "a",
        received,
    )
    await repo.add_social_intelligence(intel)
    early = SocialEngagementSnapshot(uuid4(), event.social_event_id, received, likes=100)
    late = SocialEngagementSnapshot(
        uuid4(), event.social_event_id, datetime(2026, 9, 18, 15, tzinfo=UTC), likes=10_000
    )
    await repo.add_engagement(early)
    await repo.add_engagement(late)
    assert (
        await repo.get_social_available_at(
            "BTC-EUR", datetime(2026, 9, 18, 14, tzinfo=UTC), timedelta(hours=1)
        )
        == ()
    )
    visible = await repo.get_social_available_at(
        "BTC-EUR", datetime(2026, 9, 18, 14, 10, tzinfo=UTC), timedelta(hours=1)
    )
    assert visible[0].engagement and visible[0].engagement.likes == 100
    await engine.dispose()
