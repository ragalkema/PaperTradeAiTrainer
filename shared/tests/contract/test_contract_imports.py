"""Public shared contracts remain importable from one stable surface."""

import pytest
from shared.contracts import ActionType, BotAction, MarketState, TradeResult


@pytest.mark.contract
def test_public_contract_surface() -> None:
    assert {ActionType, BotAction, MarketState, TradeResult}
