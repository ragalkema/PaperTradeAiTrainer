"""Buy-once baseline."""

from decimal import Decimal

from shared.contracts import ActionType, BotAction, MarketState, TradeResult

from ai_trainer.application.ports import TradingBot


class BuyAndHoldBot(TradingBot):
    """Spend a fixed quote amount once, then hold."""

    def __init__(self, buy_value: Decimal = Decimal("1000")) -> None:
        self.buy_value = buy_value
        self._state: MarketState | None = None
        self._bought = False

    def reset(self) -> None:
        self._state = None
        self._bought = False

    def observe(self, state: MarketState) -> None:
        self._state = state

    def decide(self) -> BotAction:
        if self._state is None:
            raise RuntimeError("bot must observe a market state before deciding")
        if not self._bought:
            return BotAction.buy(self._state.market, self.buy_value)
        return BotAction.hold(self._state.market)

    def on_trade_result(self, result: TradeResult) -> None:
        if result.accepted and result.action is ActionType.BUY:
            self._bought = True
