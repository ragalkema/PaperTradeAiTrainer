from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.application.services.news_features import calculate_features
from data_collector.domain.entities import (
    NewsEvent,
    NewsEventType,
    NewsIntelligence,
    OnlineNewsItem,
)


def item(received: datetime, sentiment: str, importance: str = "0.8") -> OnlineNewsItem:
    event = NewsEvent(
        uuid4(),
        uuid4(),
        "s",
        "S",
        "BTC news",
        "https://x",
        received,
        received,
        received,
        ("BTC",),
        {"BTC": Decimal("0.9")},
        "en",
    )
    intel = NewsIntelligence(
        uuid4(),
        event.news_event_id,
        "BTC",
        Decimal("0.9"),
        Decimal(sentiment),
        Decimal("0.8"),
        Decimal(importance),
        Decimal("0.8"),
        NewsEventType.ETF,
        Decimal("0.8"),
        (),
        Decimal("1"),
        Decimal("0.8"),
        uuid4(),
        "s1",
        "i1",
        "c1",
        "n1",
        received,
    )
    return OnlineNewsItem(event, intel)


@pytest.mark.unit
def test_features_are_reproducible_and_have_no_retrospective_fields() -> None:
    time = datetime(2026, 1, 1, 14, tzinfo=UTC)
    items = (item(time - timedelta(minutes=5), "0.5"), item(time - timedelta(minutes=30), "-0.2"))
    first = calculate_features("BTC-EUR", time, items, time)
    second = calculate_features("BTC-EUR", time, items, time)
    assert first == second
    assert first.news_count_15m == 1 and first.news_count_1h == 2
    assert first.relevance_weighted_sentiment_1h is not None
    forbidden = {"impact", "return", "volume", "volatility"}
    assert not any(any(word in field for word in forbidden) for field in first.__dataclass_fields__)
