"""Contracts exchanged between PaperTrading and AiTrainer."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ActionType(StrEnum):
    """Technology-neutral trading intent."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class MarketState:
    """Point-in-time market observation available to a bot."""

    symbol: str
    observed_at: datetime
    price: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.price <= 0:
            raise ValueError("price must be positive")


@dataclass(frozen=True, slots=True)
class BotAction:
    """Bot intent; only PaperTrading may execute it virtually."""

    action: ActionType
    quantity: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("quantity must not be negative")
        if self.action is ActionType.HOLD and self.quantity != 0:
            raise ValueError("hold actions must have zero quantity")


@dataclass(frozen=True, slots=True)
class TradeResult:
    """Result of a virtual execution attempt."""

    accepted: bool
    action: ActionType
    quantity: Decimal
    fill_price: Decimal | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("quantity must not be negative")
        if self.fill_price is not None and self.fill_price <= 0:
            raise ValueError("fill_price must be positive")
