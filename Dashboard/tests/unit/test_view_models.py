from datetime import UTC, datetime
from decimal import Decimal

import pytest
from dashboard.application.view_models import ConnectionState, MarketSummary


@pytest.mark.unit
def test_market_spread_handles_missing_and_computes_relative_value() -> None:
    assert MarketSummary("BTC-EUR").spread_percent is None
    market = MarketSummary(
        "BTC-EUR",
        datetime.now(UTC),
        Decimal("101"),
        bid=Decimal("100"),
        ask=Decimal("101"),
        state=ConnectionState.CONNECTED,
    )
    assert market.spread_percent == Decimal("0.01")
