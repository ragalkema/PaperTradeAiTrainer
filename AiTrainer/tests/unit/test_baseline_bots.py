"""Framework-neutral baseline bot tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trainer.bots.baselines import BuyAndHoldBot, MovingAverageBot, RandomBot
from shared.contracts import ActionType, BotAction, MarketState, MarketSymbol, TradeResult

MARKET = MarketSymbol("BTC-EUR")


def state(price: str, minute: int = 0) -> MarketState:
    value = Decimal(price)
    return MarketState(
        MARKET, datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minute), value, value, value
    )


def accepted_buy(action: BotAction, quantity: str = "1") -> TradeResult:
    return TradeResult(
        True,
        ActionType.BUY,
        action.market,
        datetime.now(UTC),
        Decimal(quantity),
        action.requested_value,
    )


@pytest.mark.unit
def test_random_bot_is_seeded_and_reproducible() -> None:
    first = RandomBot(seed=7)
    second = RandomBot(seed=7)
    decisions = []
    for bot in (first, second):
        sequence = []
        for minute in range(5):
            bot.observe(state("100", minute))
            sequence.append(bot.decide().action)
        decisions.append(sequence)
    assert decisions[0] == decisions[1]


@pytest.mark.unit
def test_buy_and_hold_buys_once_after_success() -> None:
    bot = BuyAndHoldBot(Decimal("500"))
    bot.observe(state("100"))
    buy = bot.decide()
    assert buy.action is ActionType.BUY
    bot.on_trade_result(accepted_buy(buy))
    assert bot.decide().action is ActionType.HOLD


@pytest.mark.unit
def test_moving_average_emits_buy_then_sell_signal() -> None:
    bot = MovingAverageBot(short_window=2, long_window=3)
    for minute, price in enumerate(("100", "101", "103")):
        bot.observe(state(price, minute))
    buy = bot.decide()
    assert buy.action is ActionType.BUY
    bot.on_trade_result(accepted_buy(buy))
    for minute, price in enumerate(("100", "90", "80"), start=3):
        bot.observe(state(price, minute))
    assert bot.decide().action is ActionType.SELL
