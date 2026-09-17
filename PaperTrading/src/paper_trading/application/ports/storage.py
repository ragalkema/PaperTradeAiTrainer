"""Replaceable persistence ports for market observations."""

from typing import Protocol

from shared.contracts import Candle


class RawMarketDataStore(Protocol):
    """Append-only storage for exact public provider payloads."""

    async def append(self, source: str, payload: str) -> None:
        """Append without replacing previous raw data."""
        ...


class CandleRepository(Protocol):
    """Normalized candle persistence with idempotent identity."""

    async def save(self, candles: list[Candle]) -> int:
        """Persist new candles and return the number inserted."""
        ...
