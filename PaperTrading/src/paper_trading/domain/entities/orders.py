"""Minimal virtual-order entities."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.contracts import ActionType

from paper_trading.domain.enums import PaperOrderStatus


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Request for virtual execution; BUY and SELL require positive quantity."""

    symbol: str
    side: ActionType
    quantity: Decimal

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.side is ActionType.HOLD:
            raise ValueError("hold is not an executable order")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")


@dataclass(frozen=True, slots=True)
class PaperOrder:
    """Virtual order with no representation of a real exchange order."""

    order_id: UUID
    request: OrderRequest
    status: PaperOrderStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Read-only virtual portfolio view."""

    observed_at: datetime
    cash: Decimal
    equity: Decimal
