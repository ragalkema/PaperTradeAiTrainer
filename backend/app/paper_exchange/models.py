"""Minimal virtual-order domain models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.bots.models import ActionType, MarketState


class PaperOrderStatus(StrEnum):
    """Lifecycle states supported by the initial contract."""

    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrderRequest(BaseModel):
    """Request for virtual execution."""

    model_config = ConfigDict(frozen=True)
    symbol: str
    side: ActionType
    quantity: Decimal = Field(gt=0)


class PaperOrder(BaseModel):
    """Recorded virtual order; it cannot represent a real exchange order."""

    model_config = ConfigDict(frozen=True)
    order_id: UUID
    request: OrderRequest
    status: PaperOrderStatus
    created_at: datetime


class PortfolioSnapshot(BaseModel):
    """Minimal portfolio view exposed by a paper exchange."""

    model_config = ConfigDict(frozen=True)
    observed_at: datetime
    cash: Decimal
    equity: Decimal


MarketObservation = MarketState
