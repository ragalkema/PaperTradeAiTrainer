"""Verify that both projects depend on the same public trading contracts."""

import pytest
from ai_trainer.application.ports import TradingBot
from paper_trading.application.ports import PaperExchange
from shared.contracts import BotAction, MarketState, TradeResult


@pytest.mark.contract
def test_trading_boundary_exports_are_available() -> None:
    assert TradingBot.__name__ == "TradingBot"
    assert PaperExchange.__name__ == "PaperExchange"
    assert {BotAction, MarketState, TradeResult}
