"""Deterministic unified dataset construction, validation, and chronological splitting."""

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from statistics import mean
from uuid import NAMESPACE_URL, uuid5

from data_collector.domain.entities import NewsFeatureSnapshot, SocialFeatureSnapshot
from shared.contracts import Candle

from ai_trainer.application.services.market_features import VERSION, market_features
from ai_trainer.domain.entities import (
    ChronologicalSplit,
    DatasetConfiguration,
    DatasetMetadata,
    DatasetRow,
    FeatureConfiguration,
    FeatureGroup,
    UnifiedDataset,
    ValidationReport,
)

TARGET_VERSION = "future_return_v1"
NEWS_VERSION = "online_news_features_v1"
SOCIAL_VERSION = "online_social_features_v1"
_INTERVALS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}


class UnifiedDatasetBuilder:
    """Compose completed candles and already point-in-time-safe intelligence snapshots."""

    def build(
        self,
        candles: Sequence[Candle],
        configuration: DatasetConfiguration,
        *,
        news: Mapping[datetime, NewsFeatureSnapshot] | None = None,
        social: Mapping[datetime, SocialFeatureSnapshot] | None = None,
        git_commit: str | None = None,
    ) -> UnifiedDataset:
        seconds = _INTERVALS.get(configuration.interval)
        if seconds is None:
            raise ValueError(f"unsupported dataset interval: {configuration.interval}")
        ordered = sorted(candles, key=lambda x: x.timestamp)
        if any(
            str(x.market) != configuration.market or x.interval != configuration.interval
            for x in ordered
        ):
            raise ValueError("all candles must match dataset market and interval")
        if len({x.timestamp for x in ordered}) != len(ordered):
            raise ValueError("duplicate candle timestamps")
        candle_step = timedelta(seconds=seconds)
        close_by_time = {item.timestamp + candle_step: float(item.close) for item in ordered}
        rows: list[DatasetRow] = []
        analyzers: set[str] = set()
        for index, candle in enumerate(ordered):
            decision_time = candle.timestamp + candle_step
            if not configuration.start_time <= decision_time <= configuration.end_time:
                continue
            values = market_features(ordered, index)
            observed = {name: decision_time for name in values}
            if FeatureGroup.NEWS in configuration.feature_configuration.groups:
                news_snapshot = (news or {}).get(decision_time)
                values.update(_news_values(news_snapshot))
                observed.update(
                    {name: decision_time for name in values if name.startswith("news_")}
                )
                if news_snapshot:
                    analyzers.update(news_snapshot.analyzer_versions)
            if FeatureGroup.SOCIAL in configuration.feature_configuration.groups:
                social_snapshot = (social or {}).get(decision_time)
                values.update(_social_values(social_snapshot))
                observed.update(
                    {name: decision_time for name in values if name.startswith("social_")}
                )
                if social_snapshot:
                    analyzers.update(social_snapshot.analyzer_versions)
            target_at = decision_time + configuration.target_horizon
            target_price = close_by_time.get(target_at)
            target = target_price / float(candle.close) - 1 if target_price is not None else None
            rows.append(DatasetRow(decision_time, values, observed, target, target_at))
        fingerprint = _fingerprint(configuration, ordered)
        metadata = DatasetMetadata(
            str(uuid5(NAMESPACE_URL, fingerprint)),
            fingerprint,
            configuration.market,
            configuration.interval,
            configuration.start_time,
            configuration.end_time,
            tuple(sorted(x.value for x in configuration.feature_configuration.groups)),
            VERSION,
            NEWS_VERSION,
            SOCIAL_VERSION,
            TARGET_VERSION,
            int(configuration.target_horizon.total_seconds()),
            tuple(sorted(analyzers)),
            datetime.now(UTC),
            git_commit,
        )
        dataset = UnifiedDataset(metadata, tuple(rows))
        report = DatasetValidator(candle_step).validate(dataset)
        return UnifiedDataset(metadata, tuple(rows), report)


