from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.application.services.social_intelligence import (
    account_influence,
    analyze_social,
    normalize_social,
)
from data_collector.domain.entities import (
    RawSocialPost,
    SocialAccountCategory,
    SocialPostType,
    TrackedSocialAccount,
)


def account(now: datetime) -> TrackedSocialAccount:
    return TrackedSocialAccount(
        uuid4(),
        "x",
        "1",
        "alice",
        "Alice",
        True,
        SocialAccountCategory.ANALYST,
        10,
        now,
        now,
        followers=100_000,
        typical_engagement=Decimal("500"),
        posts_per_day=Decimal("5"),
    )


def raw(text: str, created: datetime, received: datetime, **refs: object) -> RawSocialPost:
    return RawSocialPost(
        uuid4(), "x", str(uuid4()), "1", "alice", text, created, received, "a" * 64, **refs
    )


@pytest.mark.unit
def test_social_assets_cashtags_post_type_and_asset_sentiment() -> None:
    now = datetime(2026, 9, 18, 14, tzinfo=UTC)
    acct = account(now)
    event = normalize_social(
        raw("$ETH looks stronger than $BTC", now, now, quote_of="9"), acct, now
    )
    assert event.post_type is SocialPostType.QUOTE and event.asset_relevance["ETH"] == Decimal(
        "0.95"
    )
    results = {x.asset: x for x in analyze_social(event, acct, (), now)}
    assert results["ETH"].sentiment > results["BTC"].sentiment
    assert results["ETH"].importance > 0 and results["ETH"].influence_version


@pytest.mark.unit
def test_social_novelty_is_chronological_and_reposts_are_discounted() -> None:
    now = datetime(2026, 9, 18, 14, tzinfo=UTC)
    acct = account(now)
    first = normalize_social(raw("Bitcoin ETF approved", now, now), acct, now)
    later = normalize_social(
        raw("Bitcoin ETF approved today", now, now + timedelta(minutes=20), repost_of="1"),
        acct,
        now + timedelta(minutes=20),
    )
    assert analyze_social(first, acct, (later,), now)[0].novelty == 1
    assert analyze_social(later, acct, (first,), later.processed_at)[0].novelty == Decimal("0.2")
    assert account_influence(acct)[0] < 1


@pytest.mark.unit
def test_social_future_timestamp_is_rejected() -> None:
    now = datetime(2026, 9, 18, 14, tzinfo=UTC)
    with pytest.raises(ValueError, match="future"):
        normalize_social(raw("BTC", now + timedelta(hours=1), now), account(now), now)
