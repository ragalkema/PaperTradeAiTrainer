"""Seeded random baseline used to exercise the bot contract."""

import random
from decimal import Decimal

from shared.contracts import ActionType, BotAction, MarketState, TradeResult

from ai_trainer.application.ports import TradingBot


class RandomBot(TradingBot):
    """Choose BUY/SELL/HOLD reproducibly; it is not a profitable strategy claim."""

    def __init__(self, buy_value: Decimal = Decimal("100"), seed: int = 0) -> None:
        self.buy_value = buy_value
        self.seed = seed
        self._random = random.Random(seed)
        self._state: MarketState | None = None
        self._quantity = Decimal("0")

    def reset(self) -> None:
        self._random.seed(self.seed)
        self._state = None
        self._quantity = Decimal("0")

    def observe(self, state: MarketState) -> None:
        self._state = state

    def decide(self) -> BotAction:
        if self._state is None:
            raise RuntimeError("bot must observe a market state before deciding")
        action = self._random.choice(tuple(ActionType))
        if action is ActionType.BUY:
            return BotAction.buy(self._state.market, self.buy_value)
        if action is ActionType.SELL and self._quantity > 0:
            return BotAction.sell(self._state.market, self._quantity)
        return BotAction.hold(self._state.market)

    def on_trade_result(self, result: TradeResult) -> None:
        if not result.accepted:
            return
        if result.action is ActionType.BUY:
            self._quantity += result.quantity
        elif result.action is ActionType.SELL:
            self._quantity -= result.quantity
