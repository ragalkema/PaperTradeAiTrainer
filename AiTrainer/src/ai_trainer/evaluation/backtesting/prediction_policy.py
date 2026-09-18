"""Simple validation-selected prediction policy for paper research only."""

from collections.abc import Sequence

from ai_trainer.domain.entities import PaperPolicyMetrics


def select_symmetric_threshold(
    predictions: Sequence[float], actuals: Sequence[float], friction_rate: float
) -> float:
    """Choose on validation data only; caller must never pass final-test observations."""
    if len(predictions) != len(actuals) or not predictions:
        raise ValueError("equal non-empty validation predictions and actuals required")
    candidates = sorted({abs(value) for value in predictions})
    return max(
        candidates, key=lambda value: _policy_return(predictions, actuals, value, friction_rate)
    )


def evaluate_policy(
    predictions: Sequence[float],
    actuals: Sequence[float],
    *,
    threshold: float,
    starting_capital: float,
    friction_rate: float,
) -> PaperPolicyMetrics:
    if len(predictions) != len(actuals) or not predictions or starting_capital <= 0:
        raise ValueError("valid predictions, returns, and starting capital required")
    capital = starting_capital
    peak = capital
    maximum_drawdown = 0.0
    equity = [capital]
    outcomes: list[float] = []
    fees = 0.0
    previous_position = 0
    trades = 0
    for prediction, actual in zip(predictions, actuals, strict=True):
        position = 1 if prediction > threshold else -1 if prediction < -threshold else 0
        if position != previous_position:
            fees += capital * friction_rate
            capital *= 1 - friction_rate
            trades += 1
        result = position * actual
        capital *= 1 + result
        outcomes.append(result)
        peak = max(peak, capital)
        maximum_drawdown = max(maximum_drawdown, (peak - capital) / peak)
        equity.append(capital)
        previous_position = position
    wins = [x for x in outcomes if x > 0]
    losses = [x for x in outcomes if x < 0]
    return PaperPolicyMetrics(
        capital / starting_capital - 1,
        capital,
        maximum_drawdown,
        trades,
        fees,
        len(wins) / (len(wins) + len(losses)) if wins or losses else None,
        sum(wins) / abs(sum(losses)) if losses else None,
        tuple(equity),
    )


def _policy_return(
    predictions: Sequence[float], actuals: Sequence[float], threshold: float, friction: float
) -> float:
    return evaluate_policy(
        predictions,
        actuals,
        threshold=threshold,
        starting_capital=1.0,
        friction_rate=friction,
    ).total_return
