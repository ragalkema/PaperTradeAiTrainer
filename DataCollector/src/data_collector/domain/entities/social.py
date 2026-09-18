"""Provider-independent social ingestion, online intelligence, and research records."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class SocialAccountCategory(StrEnum):
    FOUNDER = "founder"
    DEVELOPER = "developer"
    EXCHANGE = "exchange"
    ANALYST = "analyst"
    TRADER = "trader"
    JOURNALIST = "journalist"
    COMPANY = "company"
    PROJECT = "project"
    REGULATOR = "regulator"
    INSTITUTION = "institution"
    OTHER = "other"


class SocialPostType(StrEnum):
    ORIGINAL = "original"
    REPLY = "reply"
    QUOTE = "quote"
    REPOST = "repost"


class SocialEventType(StrEnum):
    MARKET_OPINION = "market_opinion"
    PRICE_PREDICTION = "price_prediction"
    ANNOUNCEMENT = "announcement"
    REGULATION = "regulation"
    ETF = "etf"
    MACRO = "macro"
    SECURITY = "security"
    EXCHANGE = "exchange"
    PROTOCOL = "protocol"
    ADOPTION = "adoption"
    INSTITUTIONAL = "institutional"
    RUMOR = "rumor"
    BREAKING_NEWS = "breaking_news"
    PERSONAL_OPINION = "personal_opinion"
    OTHER = "other"


class VerificationStatus(StrEnum):
    UNKNOWN = "unknown"
    CLAIM = "claim"
    CONFIRMED_REFERENCE = "confirmed_reference"
    OFFICIAL_SOURCE = "official_source"


@dataclass(frozen=True, slots=True)
class TrackedSocialAccount:
    account_id: UUID
    provider: str
    provider_user_id: str | None
    username: str
    display_name: str | None
    enabled: bool
    category: SocialAccountCategory
    priority: int
    created_at: datetime
    updated_at: datetime
    followers: int | None = None
    typical_engagement: Decimal | None = None
    posts_per_day: Decimal | None = None


@dataclass(frozen=True, slots=True)
class RawSocialPost:
    raw_post_id: UUID
    provider: str
    external_post_id: str
    provider_user_id: str
    username: str
    text: str
    created_at: datetime
    received_at: datetime
    content_hash: str
    language: str | None = None
    reply_to: str | None = None
    quote_of: str | None = None
    repost_of: str | None = None
    public_metrics: dict[str, int] | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1


@dataclass(frozen=True, slots=True)
class SocialEngagementSnapshot:
    snapshot_id: UUID
    social_event_id: UUID
    observed_at: datetime
    likes: int | None = None
    replies: int | None = None
    reposts: int | None = None
    quotes: int | None = None
    bookmarks: int | None = None
    views: int | None = None


@dataclass(frozen=True, slots=True)
class SocialEvent:
    social_event_id: UUID
    raw_post_id: UUID
    provider: str
    source_account_id: UUID
    external_post_id: str
    username: str
    text: str
    created_at: datetime
    received_at: datetime
    processed_at: datetime
    language: str
    mentioned_assets: tuple[str, ...]
    asset_relevance: dict[str, Decimal]
    post_type: SocialPostType
    reply_to: str | None = None
    quote_of: str | None = None
    repost_of: str | None = None
    story_cluster_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SocialIntelligence:
    intelligence_id: UUID
    social_event_id: UUID
    asset: str
    relevance: Decimal
    sentiment: Decimal
    sentiment_confidence: Decimal
    importance: Decimal
    event_type: SocialEventType
    event_confidence: Decimal
    novelty: Decimal
    account_influence: Decimal
    verification_status: VerificationStatus
    sentiment_version: str
    relevance_version: str
    importance_version: str
    classifier_version: str
    novelty_version: str
    influence_version: str
    processed_at: datetime
    explanation: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OnlineSocialItem:
    event: SocialEvent
    intelligence: SocialIntelligence
    engagement: SocialEngagementSnapshot | None


@dataclass(frozen=True, slots=True)
class SocialFeatureSnapshot:
    market: str
    feature_time: datetime
    generated_at: datetime
    feature_version: str
    analyzer_versions: tuple[str, ...]
    post_count_15m: int
    post_count_1h: int
    post_count_6h: int
    unique_accounts_1h: int
    mean_sentiment_15m: Decimal | None
    mean_sentiment_1h: Decimal | None
    mean_sentiment_6h: Decimal | None
    weighted_sentiment_1h: Decimal | None
    max_relevance_1h: Decimal | None
    max_importance_1h: Decimal | None
    max_novelty_1h: Decimal | None
    high_influence_post_count_1h: int
    breaking_post_count_15m: int
    social_activity_zscore: Decimal | None
    engagement_velocity_1h: Decimal | None


@dataclass(frozen=True, slots=True)
class SocialMarketReaction:
    reaction_id: UUID
    social_event_id: UUID
    market: str
    window_minutes: int
    event_price: Decimal
    post_price: Decimal
    price_return: Decimal
    observed_at: datetime
    volume_before: Decimal | None = None
    volume_after: Decimal | None = None


@dataclass(frozen=True, slots=True)
class SocialMarketImpact:
    social_event_id: UUID
    asset: str
    score: Decimal
    available_windows: tuple[int, ...]
    pending_windows: tuple[int, ...]
    analyzer_version: str
    calculated_at: datetime
    components: dict[str, Decimal]
