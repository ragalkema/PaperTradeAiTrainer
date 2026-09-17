"""Protocol implemented by every paper-trading bot."""

from abc import ABC, abstractmethod

from app.bots.models import BotAction, MarketState, TradeResult


class TradingBot(ABC):
    """Technology-neutral interface used by the future bot runtime."""

    @abstractmethod
    def reset(self) -> None:
        """Reset all episode-specific state."""

    @abstractmethod
    def observe(self, market_state: MarketState) -> None:
        """Receive one normalized, time-safe market observation."""

    @abstractmethod
    def decide(self) -> BotAction:
        """Return an intent without performing any exchange operation."""

    @abstractmethod
    def on_trade_result(self, result: TradeResult) -> None:
        """Receive the result of a virtual execution attempt."""
