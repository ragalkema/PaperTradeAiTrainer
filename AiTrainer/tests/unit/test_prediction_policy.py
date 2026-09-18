import pytest
from ai_trainer.evaluation.backtesting.prediction_policy import (
    evaluate_policy,
    select_symmetric_threshold,
)


def test_threshold_uses_supplied_validation_data_and_policy_reports_metrics() -> None:
    predictions = [-0.04, -0.01, 0.0, 0.02, 0.05]
    actuals = [-0.03, -0.01, 0.0, 0.01, 0.04]
    threshold = select_symmetric_threshold(predictions, actuals, 0.001)
    result = evaluate_policy(
        predictions, actuals, threshold=threshold, starting_capital=1000, friction_rate=0.001
    )
    assert threshold in {abs(x) for x in predictions}
    assert result.final_portfolio > 1000 and result.trades > 0 and result.fees > 0


def test_policy_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        select_symmetric_threshold([], [], 0)
    with pytest.raises(ValueError):
        evaluate_policy([1], [], threshold=0, starting_capital=1, friction_rate=0)
