"""Source-neutral news ingestion and intelligence records."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


class NewsSourceKind(StrEnum):
    RSS = "rss"
    API = "api"


class SourceHealth(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class RawNewsStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class NewsSource:
    source_id: str
    name: str
    kind: NewsSourceKind
    enabled: bool
    priority: int
    poll_interval_seconds: int
    feed_url: str
    health: SourceHealth = SourceHealth.UNKNOWN
    last_success: datetime | None = None
    last_failure: datetime | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.name.strip():
            raise ValueError("source id and name are required")
        if not self.feed_url.startswith(("https://", "http://")):
            raise ValueError("news source URL must use HTTP(S)")
        if self.poll_interval_seconds < 30:
            raise ValueError("poll interval must be at least 30 seconds")


@dataclass(frozen=True, slots=True)
class RawNewsItem:
    raw_item_id: UUID
    source_id: str
    title: str
    url: str
    published_at: datetime
    received_at: datetime
    content_hash: str
    external_id: str | None = None
    summary: str | None = None
    author: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    status: RawNewsStatus = RawNewsStatus.RECEIVED
    quarantine_reason: str | None = None

    def __post_init__(self) -> None:
        _aware(self.published_at, "published_at")
        _aware(self.received_at, "received_at")
        if not self.source_id.strip() or not self.title.strip() or not self.url.strip():
            raise ValueError("source, title, and URL are required")
        if len(self.content_hash) != 64:
            raise ValueError("content_hash must be SHA-256 hex")


@dataclass(frozen=True, slots=True)
class NewsEvent:
    news_event_id: UUID
    raw_item_id: UUID
    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime
    received_at: datetime
    processed_at: datetime
    mentioned_assets: tuple[str, ...]
    asset_relevance: dict[str, Decimal]
    language: str
    summary: str | None = None
    author: str | None = None
    importance: Decimal | None = None
    sentiment: Decimal | None = None
    duplicate_group_id: UUID | None = None
    story_cluster_id: UUID | None = None

    def __post_init__(self) -> None:
        for name in ("published_at", "received_at", "processed_at"):
            _aware(getattr(self, name), name)
        if self.processed_at < self.received_at:
            raise ValueError("processed_at must not precede received_at")
        if any(value < 0 or value > 1 for value in self.asset_relevance.values()):
            raise ValueError("asset relevance must be between zero and one")


@dataclass(frozen=True, slots=True)
class MarketAssociation:
    association_id: UUID
    news_event_id: UUID
    market: str
    window_minutes: int
    event_price: Decimal
    post_event_price: Decimal
    price_return: Decimal
    observed_at: datetime
    volume_before: Decimal | None = None
    volume_after: Decimal | None = None

    def __post_init__(self) -> None:
        _aware(self.observed_at, "observed_at")
