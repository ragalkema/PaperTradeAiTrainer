"""Shared trading-contract invariants."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from shared.contracts import ActionType, BotAction, MarketState, TradeResult


@pytest.mark.unit
def test_market_state_requires_point_in_time_values() -> None:
    state = MarketState("BTC-EUR", datetime.now(UTC), Decimal("100000"))
    assert state.symbol == "BTC-EUR"
    with pytest.raises(ValueError, match="positive"):
        MarketState("BTC-EUR", datetime.now(UTC), Decimal("0"))
    with pytest.raises(ValueError, match="timezone-aware"):
        MarketState("BTC-EUR", datetime.now(), Decimal("1"))


@pytest.mark.unit
def test_actions_and_results_enforce_quantities() -> None:
    assert BotAction(ActionType.HOLD).quantity == 0
    with pytest.raises(ValueError, match="zero quantity"):
        BotAction(ActionType.HOLD, Decimal("1"))
    with pytest.raises(ValueError, match="positive"):
        TradeResult(True, ActionType.BUY, Decimal("1"), Decimal("0"))
