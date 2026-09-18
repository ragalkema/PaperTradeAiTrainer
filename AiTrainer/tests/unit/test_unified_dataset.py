from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trainer.application.services.dataset import (
    DatasetLeakageValidator,
    UnifiedDatasetBuilder,
    chronological_split,
    select_features,
    walk_forward_splits,
)
from ai_trainer.domain.entities import DatasetConfiguration, DatasetRow, FeatureConfiguration
from shared.contracts import Candle, MarketSymbol


def _candles(count: int = 80) -> tuple[Candle, ...]:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            MarketSymbol("BTC-EUR"),
            "1h",
            start + timedelta(hours=i),
            Decimal(100 + i),
            Decimal(102 + i),
            Decimal(99 + i),
            Decimal(101 + i),
            Decimal(10 + i),
        )
        for i in range(count)
    )


def _dataset():
    candles = _candles()
    return UnifiedDatasetBuilder().build(
        candles,
        DatasetConfiguration(
            "BTC-EUR", "1h", candles[0].timestamp, candles[-1].timestamp + timedelta(hours=1)
        ),
    )


def test_completed_candle_and_future_target_are_isolated() -> None:
    candles = list(_candles())
    original = _dataset()
    candles[-1] = Candle(
        candles[-1].market,
        "1h",
        candles[-1].timestamp,
        Decimal(999),
        Decimal(1001),
        Decimal(998),
        Decimal(1000),
        Decimal(999),
    )
    changed = UnifiedDatasetBuilder().build(
        candles,
        DatasetConfiguration(
            "BTC-EUR", "1h", candles[0].timestamp, candles[-1].timestamp + timedelta(hours=1)
        ),
    )
    assert original.rows[-2].features == changed.rows[-2].features
    assert original.rows[-2].target != changed.rows[-2].target
    assert original.rows[0].timestamp == candles[0].timestamp + timedelta(hours=1)


@pytest.mark.parametrize(
    "configuration,forbidden",
    [
        (FeatureConfiguration.MARKET_ONLY, ("news_", "social_")),
        (FeatureConfiguration.MARKET_NEWS, ("social_",)),
        (FeatureConfiguration.MARKET_SOCIAL, ("news_",)),
        (FeatureConfiguration.MARKET_NEWS_SOCIAL, ()),
    ],
)
def test_feature_group_isolation(
    configuration: FeatureConfiguration, forbidden: tuple[str, ...]
) -> None:
    features = select_features(_dataset().rows[20], configuration)
    assert features
    assert not any(name.startswith(forbidden) for name in features)


def test_purged_chronological_and_walk_forward_splits() -> None:
    dataset = _dataset()
    split = chronological_split(dataset.rows, purge=timedelta(hours=1))
    DatasetLeakageValidator().validate(dataset, split)
    assert max(split.train) < min(split.validation) < max(split.validation) < min(split.test)
    folds = walk_forward_splits(dataset.rows, 3)
    assert len(folds) == 3 and all(fold.train[-1] < fold.test[0] for fold in folds)


def test_validator_rejects_future_and_retrospective_features() -> None:
    dataset = _dataset()
    row = dataset.rows[0]
    bad = DatasetRow(
        row.timestamp,
        {"news_market_impact": 1.0},
        {"news_market_impact": row.timestamp + timedelta(seconds=1)},
        row.target,
        row.target_at,
    )
    with pytest.raises(ValueError):
        DatasetLeakageValidator().validate(type(dataset)(dataset.metadata, (bad,)))
