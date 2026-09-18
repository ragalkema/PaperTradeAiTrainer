"""Fair same-row feature-group comparison and naive baselines."""

import hashlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

from ai_trainer.application.ports.ml import RegressionModelPort
from ai_trainer.application.services.dataset import select_features
from ai_trainer.domain.entities import (
    ChronologicalSplit,
    FeatureConfiguration,
    ResearchModelResult,
    UnifiedDataset,
)
from ai_trainer.evaluation.metrics.regression import evaluate


class ZeroReturnPredictor:
    def predict(self, count: int) -> tuple[float, ...]:
        return (0.0,) * count


class PreviousReturnPredictor:
    def predict(self, rows: tuple[dict[str, float | None], ...]) -> tuple[float, ...]:
        return tuple(float(row.get("market_return_1") or 0.0) for row in rows)


class FeatureGroupComparison:
    def __init__(
        self, model_factory: Callable[[], RegressionModelPort], artifact_root: Path
    ) -> None:
        self._factory, self._root = model_factory, artifact_root

    def run(
        self, dataset: UnifiedDataset, split: ChronologicalSplit
    ) -> tuple[ResearchModelResult, ...]:
        configurations = tuple(FeatureConfiguration)
        canonical = split.test
        actual = tuple(_target(dataset, i) for i in canonical)
        timestamps = tuple(dataset.rows[i].timestamp for i in canonical)
        if len(actual) != len(canonical):
            raise ValueError("canonical test rows require targets")
        rows = tuple(
            select_features(dataset.rows[i], FeatureConfiguration.MARKET_ONLY) for i in canonical
        )
        baseline_predictions = (
            ("Zero Return", ZeroReturnPredictor().predict(len(canonical))),
            ("Previous Return", PreviousReturnPredictor().predict(rows)),
        )
        results = [
            ResearchModelResult(
                str(uuid4()),
                name,
                "baseline",
                FeatureConfiguration.MARKET_ONLY,
                ("market_return_1",) if name == "Previous Return" else (),
                evaluate(actual, predictions),
                predictions,
                actual,
                timestamps,
                dataset_fingerprint=dataset.metadata.fingerprint,
                training_period=_period(dataset, split.train),
                validation_period=_period(dataset, split.validation),
                test_period=_period(dataset, split.test),
            )
            for name, predictions in baseline_predictions
        ]
        self._root.mkdir(parents=True, exist_ok=True)
        for configuration in configurations:
            names = tuple(sorted(select_features(dataset.rows[0], configuration)))
            train_x, train_y = _matrix(dataset, split.train, names)
            validation_x, validation_y = _matrix(dataset, split.validation, names)
            test_x, _ = _matrix(dataset, split.test, names)
            model = self._factory()
            model.fit(train_x, train_y, validation_x, validation_y)
            prediction = tuple(float(x) for x in model.predict(test_x))
            model_id = str(uuid4())
            artifact = self._root / f"{model_id}.json"
            model.save(str(artifact))
            checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
            results.append(
                ResearchModelResult(
                    model_id,
                    f"XGB {configuration.value}",
                    "xgboost",
                    configuration,
                    names,
                    evaluate(actual, prediction),
                    prediction,
                    actual,
                    timestamps,
                    model.feature_importance(names),
                    getattr(model, "parameters", {}),
                    str(artifact),
                    checksum,
                    dataset.metadata.fingerprint,
                    int(getattr(model, "parameters", {}).get("random_state", 42)),
                    _period(dataset, split.train),
                    _period(dataset, split.validation),
                    _period(dataset, split.test),
                )
            )
        if any(item.timestamps != timestamps for item in results):
            raise ValueError("models did not evaluate on the canonical timestamps")
        return tuple(results)


def _matrix(
    dataset: UnifiedDataset, indices: tuple[int, ...], names: tuple[str, ...]
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(
        [
            [np.nan if row.features.get(name) is None else row.features[name] for name in names]
            for row in (dataset.rows[i] for i in indices)
        ],
        dtype=np.float64,
    )
    y = np.asarray([dataset.rows[i].target for i in indices], dtype=np.float64)
    return x, y


def _target(dataset: UnifiedDataset, index: int) -> float:
    value = dataset.rows[index].target
    if value is None:
        raise ValueError("target-complete rows required")
    return value


def _period(dataset: UnifiedDataset, indices: tuple[int, ...]) -> tuple[datetime, datetime] | None:
    if not indices:
        return None
    return dataset.rows[indices[0]].timestamp, dataset.rows[indices[-1]].timestamp
