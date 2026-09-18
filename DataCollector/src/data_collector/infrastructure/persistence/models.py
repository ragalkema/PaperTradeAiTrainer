"""DataCollector-owned SQLAlchemy news tables."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DataCollectorBase(DeclarativeBase):
    pass


SCORE = Numeric(12, 10)
MONEY = Numeric(38, 18)


class NewsSourceModel(DataCollectorBase):
    __tablename__ = "news_sources"
    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool]
    priority: Mapped[int] = mapped_column(Integer)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer)
    feed_url: Mapped[str] = mapped_column(String(1000))
    health: Mapped[str] = mapped_column(String(20), index=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RawNewsItemModel(DataCollectorBase):
    __tablename__ = "raw_news_items"
    raw_item_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("news_sources.source_id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(2000))
    author: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), index=True)
    quarantine_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        Index("uq_raw_news_source_hash", "source_id", "content_hash", unique=True),
        Index("ix_raw_news_source_received", "source_id", "received_at"),
    )


class NewsEventModel(DataCollectorBase):
    __tablename__ = "news_events"
    news_event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    raw_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_news_items.raw_item_id"), unique=True, index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("news_sources.source_id"), index=True)
    source_name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(2000))
    author: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mentioned_assets: Mapped[list[str]] = mapped_column(JSON)
    asset_relevance: Mapped[dict[str, str]] = mapped_column(JSON)
    importance: Mapped[Decimal | None] = mapped_column(SCORE)
    sentiment: Mapped[Decimal | None] = mapped_column(SCORE)
    language: Mapped[str] = mapped_column(String(20))
    duplicate_group_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True, index=True)
    story_cluster_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    __table_args__ = (Index("ix_news_availability", "received_at", "processed_at"),)


class NewsMarketAssociationModel(DataCollectorBase):
    __tablename__ = "news_market_associations"
    association_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    news_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("news_events.news_event_id", ondelete="CASCADE"), index=True
    )
    market: Mapped[str] = mapped_column(String(32), index=True)
    window_minutes: Mapped[int] = mapped_column(Integer)
    event_price: Mapped[Decimal] = mapped_column(MONEY)
    post_event_price: Mapped[Decimal] = mapped_column(MONEY)
    price_return: Mapped[Decimal] = mapped_column(SCORE)
    volume_before: Mapped[Decimal | None] = mapped_column(MONEY)
    volume_after: Mapped[Decimal | None] = mapped_column(MONEY)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index("uq_news_market_window", "news_event_id", "market", "window_minutes", unique=True),
    )
