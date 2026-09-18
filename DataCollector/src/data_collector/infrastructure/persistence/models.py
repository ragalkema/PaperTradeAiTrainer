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


class NewsIntelligenceModel(DataCollectorBase):
    __tablename__ = "news_intelligence"
    intelligence_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    news_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("news_events.news_event_id", ondelete="CASCADE"), index=True
    )
    asset: Mapped[str] = mapped_column(String(20), index=True)
    relevance: Mapped[Decimal] = mapped_column(SCORE)
    sentiment: Mapped[Decimal] = mapped_column(SCORE)
    sentiment_confidence: Mapped[Decimal] = mapped_column(SCORE)
    importance: Mapped[Decimal] = mapped_column(SCORE, index=True)
    importance_confidence: Mapped[Decimal] = mapped_column(SCORE)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    event_confidence: Mapped[Decimal] = mapped_column(SCORE)
    secondary_tags: Mapped[list[str]] = mapped_column(JSON)
    novelty: Mapped[Decimal] = mapped_column(SCORE)
    novelty_confidence: Mapped[Decimal] = mapped_column(SCORE)
    story_cluster_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    sentiment_version: Mapped[str] = mapped_column(String(100))
    importance_version: Mapped[str] = mapped_column(String(100))
    classifier_version: Mapped[str] = mapped_column(String(100))
    novelty_version: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    explanation: Mapped[dict[str, list[str]]] = mapped_column(JSON)
    __table_args__ = (
        Index(
            "uq_news_intelligence_versions",
            "news_event_id",
            "asset",
            "sentiment_version",
            "importance_version",
            "classifier_version",
            "novelty_version",
            unique=True,
        ),
    )


class NewsFeatureSnapshotModel(DataCollectorBase):
    __tablename__ = "news_feature_snapshots"
    snapshot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    feature_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    feature_version: Mapped[str] = mapped_column(String(100))
    analyzer_versions: Mapped[list[str]] = mapped_column(JSON)
    lookbacks_minutes: Mapped[list[int]] = mapped_column(JSON)
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (
        Index("uq_news_feature_identity", "market", "feature_time", "feature_version", unique=True),
    )


class NewsMarketImpactModel(DataCollectorBase):
    __tablename__ = "news_market_impact"
    news_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("news_events.news_event_id", ondelete="CASCADE"), primary_key=True
    )
    asset: Mapped[str] = mapped_column(String(20), primary_key=True)
    score: Mapped[Decimal] = mapped_column(SCORE, index=True)
    available_windows: Mapped[list[int]] = mapped_column(JSON)
    pending_windows: Mapped[list[int]] = mapped_column(JSON)
    analyzer_version: Mapped[str] = mapped_column(String(100))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    components: Mapped[dict[str, str]] = mapped_column(JSON)


class TrackedSocialAccountModel(DataCollectorBase):
    __tablename__ = "tracked_social_accounts"
    account_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    provider_user_id: Mapped[str | None] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(index=True)
    category: Mapped[str] = mapped_column(String(30))
    priority: Mapped[int]
    followers: Mapped[int | None]
    typical_engagement: Mapped[Decimal | None] = mapped_column(MONEY)
    posts_per_day: Mapped[Decimal | None] = mapped_column(MONEY)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("uq_social_provider_username", "provider", "username", unique=True),)


class RawSocialPostModel(DataCollectorBase):
    __tablename__ = "raw_social_posts"
    raw_post_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    external_post_id: Mapped[str] = mapped_column(String(100))
    provider_user_id: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(20))
    reply_to: Mapped[str | None] = mapped_column(String(100))
    quote_of: Mapped[str | None] = mapped_column(String(100))
    repost_of: Mapped[str | None] = mapped_column(String(100))
    public_metrics: Mapped[dict[str, int] | None] = mapped_column(JSON)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int]
    __table_args__ = (
        Index("uq_raw_social_version", "provider", "external_post_id", "content_hash", unique=True),
    )


