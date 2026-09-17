"""Normalized market-data contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from shared.contracts.values import MarketSymbol, Price, Quantity, require_positive


def require_aware(timestamp: datetime, name: str = "timestamp") -> datetime:
    """Reject naive timestamps."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return timestamp


@dataclass(frozen=True, slots=True)
class MarketState:
    """Current normalized top-of-book market state."""

    market: MarketSymbol
    timestamp: datetime
    current_price: Price
    bid: Price
    ask: Price
    volume: Quantity = Decimal("0")

    def __post_init__(self) -> None:
        require_aware(self.timestamp)
        require_positive(self.current_price, "current_price")
        require_positive(self.bid, "bid")
        require_positive(self.ask, "ask")
        if self.ask < self.bid:
            raise ValueError("ask must be greater than or equal to bid")
        if not self.volume.is_finite() or self.volume < 0:
            raise ValueError("volume must be finite and non-negative")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class MarketTick:
    """One normalized public trade/price observation."""

    market: MarketSymbol
    timestamp: datetime
    price: Price
    quantity: Quantity = Decimal("0")

    def __post_init__(self) -> None:
        require_aware(self.timestamp)
        require_positive(self.price, "price")
        if not self.quantity.is_finite() or self.quantity < 0:
            raise ValueError("quantity must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class Candle:
    """Normalized OHLCV candle uniquely identified by market/interval/time."""

    market: MarketSymbol
    interval: str
    timestamp: datetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity

    def __post_init__(self) -> None:
        require_aware(self.timestamp)
        if not self.interval.strip():
            raise ValueError("interval must not be empty")
        for name in ("open", "high", "low", "close"):
            require_positive(getattr(self, name), name)
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be at least open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be at most open, close, and high")
        if not self.volume.is_finite() or self.volume < 0:
            raise ValueError("volume must be finite and non-negative")
