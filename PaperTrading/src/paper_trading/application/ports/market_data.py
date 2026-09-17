"""Read-only market-data port."""

from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Protocol

from shared.contracts import Candle, MarketState, MarketSymbol


class MarketDataPort(Protocol):
    """Supplies public normalized observations; it has no order methods."""

    async def get_current_state(self, market: MarketSymbol) -> MarketState:
        """Return the latest observation available for a market."""
        ...

    async def get_candles(
        self,
        market: MarketSymbol,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1440,
    ) -> Sequence[Candle]:
        """Return chronological normalized historical candles."""
        ...

    def stream_states(self, markets: Sequence[MarketSymbol]) -> AsyncIterator[MarketState]:
        """Yield normalized live market states until cancelled."""
        ...
