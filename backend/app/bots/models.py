"""Minimal domain values shared by bot implementations and runtimes."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ActionType(StrEnum):
    """Direction requested by a bot."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class MarketState(BaseModel):
    """A normalized point-in-time market observation."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    observed_at: datetime
    price: Decimal = Field(gt=0)


class BotAction(BaseModel):
    """A bot intent; execution remains the paper exchange's responsibility."""

    model_config = ConfigDict(frozen=True)

    action: ActionType
    quantity: Decimal = Field(default=Decimal("0"), ge=0)


class TradeResult(BaseModel):
    """Outcome returned to a bot after virtual execution."""

    model_config = ConfigDict(frozen=True)

    accepted: bool
    action: ActionType
    quantity: Decimal = Field(ge=0)
    fill_price: Decimal | None = Field(default=None, gt=0)
    reason: str | None = None
