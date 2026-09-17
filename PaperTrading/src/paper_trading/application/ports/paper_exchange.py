"""Virtual-execution boundary."""

from abc import ABC, abstractmethod

from shared.contracts import MarketState

from paper_trading.domain.entities import OrderRequest, PaperOrder, PortfolioSnapshot


class PaperExchange(ABC):
    """Contract for simulated execution, never real exchange execution."""

    @abstractmethod
    def update_market(self, state: MarketState) -> None:
        """Advance virtual execution with a normalized observation."""

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> PaperOrder:
        """Submit a virtual order."""

    @abstractmethod
    def portfolio(self) -> PortfolioSnapshot:
        """Return the current virtual portfolio state."""
