"""Persistent research records owned by PaperTrading.

These are framework-neutral facts captured at decision/execution time. They are not ORM models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from shared.contracts import ActionType, MarketSymbol
from shared.contracts.market import require_aware


class SessionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class BotStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PositionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class PaperSessionRecord:
    session_id: UUID
    name: str
    created_at: datetime
    status: SessionStatus
    starting_balance: Decimal
    markets: tuple[MarketSymbol, ...]
    fee_rate: Decimal
    slippage_rate: Decimal
    mode: str = "paper"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    experiment_id: UUID | None = None

    def __post_init__(self) -> None:
        require_aware(self.created_at, "created_at")
        if self.starting_balance <= 0:
            raise ValueError("starting_balance must be positive")
        if self.mode != "paper":
            raise ValueError("only paper mode is supported")


@dataclass(frozen=True, slots=True)
class BotDefinitionRecord:
    bot_id: UUID
    name: str
    bot_type: str
    version: str
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SessionBotRecord:
    session_bot_id: UUID
    session_id: UUID
    bot_id: UUID
    starting_balance: Decimal
    status: BotStatus
    created_at: datetime
    participant_configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PortfolioSnapshotRecord:
    snapshot_id: UUID
    session_bot_id: UUID
    timestamp: datetime
    cash: Decimal
    asset_value: Decimal
    portfolio_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees_paid: Decimal


@dataclass(frozen=True, slots=True)
class PositionRecord:
    position_id: UUID
    session_bot_id: UUID
    recorded_at: datetime
    market: MarketSymbol
    side: str
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    opened_at: datetime
    status: PositionStatus
    closed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaperTradeRecord:
    trade_id: UUID
    session_id: UUID
    session_bot_id: UUID
    market: MarketSymbol
    side: ActionType
    requested_quantity: Decimal
    executed_quantity: Decimal
    market_price: Decimal
    execution_price: Decimal
    gross_value: Decimal
    fee: Decimal
    slippage_cost: Decimal
    realized_pnl: Decimal
    executed_at: datetime


@dataclass(frozen=True, slots=True)
class DecisionContextRecord:
    """Immutable point-in-time inputs captured when the decision was made.

    Values must be recorded at T and never reconstructed later from future observations.
    """

    market_timestamp: datetime
    price: Decimal
    bid: Decimal
    ask: Decimal
    spread: Decimal
    portfolio_value: Decimal
    cash: Decimal
    position_quantity: Decimal
    feature_snapshot_reference: str | None = None
    news_snapshot_reference: str | None = None
    social_snapshot_reference: str | None = None


@dataclass(frozen=True, slots=True)
class BotDecisionRecord:
    decision_id: UUID
    session_id: UUID
    session_bot_id: UUID
    timestamp: datetime
    market: MarketSymbol
    action: ActionType
    requested_size: Decimal
    context: DecisionContextRecord
    confidence: Decimal | None = None
    explanation_reference: str | None = None
    executed_trade_id: UUID | None = None

    def __post_init__(self) -> None:
        require_aware(self.timestamp)
        if self.context.market_timestamp > self.timestamp:
            raise ValueError("decision context cannot contain future market data")


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    experiment_id: UUID
    name: str
    description: str
    created_at: datetime
    status: ExperimentStatus
    markets: tuple[MarketSymbol, ...]
    start_period: datetime
    end_period: datetime
    starting_balance: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    random_seed: int
    dataset_version: str | None = None
    feature_version: str | None = None
    git_commit: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    starting_value: Decimal
    current_value: Decimal
    absolute_pnl: Decimal
    percentage_return: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees_paid: Decimal
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    average_winning_trade: Decimal | None
    average_losing_trade: Decimal | None
    largest_win: Decimal | None
    largest_loss: Decimal | None
    maximum_drawdown: Decimal
    current_drawdown: Decimal
    profit_factor: Decimal | None
