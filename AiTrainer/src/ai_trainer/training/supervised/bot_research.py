"""Cost-aware, same-timestamp horizon research for spot paper bots.

Train -> early stopping -> policy selection -> untouched test. No network access.
Endpoint returns are research estimates, not a limit-order execution simulator.
"""

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from shared.contracts import Candle

from ai_trainer.application.services.dataset import DatasetLeakageValidator
from ai_trainer.domain.entities import DatasetRow, UnifiedDataset
from ai_trainer.evaluation.backtesting.candle_execution import (
    ExecutionWindow,
    buy_and_hold,
    execution_windows,
    simulate,
)
from ai_trainer.infrastructure.models import XGBoostRegressorAdapter

HORIZONS = (1, 2, 6, 12, 24)


@dataclass(frozen=True)
class Costs:
    fee_per_side: float = 0.0025
    spread_slippage_per_side: float = 0.001

    def __post_init__(self) -> None:
        if any(not math.isfinite(x) or not 0 <= x < 0.1 for x in asdict(self).values()):
            raise ValueError("costs must be finite fractions in [0, 0.1)")

    @property
    def side(self) -> float:
        return self.fee_per_side + self.spread_slippage_per_side

    def net(self, gross: float) -> float:
        fee, slip = self.fee_per_side, self.spread_slippage_per_side
        return (1 + gross) * (1 - slip) * (1 - fee) / ((1 + slip) * (1 + fee)) - 1


def horizon_rows(dataset: UnifiedDataset) -> dict[int, tuple[DatasetRow, ...]]:
    """Require continuous warmup and all five outcomes on a common decision grid."""
    DatasetLeakageValidator().validate(dataset)
    rows = dataset.rows
    by_time = {row.timestamp: row for row in rows}
    output: dict[int, list[DatasetRow]] = {h: [] for h in HORIZONS}
    for row in rows:
        # Consecutive one-hour returns reconstruct every future endpoint. No gap bridging.
        window = [by_time.get(row.timestamp + timedelta(hours=i)) for i in range(-24, 24)]
        if any(x is None for x in window):
            continue
        future = window[24:]
        if any(x is None or x.target is None for x in future):
            continue
        for horizon in HORIZONS:
            gross = (
                math.prod(
                    (
                        1 + x.target
                        for x in future[:horizon]
                        if x is not None and x.target is not None
                    ),
                    start=1.0,
                )
                - 1
            )
            output[horizon].append(
                replace(row, target=gross, target_at=row.timestamp + timedelta(hours=horizon))
            )
    return {h: tuple(values) for h, values in output.items()}


def split_periods(
    rows: Sequence[DatasetRow], validation_start: datetime, test_start: datetime
) -> tuple[tuple[DatasetRow, ...], ...]:
    """Use a separate last 20% of pre-validation history for early stopping."""
    before = [r for r in rows if r.timestamp < validation_start]
    if len(before) < 250:
        raise ValueError("need at least 250 pre-validation rows")
    stopping_start = before[int(len(before) * 0.8)].timestamp
    # The same maximum horizon purge applies to all candidates.
    ranges = (
        (rows[0].timestamp, stopping_start),
        (stopping_start, validation_start),
        (validation_start, test_start),
        (test_start, rows[-1].timestamp + timedelta(hours=25)),
    )
    groups = tuple(
        tuple(
            r
            for r in rows
            if start <= r.timestamp < end and r.timestamp + timedelta(hours=25) < end
        )
        for start, end in ranges
    )
    if any(len(group) < 30 for group in groups):
        raise ValueError("each chronological partition needs at least 30 common rows")
    return groups


def policy(
    rows: Sequence[DatasetRow], predictions: Sequence[float], edge: float, costs: Costs
) -> dict[str, float | int]:
    """One long position at a time, 10% of current equity, entry AND exit costs."""
    if len(rows) != len(predictions) or not rows:
        raise ValueError("equal nonempty rows and predictions required")
    equity = peak = 1.0
    drawdown = 0.0
    trades = wins = 0
    available = rows[0].timestamp
    for row, prediction in zip(rows, predictions, strict=True):
        if row.timestamp < available or costs.net(prediction) <= edge:
            continue
        if row.target is None or row.target_at is None:
            raise ValueError("completed targets required")
        net = costs.net(row.target)
        equity *= 1 + 0.1 * net
        peak = max(peak, equity)
        drawdown = max(drawdown, 1 - equity / peak)
        trades += 1
        wins += net > 0
        available = row.target_at
    return {
        "net_return": equity - 1,
        "closed_trade_drawdown": drawdown,
        "trades": trades,
        "wins_after_costs": wins,
    }


def _matrix(rows: Sequence[DatasetRow], names: Sequence[str]) -> np.ndarray:
    return np.asarray(
        [[np.nan if r.features.get(n) is None else r.features[n] for n in names] for r in rows],
        dtype=np.float64,
    )


