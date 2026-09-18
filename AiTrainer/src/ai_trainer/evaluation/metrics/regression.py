"""Dependency-light regression metrics with explicit degenerate-case handling."""

import math
from collections.abc import Sequence

from ai_trainer.domain.entities import ModelEvaluation


def evaluate(actual: Sequence[float], predicted: Sequence[float]) -> ModelEvaluation:
    if not actual or len(actual) != len(predicted):
        raise ValueError("actual and predicted must have equal non-zero lengths")
    pairs = [
        (a, p)
        for a, p in zip(actual, predicted, strict=True)
        if math.isfinite(a) and math.isfinite(p)
    ]
    if not pairs:
        raise ValueError("no finite actual/predicted pairs")
    actual = [a for a, _ in pairs]
    predicted = [p for _, p in pairs]
    errors = [p - a for a, p in zip(actual, predicted, strict=True)]
    mae = sum(abs(x) for x in errors) / len(errors)
    rmse = math.sqrt(sum(x * x for x in errors) / len(errors))
    average = sum(actual) / len(actual)
    total = sum((x - average) ** 2 for x in actual)
    r2 = 1 - sum(x * x for x in errors) / total if total else None
    direction = sum((a >= 0) == (p >= 0) for a, p in zip(actual, predicted, strict=True)) / len(
        actual
    )
    return ModelEvaluation(
        mae,
        rmse,
        r2,
        _correlation(actual, predicted),
        _correlation(_ranks(actual), _ranks(predicted)),
        direction,
        _summary(predicted),
        _summary(actual),
    )


def _correlation(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) < 2:
        return None
    am, bm = sum(a) / len(a), sum(b) / len(b)
    numerator = sum((x - am) * (y - bm) for x, y in zip(a, b, strict=True))
    denominator = math.sqrt(sum((x - am) ** 2 for x in a) * sum((y - bm) ** 2 for y in b))
    return numerator / denominator if denominator else None


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        rank = (position + end) / 2 + 1
        for index in order[position : end + 1]:
            result[index] = rank
        position = end + 1
    return result


def _summary(values: Sequence[float]) -> dict[str, float]:
    ordered = sorted(values)
    average = sum(values) / len(values)

    def percentile(p: float) -> float:
        return ordered[round((len(ordered) - 1) * p)]

    return {
        "mean": average,
        "std": math.sqrt(sum((x - average) ** 2 for x in values) / len(values)),
        "p05": percentile(0.05),
        "p50": percentile(0.5),
        "p95": percentile(0.95),
    }
