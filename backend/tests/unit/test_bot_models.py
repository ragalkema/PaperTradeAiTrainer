"""Tests for bot domain invariants."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.bots.models import ActionType, BotAction, MarketState


def test_hold_action_defaults_to_zero_quantity() -> None:
    assert BotAction(action=ActionType.HOLD).quantity == Decimal("0")


def test_market_state_rejects_non_positive_price() -> None:
    with pytest.raises(ValidationError):
        MarketState(
            symbol="BTC-EUR",
            observed_at=datetime.now(UTC),
            price=Decimal("0"),
        )