def _score(result: dict[str, float | int]) -> float:
    if result["trades"] < 10:
        return -math.inf
    return float(
        result["net_return"] - result.get("max_drawdown", result.get("closed_trade_drawdown", 0))
    )


def diagnostics(
    predictions: Sequence[float], actual: Sequence[float], costs: Costs
) -> dict[str, Any]:
    p, y = np.asarray(predictions), np.asarray(actual)
    return {
        "predicted_mean": float(p.mean()),
        "predicted_std": float(p.std()),
        "actual_mean": float(y.mean()),
        "actual_std": float(y.std()),
        "bias": float((p - y).mean()),
        "rmse": float(np.sqrt(np.mean((p - y) ** 2))),
        "zero_baseline_rmse": float(np.sqrt(np.mean(y**2))),
        "fraction_above_cost": float(np.mean([costs.net(float(x)) > 0 for x in p])),
        "prediction_p05_p50_p95": np.quantile(p, [0.05, 0.5, 0.95]).tolist(),
    }


def run_research(
    dataset: UnifiedDataset,
    validation_start: datetime,
    test_start: datetime,
    output: Path,
    costs: Costs | None = None,
    *,
    candles: Sequence[Candle] | None = None,
    optuna_trials: int = 0,
) -> dict[str, Any]:
    configured_costs = costs or Costs()
    costs = configured_costs
    if dataset.metadata.interval != "1h" or dataset.metadata.target_horizon_seconds != 3600:
        raise ValueError("research requires one-hour candles and one-hour base targets")
    if not validation_start < test_start:
        raise ValueError("validation must precede test")
    if not 0 <= optuna_trials <= 100:
        raise ValueError("optuna trials must be 0-100 per candidate")
    output.mkdir(parents=True, exist_ok=False)
    candidates: list[dict[str, Any]] = []
    prepared = horizon_rows(dataset)
    execution: dict[int, dict[datetime, ExecutionWindow]] = {}
    if candles is not None:
        execution = {
            h: execution_windows(candles, [r.timestamp for r in rows], h)
            for h, rows in prepared.items()
        }
        common = set.intersection(*(set(w) for w in execution.values()))
        prepared = {
            h: tuple(
                replace(
                    r,
                    target=execution[h][r.timestamp].gross_return,
                    target_at=execution[h][r.timestamp].exit_at,
                )
                for r in rows
                if r.timestamp in common
            )
            for h, rows in prepared.items()
        }
    partitions = {
        h: split_periods(rows, validation_start, test_start) for h, rows in prepared.items()
    }
    market_names = sorted(n for n in dataset.rows[0].features if n.startswith("market_"))
    news_names = sorted(n for n in dataset.rows[0].features if n.startswith("news_"))
    # Presence requires a snapshot (count), not sentiment: no-news snapshots are valid.
    coverage = [
        sum(any(r.features.get(n) is not None for n in news_names) for r in group) / len(group)
        for group in partitions[1]
    ]
    news_eligible = bool(news_names) and all(x >= 0.95 for x in coverage)
    groups = {"market_only": market_names}
    if news_eligible:
        groups["market_news"] = market_names + news_names
    for horizon in HORIZONS:
        train, stopping, validation, test = partitions[horizon]
        held_windows = execution.get(horizon)

        def evaluate(
            rows: Sequence[DatasetRow],
            predictions: Sequence[float],
            edge: float,
            cost_model: Costs = configured_costs,
            windows: dict[datetime, ExecutionWindow] | None = held_windows,
        ) -> dict[str, float | int]:
            if windows is not None:
                return simulate(rows, predictions, edge, cost_model, windows)
            return policy(rows, predictions, edge, cost_model)

        for group, names in groups.items():
            parameters: dict[str, Any] = {}
            tuning: dict[str, Any] = {"trials": 0}
            if optuna_trials:
                from ai_trainer.training.tuning.chronological import tune

                parameters, tuning = tune(
                    (*train, *stopping),
                    names,
                    optuna_trials,
                    output / "optuna.db",
                    f"{group}_{horizon}h",
                )
            model = XGBoostRegressorAdapter(parameters)
            model.fit(
                _matrix(train, names),
                np.asarray([r.target for r in train]),
                _matrix(stopping, names),
                np.asarray([r.target for r in stopping]),
            )
            validation_predictions = model.predict(_matrix(validation, names)).tolist()
            # A small predeclared grid avoids a threshold per observation.
            options = [
                (edge, evaluate(validation, validation_predictions, edge))
                for edge in (0.0, 0.0025, 0.005, 0.01)
            ]
            edge, selection = max(options, key=lambda item: _score(item[1]))
            stress = evaluate(
                validation,
                validation_predictions,
                edge,
                Costs(costs.fee_per_side, costs.spread_slippage_per_side * 2),
            )
            path = output / f"{group}_{horizon}h.json"
            model.save(str(path))
            predictions = model.predict(_matrix(test, names))
            candidate = {
                "id": path.stem,
                "horizon_hours": horizon,
                "features": names,
                "minimum_net_edge": edge,
                "entry_delay_hours": 1 if candles is not None else 0,
                "tuning": tuning,
                "diagnostics": {
                    "validation": diagnostics(
                        validation_predictions,
                        [float(r.target) for r in validation if r.target is not None],
                        costs,
                    ),
                    "test": diagnostics(
                        predictions.tolist(),
                        [float(r.target) for r in test if r.target is not None],
                        costs,
                    ),
                },
                "validation": selection,
                "validation_stress": stress,
                "test": evaluate(test, predictions.tolist(), edge),
                "test_mae": float(np.mean(np.abs(predictions - [r.target for r in test]))),
                "baseline_always_long": evaluate(test, [1.0] * len(test), 0),
                "baseline_cash": evaluate(test, [0.0] * len(test), 0),
                "model_path": str(path),
                "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "parameters": model.parameters,
            }
            candidates.append(candidate)
            if candles is not None:
                candidate["baseline_buy_hold"] = buy_and_hold(
                    [
                        c
                        for c in candles
                        if execution[horizon][test[0].timestamp].entry_at
                        <= c.timestamp
                        <= execution[horizon][test[-1].timestamp].exit_at
                    ],
                    costs,
                )
            candidate["rejection_reasons"] = (
                (["fewer_than_10_validation_trades"] if selection["trades"] < 10 else [])
                + (["net_return_does_not_cover_drawdown"] if _score(selection) <= 0 else [])
                + (["nonpositive_cost_stress_return"] if stress["net_return"] <= 0 else [])
            )
            np.savez_compressed(
                output / f"{path.stem}_predictions.npz",
                timestamps=[r.timestamp.isoformat() for r in test],
                predictions=predictions,
                actual=np.asarray([r.target for r in test], dtype=float),
                validation_predictions=np.asarray(validation_predictions),
                validation_actual=np.asarray([r.target for r in validation], dtype=float),
            )
    # No test metric is consulted here, including for horizon/news selection.
    eligible = [
        c
        for c in candidates
        if _score(c["validation"]) > 0 and c["validation_stress"]["net_return"] > 0
    ]
    selected = max(eligible, key=lambda c: _score(c["validation"]), default=None)
    report: dict[str, Any] = {
        "kind": "EXPLORATORY_PAPER_RESEARCH",
        "execution_version": "delayed_ohlc_v2" if candles is not None else "endpoint_v1",
        "market": dataset.metadata.market,
        "data_start": dataset.metadata.start_time.isoformat(),
        "data_end": dataset.metadata.end_time.isoformat(),
        "dataset_fingerprint": dataset.metadata.fingerprint,
        "costs": asdict(costs),
        "validation_start": validation_start.isoformat(),
        "test_start": test_start.isoformat(),
        "rows_per_partition": [len(g) for g in partitions[1]],
        "news_coverage_per_partition": coverage,
        "news_comparison": (
            "same timestamps as market_only"
            if news_eligible
            else "SKIPPED_INSUFFICIENT_NEWS_COVERAGE"
        ),
        "selected_candidate": selected["id"] if selected else None,
        "bot_action": "REVIEW_FOR_PAPER" if selected else "HOLD",
        "limitations": [
            "OHLC risk is conservative: high-before-low bound; no depth or partial fills"
            if candles is not None
            else "Endpoint execution; no intrabar drawdown",
            "Spot long/hold only; no margin or staking simulation",
            "No calibrated probabilities; predicted returns are estimates",
            "Selection is exploratory; requires prospective paper validation",
        ],
        "candidates": candidates,
        "news_net_return_deltas": {
            str(horizon): {
                period: next(c for c in candidates if c["id"] == f"market_news_{horizon}h")[period][
                    "net_return"
                ]
                - next(c for c in candidates if c["id"] == f"market_only_{horizon}h")[period][
                    "net_return"
                ]
                for period in ("validation", "test")
            }
            for horizon in HORIZONS
            if news_eligible
        },
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    return report


def bot_signal(
    candidate: dict[str, Any],
    features: dict[str, float | None],
    costs: Costs,
) -> dict[str, Any]:
    """Inference on completed decision-safe features; fail closed on missing inputs."""
    names = candidate["features"]
    if any((value := features.get(name)) is None or not math.isfinite(value) for name in names):
        return {"action": "HOLD", "reason": "missing_or_invalid_features"}
    from xgboost import XGBRegressor

    path = Path(candidate["model_path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != candidate["model_sha256"]:
        raise ValueError("model checksum mismatch")
    model = XGBRegressor()
    model.load_model(path)
    prediction = float(model.predict(np.asarray([[features[n] for n in names]]))[0])
    net = costs.net(prediction)
    return {
        "action": "BUY" if net > candidate["minimum_net_edge"] else "HOLD",
        "predicted_gross_return": prediction,
        "estimated_net_return": net,
        "horizon_hours": candidate["horizon_hours"],
        "position_fraction": 0.1,
        "requires_no_open_position": True,
    }
