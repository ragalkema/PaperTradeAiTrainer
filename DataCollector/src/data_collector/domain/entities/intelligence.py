"""Versioned online intelligence and explicitly retrospective research records."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class NewsEventType(StrEnum):
    REGULATION = "regulation"
    ETF = "etf"
    MACRO = "macro"
    SECURITY = "security"
    EXCHANGE = "exchange"
    ADOPTION = "adoption"
    PROTOCOL = "protocol"
    LEGAL = "legal"
    STABLECOIN = "stablecoin"
    INSTITUTIONAL = "institutional"
    MARKET_STRUCTURE = "market_structure"
    COMPANY = "company"
    GENERAL_MARKET = "general_market"
    OTHER = "other"


def _range(value: Decimal, name: str, low: Decimal = Decimal("0")) -> None:
    if value < low or value > 1:
        raise ValueError(f"{name} must be between {low} and 1")


@dataclass(frozen=True, slots=True)
class AssetSentiment:
    asset: str
    score: Decimal
    confidence: Decimal
    analyzer: str
    model_version: str
    processed_at: datetime

    def __post_init__(self) -> None:
        _range(self.score, "sentiment", Decimal("-1"))
        _range(self.confidence, "sentiment confidence")


@dataclass(frozen=True, slots=True)
class Classification:
    event_type: NewsEventType
    confidence: Decimal
    secondary_tags: tuple[NewsEventType, ...]
    analyzer: str
    model_version: str
    explanation: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ImportanceResult:
    score: Decimal
    confidence: Decimal
    analyzer: str
    model_version: str
    explanation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NoveltyResult:
    score: Decimal
    confidence: Decimal
    story_cluster_id: UUID
    analyzer: str
    model_version: str
    explanation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NewsIntelligence:
    intelligence_id: UUID
    news_event_id: UUID
    asset: str
    relevance: Decimal
    sentiment: Decimal
    sentiment_confidence: Decimal
    importance: Decimal
    importance_confidence: Decimal
    event_type: NewsEventType
    event_confidence: Decimal
    secondary_tags: tuple[NewsEventType, ...]
    novelty: Decimal
    novelty_confidence: Decimal
    story_cluster_id: UUID
    sentiment_version: str
    importance_version: str
    classifier_version: str
    novelty_version: str
    processed_at: datetime
    explanation: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OnlineNewsItem:
    """Decision-safe event plus per-asset intelligence; no retrospective fields."""

    event: Any
    intelligence: NewsIntelligence


@dataclass(frozen=True, slots=True)
class NewsFeatureSnapshot:
    market: str
    feature_time: datetime
    generated_at: datetime
    feature_version: str
    analyzer_versions: tuple[str, ...]
    lookbacks_minutes: tuple[int, ...]
    news_count_15m: int
    news_count_1h: int
    news_count_6h: int
    max_relevance_1h: Decimal | None
    mean_sentiment_15m: Decimal | None
    mean_sentiment_1h: Decimal | None
    mean_sentiment_6h: Decimal | None
    relevance_weighted_sentiment_1h: Decimal | None
    max_importance_1h: Decimal | None
    mean_importance_1h: Decimal | None
    max_novelty_1h: Decimal | None
    breaking_news_count_15m: int


@dataclass(frozen=True, slots=True)
class RetrospectiveImpact:
    """Research-only temporal association. It must never enter online feature ports."""

    news_event_id: UUID
    asset: str
    score: Decimal
    available_windows: tuple[int, ...]
    pending_windows: tuple[int, ...]
    analyzer_version: str
    calculated_at: datetime
    components: dict[str, Decimal]
