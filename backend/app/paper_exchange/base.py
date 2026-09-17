"""Abstract boundary for virtual execution engines."""

from abc import ABC, abstractmethod

from app.bots.models import MarketState
from app.paper_exchange.models import OrderRequest, PaperOrder, PortfolioSnapshot


class PaperExchange(ABC):
    """Paper-only exchange contract with no real-exchange dependency."""

    @abstractmethod
    def update_market(self, state: MarketState) -> None:
        """Advance the exchange using normalized market data."""

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> PaperOrder:
        """Submit a virtual order for simulated execution."""

    @abstractmethod
    def portfolio(self) -> PortfolioSnapshot:
        """Return the current virtual portfolio state."""
