import math

import pytest
from ai_trainer.evaluation.metrics.regression import evaluate


def test_metrics_handle_constants_and_non_finite_pairs() -> None:
    result = evaluate([1.0, 1.0, math.nan], [1.0, 1.0, 2.0])
    assert result.r_squared is None and result.pearson is None and result.spearman is None
    assert result.rmse == 0


def test_metrics_reject_no_finite_pairs() -> None:
    with pytest.raises(ValueError):
        evaluate([math.nan], [math.nan])
