"""Framework-neutral view models. Missing research values remain missing."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ConnectionState(StrEnum):
    CONNECTED = "Connected"
    CONNECTING = "Connecting"
    DISCONNECTED = "Not connected"
    DISABLED = "Disabled"
    ERROR = "Error"


@dataclass(frozen=True, slots=True)
class MarketSummary:
    market: str
    timestamp: datetime | None = None
    current_price: Decimal | None = None
    change_24h: Decimal | None = None
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
    volume_24h: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    candles: tuple[tuple[datetime, Decimal, Decimal, Decimal, Decimal, Decimal], ...] = ()

    @property
    def spread_percent(self) -> Decimal | None:
        if self.bid is None or self.ask is None or self.bid <= 0:
            return None
        return (self.ask - self.bid) / self.bid


@dataclass(frozen=True, slots=True)
class BotSummary:
    bot_id: str
    name: str
    bot_type: str
    version: str | None = None
    status: str = "STOPPED"
    portfolio_value: Decimal | None = None
    percentage_return: Decimal | None = None
    maximum_drawdown: Decimal | None = None
    trades: int | None = None
    fees: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    total_capital: Decimal | None = None
    total_pnl: Decimal | None = None
    positions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TradeSummary:
    timestamp: datetime
    bot: str
    market: str
    side: str
    price: Decimal | None = None
    pnl: Decimal | None = None


@dataclass(frozen=True, slots=True)
class SessionSummary:
    session_id: str
    name: str
    status: str
    started_at: datetime | None
    markets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PositionSummary:
    market: str
    side: str
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True, slots=True)
class DecisionSummary:
    timestamp: datetime
    bot: str
    market: str
    action: str
    requested_size: Decimal
    confidence: Decimal | None
    price: Decimal
    portfolio_value: Decimal
    executed_trade_id: str | None


@dataclass(frozen=True, slots=True)
class ExperimentSummary:
    experiment_id: str
    name: str
    status: str
    markets: tuple[str, ...]
    start_period: datetime
    end_period: datetime
    starting_balance: Decimal
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IntelligenceEvent:
    event_id: str
    kind: str
    occurred_at: datetime
    title: str
    source: str | None = None
    assets: tuple[str, ...] = ()
    sentiment: Decimal | None = None
    relevance: Decimal | None = None
    importance: Decimal | None = None
    estimated_impact: Decimal | None = None
    author_influence: Decimal | None = None
    novelty: Decimal | None = None
    event_type: str | None = None
    published_at: datetime | None = None
    processed_at: datetime | None = None
    sentiment_confidence: Decimal | None = None
    event_confidence: Decimal | None = None
    impact_maturity: str | None = None
    reactions: tuple[tuple[int, Decimal], ...] = ()
    explanation: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    markets: tuple[MarketSummary, ...] = ()
    bots: tuple[BotSummary, ...] = ()
    portfolio: PortfolioSummary = field(default_factory=PortfolioSummary)
    trades: tuple[TradeSummary, ...] = ()
    sessions: tuple[SessionSummary, ...] = ()
    positions: tuple[PositionSummary, ...] = ()
    decisions: tuple[DecisionSummary, ...] = ()
    experiments: tuple[ExperimentSummary, ...] = ()
    portfolio_history: tuple[tuple[datetime, Decimal], ...] = ()
    news: tuple[IntelligenceEvent, ...] = ()
    social: tuple[IntelligenceEvent, ...] = ()
    connections: dict[str, ConnectionState] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
