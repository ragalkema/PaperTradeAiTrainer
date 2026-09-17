"""End-to-end deterministic profitable and losing paper scenarios."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from paper_trading.application.services import PaperTradingSession
from shared.contracts import BotAction, MarketState, MarketSymbol

MARKET = MarketSymbol("BTC-EUR")


def observation(price: str, minute: int) -> MarketState:
    value = Decimal(price)
    return MarketState(
        MARKET, datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minute), value, value, value
    )


@pytest.mark.simulation
@pytest.mark.parametrize(("exit_price", "is_profit"), [("105000", True), ("95000", False)])
def test_complete_round_trip_preserves_accounting(exit_price: str, is_profit: bool) -> None:
    session = PaperTradingSession(Decimal("10000"), Decimal("0.0025"), Decimal("0.0005"))
    session.update_market(observation("100000", 0))
    buy = session.execute(BotAction.buy(MARKET, Decimal("1000")))
    session.update_market(observation(exit_price, 1))
    sell = session.execute(BotAction.sell(MARKET, buy.quantity))
    metrics = session.metrics()
    assert len(session.history) == 2
    assert metrics.trade_count == 2
    assert metrics.fees_paid == buy.fee + sell.fee
    assert (sell.realized_pnl > 0) is is_profit
    assert (metrics.portfolio_value > metrics.starting_balance) is is_profit