class DatasetValidator:
    def __init__(self, expected_interval: timedelta) -> None:
        self._interval = expected_interval

    def validate(self, dataset: UnifiedDataset) -> ValidationReport:
        rows = dataset.rows
        timestamps = [x.timestamp for x in rows]
        duplicates = len(timestamps) - len(set(timestamps))
        if timestamps != sorted(timestamps):
            raise ValueError("dataset timestamps are not chronological")
        missing = sum(max(0, int((b - a) / self._interval) - 1) for a, b in pairwise(timestamps))
        names = sorted({name for row in rows for name in row.features})
        absent = {name: sum(row.features.get(name) is None for row in rows) for name in names}
        infinite = sum(
            not math.isfinite(value)
            for row in rows
            for value in row.features.values()
            if value is not None
        )
        distributions = {
            name: _distribution([r.features.get(name) for r in rows]) for name in names
        }
        targets = [x.target for x in rows]
        report = ValidationReport(
            len(rows),
            timestamps[0] if rows else None,
            timestamps[-1] if rows else None,
            duplicates,
            missing,
            absent,
            sum(x is None for x in targets),
            infinite,
            distributions,
            _distribution(targets),
            _coverage(rows, "news_"),
            _coverage(rows, "social_"),
        )
        if duplicates or infinite:
            raise ValueError("serious dataset integrity violation")
        return report


class DatasetLeakageValidator:
    FORBIDDEN = ("impact", "reaction", "future_return", "target")

    def validate(self, dataset: UnifiedDataset, split: ChronologicalSplit | None = None) -> None:
        previous: datetime | None = None
        for row in dataset.rows:
            if previous is not None and row.timestamp <= previous:
                raise ValueError("unordered or duplicate dataset timestamp")
            previous = row.timestamp
            if any(observed > row.timestamp for observed in row.feature_observed_at.values()):
                raise ValueError("feature observed after row timestamp")
            if any(any(token in name.lower() for token in self.FORBIDDEN) for name in row.features):
                raise ValueError("retrospective or target field found in feature matrix")
            if row.target_at is not None and row.target_at <= row.timestamp:
                raise ValueError("target must occur after feature timestamp")
        if split:
            _validate_split(dataset.rows, split)


def chronological_split(
    rows: Sequence[DatasetRow],
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    purge: timedelta = timedelta(hours=1),
) -> ChronologicalSplit:
    usable = [i for i, row in enumerate(rows) if row.target is not None]
    if (
        len(usable) < 12
        or train_ratio <= 0
        or validation_ratio <= 0
        or train_ratio + validation_ratio >= 1
    ):
        raise ValueError("at least 12 target-complete rows and valid ratios are required")
    train_end = int(len(usable) * train_ratio)
    validation_end = int(len(usable) * (train_ratio + validation_ratio))
    validation_start_time = rows[usable[train_end]].timestamp
    test_start_time = rows[usable[validation_end]].timestamp
    train = tuple(
        i
        for i in usable[:train_end]
        if (target_at := rows[i].target_at) is not None
        and target_at <= validation_start_time - purge
    )
    validation = tuple(
        i
        for i in usable[train_end:validation_end]
        if (target_at := rows[i].target_at) is not None and target_at <= test_start_time - purge
    )
    result = ChronologicalSplit(train, validation, tuple(usable[validation_end:]), purge)
    DatasetLeakageValidator().validate(UnifiedDataset(_dummy_metadata(rows), tuple(rows)), result)
    return result


def walk_forward_splits(
    rows: Sequence[DatasetRow], folds: int = 3, purge: timedelta = timedelta(hours=1)
) -> tuple[ChronologicalSplit, ...]:
    usable = [i for i, row in enumerate(rows) if row.target is not None]
    block = len(usable) // (folds + 1)
    if block < 2:
        raise ValueError("insufficient rows for walk-forward validation")
    output = []
    for fold in range(folds):
        boundary = block * (fold + 1)
        test = usable[boundary : boundary + block]
        start = rows[test[0]].timestamp
        train = tuple(
            i
            for i in usable[:boundary]
            if (target_at := rows[i].target_at) is not None and target_at <= start - purge
        )
        output.append(ChronologicalSplit(train, (), tuple(test), purge))
    return tuple(output)


def select_features(
    row: DatasetRow, configuration: FeatureConfiguration
) -> dict[str, float | None]:
    prefixes = tuple(f"{x.value}_" for x in configuration.groups)
    return {name: value for name, value in row.features.items() if name.startswith(prefixes)}


