"""Optional experiment observation seam; implementations may buffer persistence facts."""

from typing import Protocol

from shared.contracts import BotAction, MarketState, TradeResult


class RunObserver(Protocol):
    def on_step(
        self,
        bot_name: str,
        state: MarketState,
        action: BotAction,
        result: TradeResult,
        portfolio: object,
    ) -> None: ...
