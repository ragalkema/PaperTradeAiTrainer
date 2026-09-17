"""Virtual-execution boundary."""

from abc import ABC, abstractmethod

from shared.contracts import BotAction, MarketState, PerformanceMetrics, TradeResult

from paper_trading.domain.entities import PaperTrade, PortfolioSnapshot


class PaperExchange(ABC):
    """Contract for simulated execution, never real exchange execution."""

    @abstractmethod
    def update_market(self, state: MarketState) -> None:
        """Advance virtual execution with a normalized observation."""

    @abstractmethod
    def execute(self, action: BotAction) -> TradeResult:
        """Execute a BUY/SELL/HOLD action virtually."""

    @abstractmethod
    def snapshot(self) -> PortfolioSnapshot:
        """Return the current virtual portfolio state."""

    @property
    @abstractmethod
    def trades(self) -> tuple[PaperTrade, ...]:
        """Return immutable virtual execution history."""

    @abstractmethod
    def metrics(self) -> PerformanceMetrics:
        """Return initial performance metrics."""