class SocialEventModel(DataCollectorBase):
    __tablename__ = "social_events"
    social_event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    raw_post_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_social_posts.raw_post_id"), unique=True
    )
    provider: Mapped[str] = mapped_column(String(30))
    source_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("tracked_social_accounts.account_id"), index=True
    )
    external_post_id: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    language: Mapped[str] = mapped_column(String(20))
    mentioned_assets: Mapped[list[str]] = mapped_column(JSON)
    asset_relevance: Mapped[dict[str, str]] = mapped_column(JSON)
    post_type: Mapped[str] = mapped_column(String(20))
    reply_to: Mapped[str | None] = mapped_column(String(100))
    quote_of: Mapped[str | None] = mapped_column(String(100))
    repost_of: Mapped[str | None] = mapped_column(String(100))
    story_cluster_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)


class SocialEngagementSnapshotModel(DataCollectorBase):
    __tablename__ = "social_engagement_snapshots"
    snapshot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    social_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_events.social_event_id", ondelete="CASCADE"), index=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    likes: Mapped[int | None]
    replies: Mapped[int | None]
    reposts: Mapped[int | None]
    quotes: Mapped[int | None]
    bookmarks: Mapped[int | None]
    views: Mapped[int | None]


class SocialIntelligenceModel(DataCollectorBase):
    __tablename__ = "social_intelligence"
    intelligence_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    social_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_events.social_event_id", ondelete="CASCADE"), index=True
    )
    asset: Mapped[str] = mapped_column(String(20), index=True)
    relevance: Mapped[Decimal] = mapped_column(SCORE)
    sentiment: Mapped[Decimal] = mapped_column(SCORE)
    sentiment_confidence: Mapped[Decimal] = mapped_column(SCORE)
    importance: Mapped[Decimal] = mapped_column(SCORE, index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    event_confidence: Mapped[Decimal] = mapped_column(SCORE)
    novelty: Mapped[Decimal] = mapped_column(SCORE)
    account_influence: Mapped[Decimal] = mapped_column(SCORE, index=True)
    verification_status: Mapped[str] = mapped_column(String(30))
    versions: Mapped[dict[str, str]] = mapped_column(JSON)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    explanation: Mapped[dict[str, list[str]]] = mapped_column(JSON)


class SocialFeatureSnapshotModel(DataCollectorBase):
    __tablename__ = "social_feature_snapshots"
    snapshot_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    feature_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    feature_version: Mapped[str] = mapped_column(String(100))
    analyzer_versions: Mapped[list[str]] = mapped_column(JSON)
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (
        Index(
            "uq_social_feature_identity", "market", "feature_time", "feature_version", unique=True
        ),
    )


class SocialMarketReactionModel(DataCollectorBase):
    __tablename__ = "social_market_reactions"
    reaction_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    social_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_events.social_event_id", ondelete="CASCADE"), index=True
    )
    market: Mapped[str] = mapped_column(String(32))
    window_minutes: Mapped[int]
    event_price: Mapped[Decimal] = mapped_column(MONEY)
    post_price: Mapped[Decimal] = mapped_column(MONEY)
    price_return: Mapped[Decimal] = mapped_column(SCORE)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    volume_before: Mapped[Decimal | None] = mapped_column(MONEY)
    volume_after: Mapped[Decimal | None] = mapped_column(MONEY)
    __table_args__ = (
        Index(
            "uq_social_market_window", "social_event_id", "market", "window_minutes", unique=True
        ),
    )


class SocialMarketImpactModel(DataCollectorBase):
    __tablename__ = "social_market_impact"
    social_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_events.social_event_id", ondelete="CASCADE"), primary_key=True
    )
    asset: Mapped[str] = mapped_column(String(20), primary_key=True)
    score: Mapped[Decimal] = mapped_column(SCORE, index=True)
    available_windows: Mapped[list[int]] = mapped_column(JSON)
    pending_windows: Mapped[list[int]] = mapped_column(JSON)
    analyzer_version: Mapped[str] = mapped_column(String(100))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    components: Mapped[dict[str, str]] = mapped_column(JSON)
