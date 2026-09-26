"""Bounded Optuna tuning on rolling pre-policy-validation folds only."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import optuna

from ai_trainer.domain.entities import DatasetRow
from ai_trainer.infrastructure.models import XGBoostRegressorAdapter


def tuning_folds(rows: Sequence[DatasetRow]) -> tuple[tuple[tuple[int, ...], ...], ...]:
    if len(rows) < 200:
        raise ValueError("tuning requires at least 200 pre-validation rows")
    folds = []
    for fraction in (0.5, 0.7):
        boundary = int(len(rows) * fraction)
        stopping = int(boundary * 0.8)
        end = min(len(rows), int(len(rows) * (fraction + 0.2)))
        train = tuple(
            i
            for i in range(stopping)
            if (target := rows[i].target_at) is not None and target < rows[stopping].timestamp
        )
        stop = tuple(
            i
            for i in range(stopping, boundary)
            if (target := rows[i].target_at) is not None and target < rows[boundary].timestamp
        )
        score = tuple(
            i
            for i in range(boundary, end)
            if (target := rows[i].target_at) is not None and target <= rows[end - 1].timestamp
        )
        if min(len(train), len(stop), len(score)) < 10:
            raise ValueError("insufficient purged tuning fold")
        folds.append((train, stop, score))
    return tuple(folds)


def tune(
    rows: Sequence[DatasetRow],
    names: Sequence[str],
    trials: int,
    storage_path: Path,
    study_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not 1 <= trials <= 100:
        raise ValueError("trials must be between 1 and 100 per candidate")
    folds = tuning_folds(rows)
    matrix = np.asarray(
        [[np.nan if r.features.get(n) is None else r.features[n] for n in names] for r in rows],
        dtype=float,
    )
    targets = np.asarray([r.target for r in rows], dtype=float)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    study = optuna.create_study(
        study_name=study_name,
        storage=f"sqlite:///{storage_path.resolve().as_posix()}",
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=42),
        load_if_exists=False,
    )
    # Include the existing model as a reproducible reference trial.
    study.enqueue_trial(
        {
            "max_depth": 4,
            "learning_rate": 0.03,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
        }
    )

    def objective(trial: optuna.Trial) -> float:
        params = {
            "max_depth": trial.suggest_int("max_depth", 2, 5),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.08, log=True),
            "min_child_weight": trial.suggest_int("min_child_weight", 5, 40),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 0.1, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10, log=True),
        }
        scores = []
        for training, stopping, held in folds:
            model = XGBoostRegressorAdapter(params)
            model.fit(
                matrix[list(training)],
                targets[list(training)],
                matrix[list(stopping)],
                targets[list(stopping)],
            )
            prediction = model.predict(matrix[list(held)])
            baseline_mse = float(
                np.mean((targets[list(held)] - targets[list(training)].mean()) ** 2)
            )
            scores.append(
                float(np.mean((prediction - targets[list(held)]) ** 2)) / max(baseline_mse, 1e-12)
            )
        trial.set_user_attr("fold_normalized_mse", scores)
        return float(np.mean(scores))

    study.optimize(objective, n_trials=trials, n_jobs=1)
    return study.best_params, {
        "study": study_name,
        "storage": str(storage_path),
        "trials": len(study.trials),
        "best_normalized_mse": study.best_value,
        "latest_input_time": rows[-1].timestamp.isoformat(),
        "folds": [
            {
                "train_end": rows[a[-1]].timestamp.isoformat(),
                "stopping_start": rows[b[0]].timestamp.isoformat(),
                "score_start": rows[c[0]].timestamp.isoformat(),
                "score_end": rows[c[-1]].timestamp.isoformat(),
            }
            for a, b, c in folds
        ],
    }
