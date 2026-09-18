"""Virtual portfolio and execution history entities."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.contracts import ActionType, AssetSymbol, MarketSymbol, Money, Price, Quantity


@dataclass(frozen=True, slots=True)
class PaperTrade:
    """One completed virtual market-order execution."""

    trade_id: UUID
    timestamp: datetime
    market: MarketSymbol
    side: ActionType
    quantity: Quantity
    requested_value: Money
    market_price: Price
    execution_price: Price
    fee: Money
    slippage: Money
    realized_pnl: Money


@dataclass(slots=True)
class VirtualPortfolio:
    """Mutable aggregate owned exclusively by one paper exchange."""

    starting_balance: Money
    cash: Money
    balances: dict[AssetSymbol, Quantity] = field(default_factory=dict)
    cost_basis: dict[AssetSymbol, Money] = field(default_factory=dict)
    realized_pnl: Money = Decimal("0")
    fees_paid: Money = Decimal("0")


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Read-only valuation of one independent virtual portfolio."""

    timestamp: datetime
    starting_balance: Money
    cash: Money
    asset_balances: dict[AssetSymbol, Quantity]
    asset_values: dict[AssetSymbol, Money]
    unrealized_pnl: Money
    realized_pnl: Money
    portfolio_value: Money
    fees_paid: Money
    asset_cost_basis: dict[AssetSymbol, Money] = field(default_factory=dict)
