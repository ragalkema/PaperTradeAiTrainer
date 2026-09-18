from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.application.services.market_association import (
    CandleObservation,
    MarketAssociationService,
)
from data_collector.domain.entities import NewsEvent


@pytest.mark.unit
def test_association_uses_received_time_and_reports_observation_not_causality() -> None:
    received = datetime(2026, 9, 18, 12, tzinfo=UTC)
    event = NewsEvent(
        uuid4(),
        uuid4(),
        "s",
        "S",
        "BTC",
        "https://x",
        received - timedelta(hours=1),
        received,
        received,
        ("BTC",),
        {"BTC": Decimal(".8")},
        "en",
    )
    candles = (
        CandleObservation(
            "BTC-EUR", received - timedelta(minutes=1), Decimal("100"), Decimal("10")
        ),
        CandleObservation(
            "BTC-EUR", received + timedelta(minutes=5), Decimal("105"), Decimal("12")
        ),
    )
    result = MarketAssociationService().associate(event, candles, (5,))
    assert result[0].price_return == Decimal(".05")
    assert result[0].event_price == Decimal("100")
