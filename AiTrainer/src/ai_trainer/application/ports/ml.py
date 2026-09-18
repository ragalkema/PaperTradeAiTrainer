"""Replaceable supervised-model boundary."""

from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class RegressionModelPort(Protocol):
    def fit(
        self,
        features: NDArray[np.float64],
        targets: NDArray[np.float64],
        validation_features: NDArray[np.float64],
        validation_targets: NDArray[np.float64],
    ) -> None: ...

    def predict(self, features: NDArray[np.float64]) -> NDArray[np.float64]: ...
    def feature_importance(self, names: tuple[str, ...]) -> dict[str, float]: ...
    def save(self, path: str) -> None: ...
