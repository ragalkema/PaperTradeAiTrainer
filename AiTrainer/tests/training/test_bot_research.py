import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest
from ai_trainer.application.services.dataset import UnifiedDatasetBuilder
from ai_trainer.application.services.market_features import market_feature_rows, market_features
from ai_trainer.domain.entities import DatasetConfiguration, DatasetRow
from ai_trainer.infrastructure.models.paper_signal import PaperSignalPredictor
from ai_trainer.training.supervised.bot_research import (
    Costs,
    bot_signal,
    horizon_rows,
    policy,
    run_research,
    split_periods,
)
from data_collector.domain.entities import NewsFeatureSnapshot
from shared.contracts import Candle, MarketSymbol


def candles(count: int = 750) -> tuple[Candle, ...]:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            MarketSymbol("BTC-EUR"),
            "1h",
            start + timedelta(hours=i),
            Decimal(100 + i % 13),
            Decimal(115),
            Decimal(95),
            Decimal(101 + i % 11),
            Decimal(10 + i % 5),
        )
        for i in range(count)
    )


def dataset():
    values = candles()
    return UnifiedDatasetBuilder().build(
        values,
        DatasetConfiguration(
            "BTC-EUR", "1h", values[0].timestamp, values[-1].timestamp + timedelta(hours=1)
        ),
    )


def test_fast_features_match_reference_and_ignore_future() -> None:
    values = candles(90)
    fast = market_feature_rows(values)
    for i in range(len(values)):
        assert fast[i] == pytest.approx(market_features(values, i))
    assert market_feature_rows(values[:60]) == fast[:60]


def test_news_availability_and_content_fingerprint() -> None:
    values = candles(60)
    stamp = values[30].timestamp + timedelta(hours=1)
    config = DatasetConfiguration(
        "BTC-EUR", "1h", values[0].timestamp, values[-1].timestamp + timedelta(hours=1)
    )
    snapshot = NewsFeatureSnapshot(
        "BTC-EUR",
        stamp,
        stamp,
        "test",
        ("test",),
        (60,),
        0,
        1,
        1,
        Decimal("0.8"),
        None,
        Decimal("0.1"),
        Decimal("0.1"),
        Decimal("0.1"),
        Decimal("0.5"),
        Decimal("0.5"),
        Decimal("0.8"),
        0,
    )
    builder = UnifiedDatasetBuilder()
    first = builder.build(values, config, news={stamp: snapshot})
    changed = builder.build(values, config, news={stamp: replace(snapshot, news_count_1h=2)})
    assert first.metadata.fingerprint != changed.metadata.fingerprint
    with pytest.raises(ValueError, match="after decision"):
        builder.build(
            values,
            config,
            news={stamp: replace(snapshot, generated_at=stamp + timedelta(seconds=1))},
        )
    with pytest.raises(ValueError, match="mismatch"):
        builder.build(values, config, news={stamp: replace(snapshot, market="ETH-EUR")})


def test_five_targets_match_prices_and_reject_gap_windows() -> None:
    source = dataset()
    prepared = horizon_rows(source)
    assert len({tuple(r.timestamp for r in rows) for rows in prepared.values()}) == 1
    prices = {c.timestamp + timedelta(hours=1): float(c.close) for c in candles()}
    for rows in prepared.values():
        for row in rows:
            assert row.target == pytest.approx(prices[row.target_at] / prices[row.timestamp] - 1)
    gap = source.rows[100].timestamp
    broken = horizon_rows(replace(source, rows=source.rows[:100] + source.rows[101:]))
    assert all(
        not r.timestamp - timedelta(hours=24) <= gap < r.timestamp + timedelta(hours=24)
        for r in broken[24]
    )


def test_policy_charges_both_sides_and_does_not_reuse_capital() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = tuple(
        DatasetRow(start + timedelta(hours=i), {}, {}, 0.0, start + timedelta(hours=i + 6))
        for i in range(12)
    )
    costs = Costs(0.0025, 0.001)
    result = policy(rows, [0.1] * 12, 0, costs)
    assert result["trades"] == 2
    assert result["net_return"] == pytest.approx((1 + 0.1 * costs.net(0)) ** 2 - 1)
    assert policy(rows, [0.001] * 12, 0, costs)["trades"] == 0


def test_partitions_purge_all_horizons() -> None:
    source = dataset()
    start = source.rows[0].timestamp
    for rows in horizon_rows(source).values():
        groups = split_periods(rows, start + timedelta(hours=450), start + timedelta(hours=600))
        for left, right in pairwise(groups):
            assert left[-1].timestamp + timedelta(hours=24) < right[0].timestamp


def test_real_training_saves_models_skips_absent_news_and_keeps_test_out_of_selection(
    tmp_path: Path,
) -> None:
    source = dataset()
    start = source.rows[0].timestamp
    validation, test = start + timedelta(hours=450), start + timedelta(hours=600)
    first = run_research(source, validation, test, tmp_path / "first")
    changed = replace(
        source,
        rows=tuple(replace(r, target=0.05) if r.timestamp >= test else r for r in source.rows),
    )
    second = run_research(changed, validation, test, tmp_path / "second")
    assert first["selected_candidate"] == second["selected_candidate"]
    assert first["news_comparison"] == "SKIPPED_INSUFFICIENT_NEWS_COVERAGE"
    assert len(first["candidates"]) == 5
    for a, b in zip(first["candidates"], second["candidates"], strict=True):
        assert a["model_sha256"] == b["model_sha256"]
        assert a["minimum_net_edge"] == b["minimum_net_edge"]
        assert a["validation"] == b["validation"]
        assert Path(a["model_path"]).exists()
        assert bot_signal(a, {}, Costs())["action"] == "HOLD"
    assert any(
        a["test_mae"] != b["test_mae"]
        for a, b in zip(first["candidates"], second["candidates"], strict=True)
    )


def test_news_comparison_and_persistent_bot_inference(tmp_path: Path) -> None:
    source = dataset()
    rows = tuple(
        replace(
            r,
            features={**r.features, "news_count_1h": float(i % 3)},
            feature_observed_at={**r.feature_observed_at, "news_count_1h": r.timestamp},
        )
        for i, r in enumerate(source.rows)
    )
    source = replace(source, rows=rows)
    start = rows[0].timestamp
    folder = tmp_path / "paired"
    report = run_research(
        source, start + timedelta(hours=450), start + timedelta(hours=600), folder
    )
    assert report["news_comparison"] == "same timestamps as market_only"
    assert len(report["candidates"]) == 10
    assert report["news_coverage_per_partition"] == [1, 1, 1, 1]
    # Force a candidate ONLY in this fixture to exercise loading/inference guards.
    report["selected_candidate"] = report["candidates"][0]["id"]
    path = folder / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    predictor = PaperSignalPredictor(path)
    row = rows[500]
    assert "estimated_net_return" in predictor.predict(row, row.timestamp)
    assert predictor.predict(row, row.timestamp, position_open=True)["action"] == "HOLD"
    assert predictor.predict(row, row.timestamp + timedelta(hours=2))["action"] == "HOLD"
    unsafe = replace(
        row, feature_observed_at={k: row.timestamp + timedelta(seconds=1) for k in row.features}
    )
    assert predictor.predict(unsafe, row.timestamp)["action"] == "HOLD"
    report["selected_candidate"] = None
    path.write_text(json.dumps(report), encoding="utf-8")
    assert (
        PaperSignalPredictor(path).predict(row, row.timestamp)["reason"]
        == "no_validation_candidate"
    )
