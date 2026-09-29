"""Hourly matched market/text baselines with purged chronological evaluation."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, hstack  # type: ignore[import-untyped]
from shared.contracts import Candle
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]
from sklearn.linear_model import Ridge  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from ai_trainer.application.services.event_reactions import ContentEvent, ReactionPrices, next_open
from ai_trainer.application.services.market_features import market_features
from ai_trainer.domain.entities import DatasetRow
from ai_trainer.evaluation.backtesting.candle_execution import (
    buy_and_hold,
    execution_windows,
    simulate,
)
from ai_trainer.training.supervised.bot_research import Costs

HOUR = timedelta(hours=1)
FEATURES = [
    "market_return_1",
    "market_return_3",
    "market_return_6",
    "market_return_12",
    "market_rolling_volatility",
    "market_high_low_range",
    "market_volume_zscore",
]


def observations(
    events: Sequence[ContentEvent],
    candles: Sequence[Candle],
    market: str,
    decisions: Sequence[datetime],
) -> list[dict[str, Any]]:
    """Identical input construction for offline research and order-free forward logging."""
    by_time = {c.timestamp: c for c in candles if str(c.market) == market and c.interval == "1h"}
    relevant = [e for e in events if market.split("-")[0] in e.assets]
    output = []
    for decision in sorted(set(decisions)):
        content = sorted(
            (e for e in relevant if decision - HOUR < e.available_at <= decision),
            key=lambda e: (e.available_at, e.event_id),
        )
        if not content:
            continue
        closed = decision.replace(minute=0, second=0, microsecond=0)
        times = [closed - i * HOUR for i in range(24, 0, -1)]
        if any(t not in by_time for t in times):
            continue
        features = market_features([by_time[t] for t in times], 23)
        unique = {e.content_hash: e for e in content}
        output.append(
            {
                "decision_at": decision.isoformat(),
                "market": market,
                "text": "\n".join(e.text for e in unique.values()),
                "numeric": [features[n] if features[n] is not None else 0.0 for n in FEATURES],
                "groups": sorted({g for e in content for g in (e.content_hash, e.story_id) if g}),
                "event_ids": sorted({e.event_id for e in content}),
                "source_counts": {
                    kind: sum(e.source_type == kind for e in content) for kind in ("news", "x")
                },
            }
        )
    return output


def purged_split(
    rows: list[dict[str, Any]], validation: datetime, test: datetime
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, str] = {}
    result: dict[str, list[dict[str, Any]]] = {k: [] for k in ("train", "validation", "test")}
    for row in sorted(rows, key=lambda r: r["decision_at"]):
        time = datetime.fromisoformat(row["decision_at"])
        split = "train" if time < validation else "validation" if time < test else "test"
        boundary = validation if split == "train" else test if split == "validation" else None
        repeat = any(g in groups and groups[g] != split for g in row["groups"])
        for group in row["groups"]:
            groups.setdefault(group, split)
        if repeat or (
            boundary and datetime.fromisoformat(row["target"]["label_available_at"]) >= boundary
        ):
            continue
        result[split].append(row)
    return result


def matrix(rows: Sequence[dict[str, Any]]) -> Any:
    return np.asarray([r["numeric"] for r in rows], dtype=float)


def fit_linear(rows: Sequence[dict[str, Any]], with_text: bool, alpha: float) -> dict[str, Any]:
    scaler = StandardScaler().fit(matrix(rows))
    numeric = csr_matrix(scaler.transform(matrix(rows)))
    vocabulary: dict[str, int] = {}
    idf: list[float] = []
    if with_text:
        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), sublinear_tf=True)
        text = vectorizer.fit_transform([r["text"] for r in rows])
        vocabulary = {str(k): int(v) for k, v in vectorizer.vocabulary_.items()}
        idf = vectorizer.idf_.tolist()
        numeric = hstack((numeric, text)).tocsr()
    model = Ridge(alpha=alpha, solver="lsqr").fit(
        numeric, [r["target"]["return_fraction"] for r in rows]
    )
    return {
        "schema": "linear_content_v1",
        "features": FEATURES,
        "with_text": with_text,
        "alpha": alpha,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "vocabulary": vocabulary,
        "idf": idf,
        "coefficient": model.coef_.tolist(),
        "intercept": float(model.intercept_),
    }


def predict(model: dict[str, Any], rows: Sequence[dict[str, Any]]) -> list[float]:
    if not rows:
        return []
    numeric = csr_matrix((matrix(rows) - np.asarray(model["mean"])) / np.asarray(model["scale"]))
    if model["with_text"]:
        vectorizer = TfidfVectorizer(
            vocabulary=model["vocabulary"], ngram_range=(1, 2), sublinear_tf=True
        )
        vectorizer.idf_ = np.asarray(model["idf"])
        numeric = hstack((numeric, vectorizer.transform([r["text"] for r in rows]))).tocsr()
    return list(np.asarray(numeric @ np.asarray(model["coefficient"]) + model["intercept"]).ravel())


def evaluate(
    rows: list[dict[str, Any]],
    predictions: list[float],
    candles: Sequence[Candle],
    horizon: int,
    costs: Costs,
) -> dict[str, Any]:
    actual = np.asarray([r["target"]["return_fraction"] for r in rows])
    times = [datetime.fromisoformat(r["decision_at"]) for r in rows]
    dataset = [
        DatasetRow(t, {}, {}, float(y), t + (horizon + 1) * HOUR)
        for t, y in zip(times, actual, strict=True)
    ]
    windows = execution_windows(candles, times, horizon)
    return {
        "samples": len(rows),
        "rmse": float(np.sqrt(np.mean((actual - predictions) ** 2))),
        "zero_return_rmse": float(np.sqrt(np.mean(actual**2))),
        "direction_accuracy": float(np.mean(np.sign(actual) == np.sign(predictions))),
        "paper": simulate(dataset, predictions, 0, costs, windows),
    }


def run_comparison(
    events: Sequence[ContentEvent],
    candles: Sequence[Candle],
    market: str,
    cutoff: datetime,
    output: Path,
    validation: datetime | None = None,
    test: datetime | None = None,
) -> dict[str, Any]:
    from ai_trainer.application.services.event_reactions import HORIZONS

    prices = ReactionPrices(candles, cutoff)
    decisions = [
        e.available_at
        if e.available_at.minute == e.available_at.second == e.available_at.microsecond == 0
        else next_open(e.available_at)
        for e in events
        if e.available_at <= cutoff
    ]
    rows = observations(events, candles, market, [d for d in decisions if d <= cutoff])
    times = sorted({datetime.fromisoformat(r["decision_at"]) for r in rows})
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "market": market,
        "cutoff": cutoff.isoformat(),
        "observation_windows": len(rows),
        "status": "INSUFFICIENT_DATA",
        "horizons": {},
        "costs": {"fee_per_side": 0.0025, "spread_slippage_per_side": 0.001},
        "limitations": [
            "Exploratory event-hour sample, not continuous all-hours performance.",
            "No causal attribution; fixed long/hold policy with 10% allocation.",
            "No orders; small partitions are mechanics checks, not evidence of profit.",
            "No Optuna in this small-data baseline; fixed alpha grid .1, 1, 10.",
        ],
    }
    if len(times) >= 5:
        validation = validation or times[int(len(times) * 0.6)]
        test = test or times[int(len(times) * 0.8)]
        if not times[0] < validation < test <= cutoff:
            raise ValueError("invalid chronological boundaries")
        report.update(validation_start=validation.isoformat(), test_start=test.isoformat())
        for name, hours in HORIZONS.items():
            ready = [
                {
                    **r,
                    "target": prices.measure(
                        market, datetime.fromisoformat(r["decision_at"]), hours
                    ),
                }
                for r in rows
            ]
            ready = [r for r in ready if r["target"]["status"] == "ready"]
            splits = purged_split(ready, validation, test)
            counts = {key: len(value) for key, value in splits.items()}
            result: dict[str, Any] = {"partition_counts": counts, "status": "INSUFFICIENT_DATA"}
            report["horizons"][name] = result
            if counts["train"] < 3 or min(counts["validation"], counts["test"]) < 1:
                continue
            result["status"] = "EXPLORATORY_ONLY"
            result["models"] = {}
            for kind, use_text in (("market", False), ("market_text", True)):
                candidates = [fit_linear(splits["train"], use_text, a) for a in (0.1, 1.0, 10.0)]
                truth = np.asarray([r["target"]["return_fraction"] for r in splits["validation"]])
                model = min(
                    candidates,
                    key=lambda m: float(np.mean((truth - predict(m, splits["validation"])) ** 2)),
                )
                model.update(
                    market=market,
                    horizon_hours=hours,
                    frozen_at=datetime.now(UTC).isoformat(),
                    training_end=max(r["target"]["label_available_at"] for r in splits["train"]),
                    selection_end=max(
                        r["target"]["label_available_at"] for r in splits["validation"]
                    ),
                )
                path = output / f"{kind}_{name}.json"
                path.write_text(json.dumps(model, allow_nan=False), encoding="utf-8")
                metrics = {
                    period: evaluate(
                        splits[period], predict(model, splits[period]), candles, hours, Costs()
                    )
                    for period in ("validation", "test")
                }
                result["models"][kind] = {
                    "alpha": model["alpha"],
                    "model_path": path.name,
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                    **metrics,
                }
                with (output / f"predictions_{kind}_{name}.jsonl").open(
                    "x", encoding="utf-8"
                ) as stream:
                    for row, prediction in zip(
                        splits["test"], predict(model, splits["test"]), strict=True
                    ):
                        stream.write(
                            json.dumps(
                                {
                                    "decision_at": row["decision_at"],
                                    "text": row["text"],
                                    "predicted": prediction,
                                    "actual": row["target"]["return_fraction"],
                                }
                            )
                            + "\n"
                        )
            test_rows = splits["test"]
            result["baselines"] = {
                "cash_net_return": 0,
                "always_long": evaluate(test_rows, [1.0] * len(test_rows), candles, hours, Costs()),
            }
            first = datetime.fromisoformat(test_rows[0]["target"]["entry_at"])
            last = datetime.fromisoformat(test_rows[-1]["target"]["target_at"])
            held = sorted(
                (c for c in candles if first <= c.timestamp <= last), key=lambda c: c.timestamp
            )
            if len(held) == int((last - first) / HOUR) + 1:
                result["baselines"]["buy_and_hold"] = buy_and_hold(held, Costs())
            result["news_test_net_return_delta"] = (
                result["models"]["market_text"]["test"]["paper"]["net_return"]
                - result["models"]["market"]["test"]["paper"]["net_return"]
            )
            report["status"] = "EXPLORATORY_ONLY"
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    return report
