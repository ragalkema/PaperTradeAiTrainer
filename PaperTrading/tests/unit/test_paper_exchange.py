"""Deterministic paper-exchange domain tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from paper_trading.application.services import PaperTradingSession
from shared.contracts import ActionType, BotAction, MarketState, MarketSymbol

MARKET = MarketSymbol("BTC-EUR")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def state(
    price: str, *, bid: str | None = None, ask: str | None = None, step: int = 0
) -> MarketState:
    value = Decimal(price)
    return MarketState(
        MARKET,
        NOW + timedelta(minutes=step),
        value,
        Decimal(bid) if bid else value,
        Decimal(ask) if ask else value,
    )


@pytest.mark.unit
def test_starting_portfolio_and_hold() -> None:
    session = PaperTradingSession(Decimal("10000"))
    session.update_market(state("100000"))
    result = session.execute(BotAction.hold(MARKET))
    portfolio = session.portfolio()
    assert result.accepted and result.action is ActionType.HOLD
    assert portfolio.cash == Decimal("10000")
    assert portfolio.portfolio_value == Decimal("10000")
    assert session.history == ()


@pytest.mark.unit
def test_buy_uses_ask_fee_and_adverse_slippage() -> None:
    session = PaperTradingSession(Decimal("10000"), Decimal("0.0025"), Decimal("0.0005"))
    session.update_market(state("99995", bid="99990", ask="100000"))
    result = session.execute(BotAction.buy(MARKET, Decimal("1000")))
    portfolio = session.portfolio()
    assert result.accepted
    assert result.market_price == Decimal("100000")
    assert result.execution_price == Decimal("100050.0000")
    assert result.quantity == Decimal("1000") / Decimal("100050")
    assert result.fee == Decimal("2.5000")
    assert portfolio.cash == Decimal("8997.5000")
    assert portfolio.asset_balances[MARKET.base] == result.quantity
    assert portfolio.fees_paid == result.fee


@pytest.mark.unit
def test_sell_uses_bid_and_calculates_net_realized_pnl() -> None:
    session = PaperTradingSession(Decimal("10000"), Decimal("0.0025"), Decimal("0.0005"))
    session.update_market(state("100000"))
    bought = session.execute(BotAction.buy(MARKET, Decimal("1000")))
    session.update_market(state("105000", bid="105000", ask="105010", step=1))
    sold = session.execute(BotAction.sell(MARKET, bought.quantity))
    portfolio = session.portfolio()
    proceeds = bought.quantity * Decimal("104947.5000")
    expected_sell_fee = proceeds * Decimal("0.0025")
    assert sold.execution_price == Decimal("104947.5000")
    assert sold.fee == expected_sell_fee
    assert sold.realized_pnl == proceeds - expected_sell_fee - Decimal("1002.5000")
    assert portfolio.asset_balances[MARKET.base] == 0
    assert portfolio.realized_pnl == sold.realized_pnl
    assert session.metrics().winning_trades == 1


@pytest.mark.unit
def test_rejects_insufficient_cash_and_assets_without_mutation() -> None:
    session = PaperTradingSession(Decimal("100"), Decimal("0.01"), Decimal("0"))
    session.update_market(state("100"))
    buy = session.execute(BotAction.buy(MARKET, Decimal("100")))
    sell = session.execute(BotAction.sell(MARKET, Decimal("1")))
    assert not buy.accepted and buy.reason == "insufficient cash"
    assert not sell.accepted and sell.reason == "insufficient asset balance"
    assert session.portfolio().cash == Decimal("100")
    assert session.history == ()


@pytest.mark.unit
def test_portfolio_valuation_unrealized_pnl_and_fees() -> None:
    session = PaperTradingSession(Decimal("10000"), Decimal("0"), Decimal("0"))
    session.update_market(state("100000"))
    session.execute(BotAction.buy(MARKET, Decimal("1000")))
    session.update_market(state("110000", step=1))
    portfolio = session.portfolio()
    assert portfolio.asset_values[MARKET.base] == Decimal("1100")
    assert portfolio.unrealized_pnl == Decimal("100")
    assert portfolio.portfolio_value == Decimal("10100")
    assert session.metrics().percentage_return == Decimal("0.01")


@pytest.mark.unit
def test_market_updates_must_be_chronological() -> None:
    session = PaperTradingSession()
    session.update_market(state("100", step=1))
    with pytest.raises(ValueError, match="backwards"):
        session.update_market(state("99", step=0))
