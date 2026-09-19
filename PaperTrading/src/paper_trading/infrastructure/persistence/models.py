"""SQLAlchemy tables for append-oriented paper research persistence."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from paper_trading.infrastructure.persistence import Base

MONEY = Numeric(38, 18)


class PaperSessionModel(Base):
    __tablename__ = "paper_sessions"
    session_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    starting_balance: Mapped[Decimal] = mapped_column(MONEY)
    markets: Mapped[list[str]] = mapped_column(JSON)
    fee_rate: Mapped[Decimal] = mapped_column(MONEY)
    slippage_rate: Mapped[Decimal] = mapped_column(MONEY)
    mode: Mapped[str] = mapped_column(String(16), default="paper")
    experiment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("experiments.experiment_id"), index=True
    )


class BotDefinitionModel(Base):
    __tablename__ = "bot_definitions"
    bot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    bot_type: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(100))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("name", "bot_type", "version", name="uq_bot_identity"),)


class SessionBotModel(Base):
    __tablename__ = "session_bots"
    session_bot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("paper_sessions.session_id", ondelete="CASCADE"), index=True
    )
    bot_id: Mapped[UUID] = mapped_column(ForeignKey("bot_definitions.bot_id"), index=True)
    starting_balance: Mapped[Decimal] = mapped_column(MONEY)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    participant_configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("session_id", "bot_id", name="uq_session_bot"),)


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"
    snapshot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_bot_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_bots.session_bot_id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cash: Mapped[Decimal] = mapped_column(MONEY)
    asset_value: Mapped[Decimal] = mapped_column(MONEY)
    portfolio_value: Mapped[Decimal] = mapped_column(MONEY)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    unrealized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    fees_paid: Mapped[Decimal] = mapped_column(MONEY)
    __table_args__ = (Index("ix_portfolio_bot_time", "session_bot_id", "timestamp"),)


class PositionModel(Base):
    __tablename__ = "paper_positions"
    position_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_bot_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_bots.session_bot_id", ondelete="CASCADE"), index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(MONEY)
    average_entry_price: Mapped[Decimal] = mapped_column(MONEY)
    current_price: Mapped[Decimal] = mapped_column(MONEY)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    unrealized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), index=True)
    __table_args__ = (Index("ix_position_bot_time", "session_bot_id", "recorded_at"),)


class PaperTradeModel(Base):
    __tablename__ = "paper_trades"
    trade_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("paper_sessions.session_id", ondelete="CASCADE"), index=True
    )
    session_bot_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_bots.session_bot_id", ondelete="CASCADE"), index=True
    )
    market: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    requested_quantity: Mapped[Decimal] = mapped_column(MONEY)
    executed_quantity: Mapped[Decimal] = mapped_column(MONEY)
    market_price: Mapped[Decimal] = mapped_column(MONEY)
    execution_price: Mapped[Decimal] = mapped_column(MONEY)
    gross_value: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY)
    slippage_cost: Mapped[Decimal] = mapped_column(MONEY)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (Index("ix_trade_session_time", "session_id", "executed_at"),)


class BotDecisionModel(Base):
    __tablename__ = "bot_decisions"
    decision_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("paper_sessions.session_id", ondelete="CASCADE"), index=True
    )
    session_bot_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_bots.session_bot_id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    market: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(16))
    requested_size: Mapped[Decimal] = mapped_column(MONEY)
    confidence: Mapped[Decimal | None] = mapped_column(MONEY)
    market_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price: Mapped[Decimal] = mapped_column(MONEY)
    bid: Mapped[Decimal] = mapped_column(MONEY)
    ask: Mapped[Decimal] = mapped_column(MONEY)
    spread: Mapped[Decimal] = mapped_column(MONEY)
    portfolio_value: Mapped[Decimal] = mapped_column(MONEY)
    cash: Mapped[Decimal] = mapped_column(MONEY)
    position_quantity: Mapped[Decimal] = mapped_column(MONEY)
    feature_snapshot_reference: Mapped[str | None] = mapped_column(String(500))
    news_snapshot_reference: Mapped[str | None] = mapped_column(String(500))
    social_snapshot_reference: Mapped[str | None] = mapped_column(String(500))
    explanation_reference: Mapped[str | None] = mapped_column(String(500))
    executed_trade_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("paper_trades.trade_id"), index=True
    )
    __table_args__ = (Index("ix_decision_bot_time", "session_bot_id", "timestamp"),)


class ExperimentModel(Base):
    __tablename__ = "experiments"
    experiment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    markets: Mapped[list[str]] = mapped_column(JSON)
    start_period: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_period: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    starting_balance: Mapped[Decimal] = mapped_column(MONEY)
    fee_rate: Mapped[Decimal] = mapped_column(MONEY)
    slippage_rate: Mapped[Decimal] = mapped_column(MONEY)
    random_seed: Mapped[int] = mapped_column(Integer)
    dataset_version: Mapped[str | None] = mapped_column(String(200))
    feature_version: Mapped[str | None] = mapped_column(String(200))
    git_commit: Mapped[str | None] = mapped_column(String(64))
