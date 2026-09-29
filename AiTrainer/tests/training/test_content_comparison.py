import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trainer.application.services.event_reactions import ContentEvent
from ai_trainer.infrastructure.models.content_shadow import ShadowJournal
from ai_trainer.training.supervised.content_comparison import (
    fit_linear,
    observations,
    predict,
    run_comparison,
)
from shared.contracts import Candle, MarketSymbol

START = datetime(2025, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)


def inputs(count=180):
    candles = []
    for i in range(count):
        price = Decimal(100 + i % 9)
        candles.append(
            Candle(
                MarketSymbol("ETH-EUR"),
                "1h",
                START + i * HOUR,
                price,
                price + 2,
                price - 2,
                price + 1,
                Decimal(10 + i % 3),
            )
        )
    events = [
        ContentEvent(
            str(i),
            "news",
            "test",
            f"ETH announcement topic{i}",
            START + i * HOUR,
            START + i * HOUR,
            START + i * HOUR,
            ("ETH",),
        )
        for i in range(25, count - 2, 2)
    ]
    return events, candles


def test_point_in_time_aggregation_ignores_future_content_prices_and_deduplicates():
    events, candles = inputs()
    decision = events[0].available_at
    row = observations(events, candles, "ETH-EUR", [decision])[0]
    duplicate = replace(events[0], event_id="copy")
    later = replace(
        events[0], event_id="future", text="SECRET FUTURE", processed_at=decision + HOUR
    )
    candles[26] = replace(candles[26], high=Decimal(100000))
    checked = observations([*events, duplicate, later], candles, "ETH-EUR", [decision])[0]
    assert checked["text"] == row["text"]
    assert checked["numeric"] == row["numeric"]
    assert "future" not in checked["event_ids"]
    assert not observations(events, candles[10:], "ETH-EUR", [decision])


def test_training_serialization_uses_training_vocabulary_only(tmp_path):
    rows = [
        {
            "numeric": [float(i)] * 7,
            "text": f"training token{i}",
            "target": {"return_fraction": i * 0.01},
        }
        for i in range(10)
    ]
    model = fit_linear(rows, True, 1.0)
    assert "futureonly" not in model["vocabulary"]
    sample = {"numeric": [3.0] * 7, "text": "futureonly"}
    original = predict(model, [sample])
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model), encoding="utf-8")
    assert predict(json.loads(path.read_text()), [sample]) == pytest.approx(original)


def test_full_comparison_same_samples_purged_labels_and_test_not_selecting(tmp_path):
    events, candles = inputs()
    validation, test = START + 100 * HOUR, START + 140 * HOUR
    output = tmp_path / "first"
    report = run_comparison(
        events, candles, "ETH-EUR", START + 180 * HOUR, output, validation, test
    )
    models = report["horizons"]["1h"]["models"]
    assert models["market"]["test"]["samples"] == models["market_text"]["test"]["samples"]
    assert report["horizons"]["30d"]["status"] == "INSUFFICIENT_DATA"
    first = json.loads((output / "market_text_1h.json").read_text())
    assert datetime.fromisoformat(first["training_end"]) < validation
    assert datetime.fromisoformat(first["selection_end"]) < test
    changed = [
        replace(c, open=c.open * 2, close=c.close * 2, high=c.high * 2, low=c.low * 2)
        if c.timestamp >= test
        else c
        for c in candles
    ]
    second_output = tmp_path / "changed"
    run_comparison(events, changed, "ETH-EUR", START + 180 * HOUR, second_output, validation, test)
    second = json.loads((second_output / "market_text_1h.json").read_text())
    assert first["coefficient"] == second["coefficient"]
    assert first["alpha"] == second["alpha"]
    assert first["vocabulary"] == second["vocabulary"]


def test_forward_journal_rejects_backdating_survives_restart_and_settles_once(tmp_path):
    events, candles = inputs()
    decision = events[-1].available_at
    row = observations(events, candles, "ETH-EUR", [decision])[0]
    fitting = [{**row, "target": {"return_fraction": 0.01}} for _ in range(3)]
    model = fit_linear(fitting, True, 1.0)
    model.update(market="ETH-EUR", horizon_hours=1, frozen_at=(decision - HOUR).isoformat())
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model))
    journal_path = tmp_path / "journal.db"
    journal = ShadowJournal(journal_path)
    assert journal.record(path, row, decision + timedelta(seconds=1))
    assert not ShadowJournal(journal_path).record(path, row, decision + timedelta(seconds=2))
    assert journal.settle(candles, decision + HOUR) == 0
    assert journal.settle(candles, START + 180 * HOUR) == 1
    assert journal.settle(candles, START + 180 * HOUR) == 0
    assert journal.summary()["predictions"] == journal.summary()["matured"] == 1
    with pytest.raises(ValueError, match="forward"):
        journal.record(path, row, decision + HOUR)
    model["frozen_at"] = (decision + HOUR).isoformat()
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError, match="forward"):
        journal.record(path, row, decision)
