"""Minimal moving-average signal baseline."""

from collections import deque
from decimal import Decimal

from shared.contracts import ActionType, BotAction, MarketState, TradeResult

from ai_trainer.application.ports import TradingBot


class MovingAverageBot(TradingBot):
    """BUY when short average exceeds long average; SELL on the inverse."""

    def __init__(
        self,
        short_window: int = 3,
        long_window: int = 5,
        buy_value: Decimal = Decimal("1000"),
    ) -> None:
        if not 0 < short_window < long_window:
            raise ValueError("windows must satisfy 0 < short < long")
        self.short_window = short_window
        self.long_window = long_window
        self.buy_value = buy_value
        self._prices: deque[Decimal] = deque(maxlen=long_window)
        self._state: MarketState | None = None
        self._quantity = Decimal("0")

    def reset(self) -> None:
        self._prices.clear()
        self._state = None
        self._quantity = Decimal("0")

    def observe(self, state: MarketState) -> None:
        self._state = state
        self._prices.append(state.current_price)

    def decide(self) -> BotAction:
        if self._state is None:
            raise RuntimeError("bot must observe a market state before deciding")
        if len(self._prices) < self.long_window:
            return BotAction.hold(self._state.market)
        short_average = sum(list(self._prices)[-self.short_window :], Decimal("0")) / Decimal(
            self.short_window
        )
        long_average = sum(self._prices, Decimal("0")) / Decimal(self.long_window)
        if short_average > long_average and self._quantity == 0:
            return BotAction.buy(self._state.market, self.buy_value)
        if short_average < long_average and self._quantity > 0:
            return BotAction.sell(self._state.market, self._quantity)
        return BotAction.hold(self._state.market)

    def on_trade_result(self, result: TradeResult) -> None:
        if not result.accepted:
            return
        if result.action is ActionType.BUY:
            self._quantity += result.quantity
        elif result.action is ActionType.SELL:
            self._quantity -= result.quantity
