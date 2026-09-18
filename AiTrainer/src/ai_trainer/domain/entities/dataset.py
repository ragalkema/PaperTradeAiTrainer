"""Versioned, point-in-time supervised research dataset contracts."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any


class FeatureGroup(StrEnum):
    MARKET = "market"
    NEWS = "news"
    SOCIAL = "social"


class FeatureConfiguration(StrEnum):
    MARKET_ONLY = "market_only"
    MARKET_NEWS = "market_news"
    MARKET_SOCIAL = "market_social"
    MARKET_NEWS_SOCIAL = "market_news_social"

    @property
    def groups(self) -> frozenset[FeatureGroup]:
        values = {
            self.MARKET_ONLY: (FeatureGroup.MARKET,),
            self.MARKET_NEWS: (FeatureGroup.MARKET, FeatureGroup.NEWS),
            self.MARKET_SOCIAL: (FeatureGroup.MARKET, FeatureGroup.SOCIAL),
            self.MARKET_NEWS_SOCIAL: tuple(FeatureGroup),
        }
        return frozenset(values[self])


@dataclass(frozen=True, slots=True)
class DatasetConfiguration:
    market: str
    interval: str
    start_time: datetime
    end_time: datetime
    target_horizon: timedelta = timedelta(hours=1)
    feature_configuration: FeatureConfiguration = FeatureConfiguration.MARKET_NEWS_SOCIAL
    random_seed: int = 42

    def __post_init__(self) -> None:
        if self.market not in {"BTC-EUR", "ETH-EUR", "SOL-EUR"}:
            raise ValueError("supported markets are BTC-EUR, ETH-EUR, and SOL-EUR")
        if any(x.tzinfo is None or x.utcoffset() is None for x in (self.start_time, self.end_time)):
            raise ValueError("dataset timestamps must be timezone-aware")
        if self.end_time <= self.start_time or self.target_horizon <= timedelta(0):
            raise ValueError("dataset period and target horizon must be positive")


@dataclass(frozen=True, slots=True)
class DatasetRow:
    timestamp: datetime
    features: dict[str, float | None]
    feature_observed_at: dict[str, datetime]
    target: float | None = None
    target_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    dataset_id: str
    fingerprint: str
    market: str
    interval: str
    start_time: datetime
    end_time: datetime
    feature_groups: tuple[str, ...]
    market_feature_version: str
    news_feature_version: str
    social_feature_version: str
    target_version: str
    target_horizon_seconds: int
    analyzer_versions: tuple[str, ...]
    created_at: datetime
    git_commit: str | None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    row_count: int
    start_time: datetime | None
    end_time: datetime | None
    duplicate_timestamps: int
    missing_timestamps: int
    feature_missingness: dict[str, int]
    target_missingness: int
    infinite_values: int
    feature_distributions: dict[str, dict[str, float | None]]
    target_distribution: dict[str, float | None]
    news_coverage: float
    social_coverage: float


@dataclass(frozen=True, slots=True)
class UnifiedDataset:
    metadata: DatasetMetadata
    rows: tuple[DatasetRow, ...]
    validation: ValidationReport | None = None


@dataclass(frozen=True, slots=True)
class ChronologicalSplit:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]
    purge: timedelta


@dataclass(frozen=True, slots=True)
class ModelEvaluation:
    mae: float
    rmse: float
    r_squared: float | None
    pearson: float | None
    spearman: float | None
    directional_accuracy: float
    prediction_distribution: dict[str, float]
    actual_distribution: dict[str, float]


@dataclass(frozen=True, slots=True)
class ResearchModelResult:
    model_id: str
    name: str
    algorithm: str
    feature_configuration: FeatureConfiguration
    feature_names: tuple[str, ...]
    metrics: ModelEvaluation
    predictions: tuple[float, ...]
    actuals: tuple[float, ...]
    timestamps: tuple[datetime, ...]
    feature_importance: dict[str, float] = field(default_factory=dict)
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    artifact_path: str | None = None
    artifact_checksum: str | None = None
    dataset_fingerprint: str = ""
    random_seed: int = 42
    training_period: tuple[datetime, datetime] | None = None
    validation_period: tuple[datetime, datetime] | None = None
    test_period: tuple[datetime, datetime] | None = None


@dataclass(frozen=True, slots=True)
class PaperPolicyMetrics:
    total_return: float
    final_portfolio: float
    maximum_drawdown: float
    trades: int
    fees: float
    win_rate: float | None
    profit_factor: float | None
    equity: tuple[float, ...]
