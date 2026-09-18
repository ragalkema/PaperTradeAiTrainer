from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

import numpy as np
from ai_trainer.application.services.dataset import chronological_split
from ai_trainer.domain.entities import (
    DatasetMetadata,
    DatasetRow,
    FeatureConfiguration,
    UnifiedDataset,
)
from ai_trainer.training.supervised.comparison import FeatureGroupComparison
from numpy.typing import NDArray


class MeanModel:
    parameters: ClassVar[dict[str, int]] = {"random_state": 42}

    def fit(
        self,
        features: NDArray[np.float64],
        targets: NDArray[np.float64],
        validation_features: NDArray[np.float64],
        validation_targets: NDArray[np.float64],
    ) -> None:
        self.value = float(np.mean(targets))

    def predict(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.full(features.shape[0], self.value)

    def feature_importance(self, names: tuple[str, ...]) -> dict[str, float]:
        return dict.fromkeys(names, 0.0)

    def save(self, path: str) -> None:
        Path(path).write_text(str(self.value), encoding="utf-8")


def _dataset() -> UnifiedDataset:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for index in range(80):
        timestamp = start + timedelta(hours=index)
        rows.append(
            DatasetRow(
                timestamp,
                {
                    "market_return_1": index / 1000,
                    "news_count_1h": None if index % 2 else 0.0,
                    "social_count_1h": None,
                },
                {
                    "market_return_1": timestamp,
                    "news_count_1h": timestamp,
                    "social_count_1h": timestamp,
                },
                index / 10000,
                timestamp + timedelta(hours=1),
            )
        )
    metadata = DatasetMetadata(
        "id",
        "fingerprint",
        "BTC-EUR",
        "1h",
        start,
        rows[-1].timestamp,
        ("market", "news", "social"),
        "market_features_v1",
        "online_news_features_v1",
        "online_social_features_v1",
        "future_return_v1",
        3600,
        (),
        start,
        "abc",
    )
    return UnifiedDataset(metadata, tuple(rows))


def test_all_variants_share_canonical_test_rows_and_isolate_features(tmp_path: Path) -> None:
    dataset = _dataset()
    results = FeatureGroupComparison(MeanModel, tmp_path).run(
        dataset, chronological_split(dataset.rows)
    )
    assert len(results) == 6
    assert all(result.timestamps == results[0].timestamps for result in results)
    variants = {
        result.feature_configuration: result for result in results if result.algorithm == "xgboost"
    }
    assert not any(
        name.startswith(("news_", "social_"))
        for name in variants[FeatureConfiguration.MARKET_ONLY].feature_names
    )
    assert not any(
        name.startswith("social_")
        for name in variants[FeatureConfiguration.MARKET_NEWS].feature_names
    )
    assert not any(
        name.startswith("news_")
        for name in variants[FeatureConfiguration.MARKET_SOCIAL].feature_names
    )
    assert variants[FeatureConfiguration.MARKET_NEWS_SOCIAL].artifact_checksum
