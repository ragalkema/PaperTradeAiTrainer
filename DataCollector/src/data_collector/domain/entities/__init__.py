"""External content entities."""

from data_collector.domain.entities.external_content import ExternalContent
from data_collector.domain.entities.intelligence import (
    AssetSentiment,
    Classification,
    ImportanceResult,
    NewsEventType,
    NewsFeatureSnapshot,
    NewsIntelligence,
    NoveltyResult,
    OnlineNewsItem,
    RetrospectiveImpact,
)
from data_collector.domain.entities.news import (
    MarketAssociation,
    NewsEvent,
    NewsSource,
    NewsSourceKind,
    RawNewsItem,
    RawNewsStatus,
    SourceHealth,
)

__all__ = [
    "AssetSentiment",
    "Classification",
    "ExternalContent",
    "ImportanceResult",
    "MarketAssociation",
    "NewsEvent",
    "NewsEventType",
    "NewsFeatureSnapshot",
    "NewsIntelligence",
    "NewsSource",
    "NewsSourceKind",
    "NoveltyResult",
    "OnlineNewsItem",
    "RawNewsItem",
    "RawNewsStatus",
    "RetrospectiveImpact",
    "SourceHealth",
]
