"""Shared market and trading contract invariants."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from shared.contracts import BotAction, Candle, MarketState, MarketSymbol


@pytest.mark.unit
def test_market_symbol_is_normalized_and_split() -> None:
    market = MarketSymbol("btc-eur")
    assert str(market) == "BTC-EUR"
    assert str(market.base) == "BTC"
    assert str(market.quote) == "EUR"


@pytest.mark.unit
def test_market_state_validates_book_and_timestamp() -> None:
    market = MarketSymbol("BTC-EUR")
    state = MarketState(market, datetime.now(UTC), Decimal("100"), Decimal("99"), Decimal("101"))
    assert state.spread == Decimal("2")
    with pytest.raises(ValueError, match="ask"):
        MarketState(market, datetime.now(UTC), Decimal("100"), Decimal("101"), Decimal("99"))
    with pytest.raises(ValueError, match="timezone-aware"):
        MarketState(market, datetime.now(), Decimal("100"), Decimal("99"), Decimal("101"))


@pytest.mark.unit
def test_candle_rejects_invalid_ohlc() -> None:
    with pytest.raises(ValueError, match="high"):
        Candle(
            MarketSymbol("BTC-EUR"),
            "1m",
            datetime.now(UTC),
            Decimal("100"),
            Decimal("99"),
            Decimal("98"),
            Decimal("100"),
            Decimal("1"),
        )


@pytest.mark.unit
def test_action_factories_encode_buy_sell_and_hold_units() -> None:
    assert BotAction.buy("BTC-EUR", Decimal("100")).requested_value == Decimal("100")
    assert BotAction.sell("BTC-EUR", Decimal("0.01")).quantity == Decimal("0.01")
    assert BotAction.hold("BTC-EUR").quantity == 0
    with pytest.raises(ValueError, match="positive"):
        BotAction.buy("BTC-EUR", Decimal("0"))
