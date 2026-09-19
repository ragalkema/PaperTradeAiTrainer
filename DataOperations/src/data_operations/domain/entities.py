"""Framework-neutral operational data quality records."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    MISCONFIGURED = "misconfigured"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CollectorHealthObservation:
    source: str
    timestamp: datetime
    status: HealthStatus
    latency_ms: int | None = None
    events_received: int = 0
    error_category: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CollectionCheckpoint:
    source: str
    last_successful_event_time: datetime | None
    last_poll_time: datetime
    external_cursor: str | None = None
    last_processed_event: str | None = None


@dataclass(frozen=True, slots=True)
class OperationalInterval:
    source: str
    start: datetime
    end: datetime
    status: HealthStatus


@dataclass(frozen=True, slots=True)
class CoverageLimitation:
    source: str
    first_known_complete_time: datetime | None
    unavailable_before: datetime | None
    reason: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MissingRange:
    start: datetime
    end: datetime
    observations: int


@dataclass(frozen=True, slots=True)
class MarketGapReport:
    market: str
    interval: str
    start: datetime
    end: datetime
    expected: int
    present: int
    missing: tuple[datetime, ...]
    missing_ranges: tuple[MissingRange, ...]

    @property
    def coverage(self) -> float:
        return self.present / self.expected if self.expected else 0.0


@dataclass(frozen=True, slots=True)
class SourceCoverage:
    source: str
    operational_seconds: float
    requested_seconds: float
    event_count: int
    relevant_event_count: int
    first_available: datetime | None
    gaps: tuple[MissingRange, ...] = ()

    @property
    def operational_coverage(self) -> float:
        if self.requested_seconds <= 0:
            return 0.0
        return min(1.0, self.operational_seconds / self.requested_seconds)


@dataclass(frozen=True, slots=True)
class ReadinessPolicy:
    version: str = "research_readiness_v1"
    minimum_period: timedelta = timedelta(days=30)
    minimum_market_coverage: float = 0.995
    maximum_market_gap: timedelta = timedelta(hours=3)
    minimum_collector_coverage: float = 0.98
    minimum_canonical_rows: int = 500
    maximum_unusable_feature_fraction: float = 0.10


@dataclass(frozen=True, slots=True)
class GroupReadiness:
    feature_group: str
    ready: bool
    checks: dict[str, bool]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchReadinessReport:
    market: str
    interval: str
    start: datetime
    end: datetime
    policy_version: str
    market_coverage: float
    news_operational_coverage: float
    social_operational_coverage: float
    canonical_rows: int
    groups: tuple[GroupReadiness, ...]


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    manifest_id: str
    market: str
    interval: str
    start: datetime
    end: datetime
    canonical_rows: int
    feature_versions: dict[str, str]
    analyzer_versions: tuple[str, ...]
    coverage_summary: dict[str, float]
    dataset_fingerprint: str
    readiness_policy_version: str
    generated_at: datetime
    git_commit: str | None
