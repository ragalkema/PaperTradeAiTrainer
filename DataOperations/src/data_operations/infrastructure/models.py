"""Operational persistence tables."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class OperationsBase(DeclarativeBase):
    pass


class MarketCandleModel(OperationsBase):
    __tablename__ = "market_candles"
    market: Mapped[str] = mapped_column(String(32), primary_key=True)
    interval: Mapped[str] = mapped_column(String(16), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    volume: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_market_candle_range", "market", "interval", "timestamp"),)


class CollectionCheckpointModel(OperationsBase):
    __tablename__ = "collection_checkpoints"
    source: Mapped[str] = mapped_column(String(200), primary_key=True)
    last_successful_event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_poll_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    external_cursor: Mapped[str | None] = mapped_column(Text)
    last_processed_event: Mapped[str | None] = mapped_column(String(500))


class CollectorHealthModel(OperationsBase):
    __tablename__ = "collector_health_observations"
    source: Mapped[str] = mapped_column(String(200), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    events_received: Mapped[int] = mapped_column(Integer)
    error_category: Mapped[str | None] = mapped_column(String(200))
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (Index("ix_collector_health_range", "source", "timestamp"),)


class CoverageLimitationModel(OperationsBase):
    __tablename__ = "coverage_limitations"
    source: Mapped[str] = mapped_column(String(200), primary_key=True)
    first_known_complete_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unavailable_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DatasetManifestModel(OperationsBase):
    __tablename__ = "dataset_manifests"
    manifest_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    market: Mapped[str] = mapped_column(String(32))
    interval: Mapped[str] = mapped_column(String(16))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    canonical_rows: Mapped[int] = mapped_column(Integer)
    feature_versions: Mapped[dict[str, str]] = mapped_column(JSON)
    analyzer_versions: Mapped[list[str]] = mapped_column(JSON)
    coverage_summary: Mapped[dict[str, float]] = mapped_column(JSON)
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    readiness_policy_version: Mapped[str] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    git_commit: Mapped[str | None] = mapped_column(String(64))
