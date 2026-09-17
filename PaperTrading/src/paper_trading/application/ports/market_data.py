"""Read-only market-data port."""

from typing import Protocol

from shared.contracts import MarketState


class MarketDataPort(Protocol):
    """Supplies public normalized observations; it has no order methods."""

    async def latest(self, symbol: str) -> MarketState:
        """Return the latest observation available for a market."""
        ...
