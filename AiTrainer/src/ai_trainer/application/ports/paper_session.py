"""Structural contract required by bot and experiment runners."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from shared.contracts import AssetSymbol, BotAction, MarketState, PerformanceMetrics, TradeResult


class PortfolioView(Protocol):
    timestamp: datetime
    starting_balance: Decimal
    cash: Decimal
    asset_balances: dict[AssetSymbol, Decimal]
    asset_values: dict[AssetSymbol, Decimal]
    asset_cost_basis: dict[AssetSymbol, Decimal]
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    portfolio_value: Decimal
    fees_paid: Decimal


class PaperSessionPort(Protocol):
    """Minimal paper environment known to AiTrainer."""

    def update_market(self, state: MarketState) -> None: ...

    def execute(self, action: BotAction) -> TradeResult: ...

    def metrics(self) -> PerformanceMetrics: ...

    def portfolio(self) -> object: ...
