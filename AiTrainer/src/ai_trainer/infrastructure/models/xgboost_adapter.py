"""XGBoost implementation of the regression model port."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


class XGBoostRegressorAdapter:
    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise RuntimeError("Install the 'ml' extra to train XGBoost models") from exc
        defaults: dict[str, Any] = {
            "objective": "reg:squarederror",
            "n_estimators": 300,
            "max_depth": 4,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": 1,
            "tree_method": "hist",
            "early_stopping_rounds": 30,
        }
        defaults.update(parameters or {})
        self.parameters = defaults
        self._model = XGBRegressor(**defaults)

    def fit(
        self,
        features: NDArray[np.float64],
        targets: NDArray[np.float64],
        validation_features: NDArray[np.float64],
        validation_targets: NDArray[np.float64],
    ) -> None:
        self._model.fit(
            features, targets, eval_set=[(validation_features, validation_targets)], verbose=False
        )

    def predict(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.asarray(self._model.predict(features), dtype=np.float64)

    def feature_importance(self, names: tuple[str, ...]) -> dict[str, float]:
        booster = self._model.get_booster()
        scores = booster.get_score(importance_type="gain")
        output = {}
        for index, name in enumerate(names):
            value = scores.get(f"f{index}", scores.get(name, 0.0))
            output[name] = float(value) if isinstance(value, (int, float)) else 0.0
        return output

    def save(self, path: str) -> None:
        self._model.save_model(path)
