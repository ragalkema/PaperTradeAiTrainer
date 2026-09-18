from pathlib import Path

import numpy as np
from ai_trainer.evaluation.metrics.regression import evaluate
from ai_trainer.infrastructure.models import XGBoostRegressorAdapter


def test_xgboost_learns_deterministic_synthetic_signal(tmp_path: Path) -> None:
    generator = np.random.default_rng(42)
    x = generator.normal(size=(320, 2))
    y = 0.8 * x[:, 0] - 0.2 * x[:, 1]
    model = XGBoostRegressorAdapter(
        {
            "n_estimators": 180,
            "max_depth": 3,
            "learning_rate": 0.05,
            "random_state": 42,
            "early_stopping_rounds": 15,
        }
    )
    model.fit(x[:220], y[:220], x[220:270], y[220:270])
    prediction = model.predict(x[270:])
    metrics = evaluate(y[270:].tolist(), prediction.tolist())
    assert metrics.pearson is not None and metrics.pearson > 0.9
    assert metrics.rmse < 0.2
    assert model.feature_importance(("signal", "secondary"))["signal"] > 0
    artifact = tmp_path / "model.json"
    model.save(str(artifact))
    assert artifact.stat().st_size > 0


def test_noise_metrics_are_reported_without_automatic_claim() -> None:
    generator = np.random.default_rng(7)
    actual = generator.normal(size=100)
    noise = generator.normal(size=100)
    result = evaluate(actual.tolist(), noise.tolist())
    assert not hasattr(result, "beneficial")
