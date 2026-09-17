"""Contracts exchanged between PaperTrading and AiTrainer."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from shared.contracts.values import MarketSymbol, Money, Price, Quantity, require_positive


class ActionType(StrEnum):
    """Technology-neutral trading intent."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class BotAction:
    """Bot intent: BUY spends quote value; SELL disposes base quantity."""

    action: ActionType
    market: MarketSymbol
    requested_value: Money = Decimal("0")
    quantity: Quantity = Decimal("0")

    def __post_init__(self) -> None:
        if self.action is ActionType.BUY:
            require_positive(self.requested_value, "requested_value")
            if self.quantity != 0:
                raise ValueError("buy actions must not specify quantity")
        elif self.action is ActionType.SELL:
            require_positive(self.quantity, "quantity")
            if self.requested_value != 0:
                raise ValueError("sell actions must not specify requested_value")
        elif self.requested_value != 0 or self.quantity != 0:
            raise ValueError("hold actions must have zero value and quantity")

    @classmethod
    def buy(cls, market: MarketSymbol | str, requested_value: Money) -> "BotAction":
        return cls(ActionType.BUY, _market(market), requested_value=requested_value)

    @classmethod
    def sell(cls, market: MarketSymbol | str, quantity: Quantity) -> "BotAction":
        return cls(ActionType.SELL, _market(market), quantity=quantity)

    @classmethod
    def hold(cls, market: MarketSymbol | str) -> "BotAction":
        return cls(ActionType.HOLD, _market(market))


def _market(value: MarketSymbol | str) -> MarketSymbol:
    return value if isinstance(value, MarketSymbol) else MarketSymbol(value)


@dataclass(frozen=True, slots=True)
class TradeResult:
    """Complete result of a virtual execution attempt."""

    accepted: bool
    action: ActionType
    market: MarketSymbol
    timestamp: datetime
    quantity: Quantity = Decimal("0")
    requested_value: Money = Decimal("0")
    market_price: Price | None = None
    execution_price: Price | None = None
    fee: Money = Decimal("0")
    slippage: Money = Decimal("0")
    realized_pnl: Money = Decimal("0")
    trade_id: UUID | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Initial strategy metrics shared with experiment runners."""

    starting_balance: Money
    portfolio_value: Money
    absolute_pnl: Money
    percentage_return: Decimal
    trade_count: int
    fees_paid: Money
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    maximum_drawdown: Decimal
