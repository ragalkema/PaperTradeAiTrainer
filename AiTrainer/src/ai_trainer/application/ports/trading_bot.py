"""Framework-neutral bot contract."""

from abc import ABC, abstractmethod

from shared.contracts import BotAction, MarketState, TradeResult


class TradingBot(ABC):
    """Contract shared by rules, ML, and RL bot implementations."""

    @abstractmethod
    def reset(self) -> None:
        """Reset all episode-specific state."""

    @abstractmethod
    def observe(self, state: MarketState) -> None:
        """Receive a point-in-time-safe observation."""

    @abstractmethod
    def decide(self) -> BotAction:
        """Return intent without executing an exchange operation."""

    @abstractmethod
    def on_trade_result(self, result: TradeResult) -> None:
        """Observe a virtual execution result."""
