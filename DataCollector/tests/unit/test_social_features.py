from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.application.services.social_features import calculate_social_features
from data_collector.domain.entities import (
    OnlineSocialItem,
    SocialEngagementSnapshot,
    SocialEvent,
    SocialEventType,
    SocialIntelligence,
    SocialPostType,
    VerificationStatus,
)


def item(time: datetime, likes: int) -> OnlineSocialItem:
    event = SocialEvent(
        uuid4(),
        uuid4(),
        "x",
        uuid4(),
        "1",
        "alice",
        "$BTC bullish",
        time,
        time,
        time,
        "en",
        ("BTC",),
        {"BTC": Decimal(".95")},
        SocialPostType.ORIGINAL,
    )
    intel = SocialIntelligence(
        uuid4(),
        event.social_event_id,
        "BTC",
        Decimal(".95"),
        Decimal(".5"),
        Decimal(".8"),
        Decimal(".8"),
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
        time,
    )
    engagement = SocialEngagementSnapshot(
        uuid4(), event.social_event_id, time + timedelta(minutes=5), likes=likes
    )
    return OnlineSocialItem(event, intel, engagement)


@pytest.mark.unit
def test_social_features_are_reproducible_and_online_only() -> None:
    now = datetime(2026, 9, 18, 14, tzinfo=UTC)
    items = (item(now - timedelta(minutes=10), 100),)
    first = calculate_social_features("BTC-EUR", now, items, now)
    second = calculate_social_features("BTC-EUR", now, items, now)
    assert (
        first == second and first.post_count_15m == 1 and first.engagement_velocity_1h is not None
    )
    assert not any("impact" in name or "return" in name for name in first.__dataclass_fields__)