def _news_values(x: NewsFeatureSnapshot | None) -> dict[str, float | None]:
    return _snapshot_values(
        x,
        "news",
        {
            "news_count_15m": "news_count_15m",
            "news_count_1h": "news_count_1h",
            "news_count_6h": "news_count_6h",
            "max_relevance_1h": "max_relevance_1h",
            "mean_sentiment_15m": "mean_sentiment_15m",
            "mean_sentiment_1h": "mean_sentiment_1h",
            "mean_sentiment_6h": "mean_sentiment_6h",
            "weighted_sentiment_1h": "relevance_weighted_sentiment_1h",
            "max_importance_1h": "max_importance_1h",
            "mean_importance_1h": "mean_importance_1h",
            "max_novelty_1h": "max_novelty_1h",
            "breaking_count_15m": "breaking_news_count_15m",
        },
    )


def _social_values(x: SocialFeatureSnapshot | None) -> dict[str, float | None]:
    return _snapshot_values(
        x,
        "social",
        {
            "count_15m": "post_count_15m",
            "count_1h": "post_count_1h",
            "count_6h": "post_count_6h",
            "unique_accounts_1h": "unique_accounts_1h",
            "mean_sentiment_15m": "mean_sentiment_15m",
            "mean_sentiment_1h": "mean_sentiment_1h",
            "mean_sentiment_6h": "mean_sentiment_6h",
            "weighted_sentiment_1h": "weighted_sentiment_1h",
            "max_relevance_1h": "max_relevance_1h",
            "max_importance_1h": "max_importance_1h",
            "max_novelty_1h": "max_novelty_1h",
            "high_influence_posts_1h": "high_influence_post_count_1h",
            "breaking_count_15m": "breaking_post_count_15m",
            "activity_zscore": "social_activity_zscore",
            "engagement_velocity": "engagement_velocity_1h",
        },
    )


def _snapshot_values(
    snapshot: object | None, prefix: str, fields: Mapping[str, str]
) -> dict[str, float | None]:
    if snapshot is None:
        return {f"{prefix}_{name}": None for name in fields}
    return {
        f"{prefix}_{name}": float(value) if (value := getattr(snapshot, attr)) is not None else None
        for name, attr in fields.items()
    }


def _fingerprint(config: DatasetConfiguration, candles: Sequence[Candle]) -> str:
    identity = [
        (x.timestamp.isoformat(), str(x.open), str(x.high), str(x.low), str(x.close), str(x.volume))
        for x in candles
    ]
    payload = {
        "configuration": asdict(config),
        "versions": [VERSION, NEWS_VERSION, SOCIAL_VERSION, TARGET_VERSION],
        "candles": identity,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _distribution(values: Sequence[float | None]) -> dict[str, float | None]:
    clean = sorted(float(x) for x in values if x is not None and math.isfinite(float(x)))
    if not clean:
        return {"mean": None, "std": None, "min": None, "p50": None, "max": None}
    avg = mean(clean)
    return {
        "mean": avg,
        "std": math.sqrt(mean([(x - avg) ** 2 for x in clean])),
        "min": clean[0],
        "p50": clean[len(clean) // 2],
        "max": clean[-1],
    }


def _coverage(rows: Sequence[DatasetRow], prefix: str) -> float:
    relevant = [
        any(name.startswith(prefix) and value is not None for name, value in row.features.items())
        for row in rows
    ]
    return sum(relevant) / len(relevant) if relevant else 0.0


def _validate_split(rows: Sequence[DatasetRow], split: ChronologicalSplit) -> None:
    groups = (split.train, split.validation, split.test)
    if any(set(a) & set(b) for i, a in enumerate(groups) for b in groups[i + 1 :]):
        raise ValueError("split indices overlap")
    for left, right in pairwise(groups):
        if (
            left
            and right
            and (target_at := rows[left[-1]].target_at) is not None
            and target_at > rows[right[0]].timestamp - split.purge
        ):
            raise ValueError("target horizon crosses a purged split boundary")


def _dummy_metadata(rows: Sequence[DatasetRow]) -> DatasetMetadata:
    now = rows[0].timestamp if rows else datetime.now(UTC)
    return DatasetMetadata("", "", "", "", now, now, (), "", "", "", "", 0, (), now, None)
