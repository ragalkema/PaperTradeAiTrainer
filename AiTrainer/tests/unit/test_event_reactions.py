from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trainer.application.services.event_reactions import (
    HORIZONS,
    ContentEvent,
    ReactionPrices,
    assign_splits,
    build_reaction_rows,
    movement,
    trainable_samples,
)
from ai_trainer.interfaces.cli.main import _parser
from ai_trainer.interfaces.cli.reaction_dataset import write_jsonl
from shared.contracts import Candle, MarketSymbol

START = datetime(2025, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)


def candles(count=800):
    return [
        Candle(
            MarketSymbol("ETH-EUR"),
            "1h",
            START + i * HOUR,
            Decimal(100 + i),
            Decimal(103 + i),
            Decimal(98 + i),
            Decimal(101 + i),
            Decimal(10),
        )
        for i in range(count)
    ]


def event(**kwargs):
    base = ContentEvent("one", "news", "source", "ETH rises", START, START, START, ("ETH",))
    return replace(base, **kwargs)


def test_seven_horizons_known_prices_and_excursions():
    rows = build_reaction_rows([event(), event()], candles(), ["ETH-EUR"], START + 800 * HOUR)
    assert len(rows) == 1  # idempotent input
    assert set(rows[0]["targets"]) == set(HORIZONS)
    for name, hours in HORIZONS.items():
        target = rows[0]["targets"][name]
        assert target["status"] == "ready"
        assert target["return_fraction"] == pytest.approx(hours / 101)
        assert target["maximum_return_fraction"] == pytest.approx((hours + 2) / 101)
        assert target["minimum_return_fraction"] == pytest.approx(-2 / 101)
        assert target["target_at"] == (START + (hours + 1) * HOUR).isoformat()
    sample = trainable_samples(rows, "30d")[0]
    assert sample["target"]["class"] == "up:20%+"
    assert "publication_reactions_not_features" not in sample
    assert set(sample["features"]) == {"text", "source", "source_type", "asset"}


def test_late_received_post_is_not_backdated_and_missing_market_is_not_assumed():
    late = event(source_type="x", received_at=START + 40 * HOUR, processed_at=START + 42 * HOUR)
    rows = build_reaction_rows([late], candles(), ["BTC-EUR", "ETH-EUR"], START + 800 * HOUR)
    assert len(rows) == 1
    assert rows[0]["targets"]["1h"]["entry_price"] == 143
    assert rows[0]["publication_reactions_not_features"]["1h"]["entry_price"] == 101
    assert rows[0]["metadata"]["availability_delay_seconds"] == 42 * 3600
    assert not build_reaction_rows([late], candles(), ["ETH-EUR"], START + 41 * HOUR)


def test_pending_gaps_and_partial_candles_are_not_training_labels():
    values = candles()
    prices = ReactionPrices(values, START + 10 * HOUR)
    assert prices.measure("ETH-EUR", START, 7 * 24)["status"] == "pending"
    assert prices.measure("ETH-EUR", START, 8)["status"] == "ready"
    assert prices.measure("ETH-EUR", START, 9)["status"] == "pending"
    del values[4]  # Interior gap invalidates even though both endpoints exist.
    rows = build_reaction_rows([event()], values, ["ETH-EUR"], START + 10 * HOUR)
    assert rows[0]["targets"]["6h"]["status"] == "missing_candles"
    assert len(trainable_samples(rows, "1h")) == 1
    assert trainable_samples(rows, "6h") == []
    assert trainable_samples(rows, "30d") == []
    with pytest.raises(ValueError, match="duplicate"):
        ReactionPrices([values[0], values[0]], START + 800 * HOUR)


def test_future_price_mutation_cannot_change_features_or_completed_short_labels():
    values = candles()
    original = build_reaction_rows([event()], values, ["ETH-EUR"], START + 800 * HOUR)[0]
    values[100] = replace(values[100], high=Decimal(9999))
    changed = build_reaction_rows([event()], values, ["ETH-EUR"], START + 800 * HOUR)[0]
    assert original["features"] == changed["features"]
    assert original["targets"]["24h"] == changed["targets"]["24h"]
    assert original["targets"]["7d"] != changed["targets"]["7d"]


def test_boundary_purge_and_story_isolation_across_news_and_x():
    events = [
        event(story_id="story"),
        event(
            event_id="two",
            source_type="x",
            text="ETH update",
            story_id="story",
            published_at=START + 30 * HOUR,
            processed_at=START + 30 * HOUR,
        ),
        event(
            event_id="three",
            text="Different ETH topic",
            published_at=START + 60 * HOUR,
            processed_at=START + 60 * HOUR,
        ),
    ]
    rows = build_reaction_rows(events, candles(), ["ETH-EUR"], START + 800 * HOUR)
    assign_splits(rows, START + 26 * HOUR, START + 50 * HOUR)
    assert rows[0]["targets"]["12h"]["split"] == "train"
    assert rows[0]["targets"]["24h"]["split"] == "purged_boundary"
    assert rows[1]["targets"]["1h"]["split"] == "excluded_repeated_story"
    assert rows[2]["targets"]["30d"]["split"] == "test"
    assert len(trainable_samples(rows, "30d")) == 1


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", "flat:0-2%"),
        ("0.0199", "up:0-2%"),
        ("0.02", "up:2-5%"),
        ("-0.05", "down:5-10%"),
        ("0.1", "up:10-15%"),
        ("-0.15", "down:15-20%"),
        ("0.2", "up:20%+"),
    ],
)
def test_non_overlapping_percentage_classes(value, expected):
    assert movement(Decimal(value))["class"] == expected


def test_cli_and_deterministic_export_without_overwrite(tmp_path):
    args = _parser().parse_args(["build-event-reactions", "--start", "2025-01-01"])
    assert args.markets == ["BTC-EUR", "ETH-EUR", "SOL-EUR"]
    rows = build_reaction_rows([event()], candles(), ["ETH-EUR"], START + 800 * HOUR)
    one = write_jsonl(tmp_path / "one.jsonl", rows)
    two = write_jsonl(tmp_path / "two.jsonl", rows)
    assert one == two
    with pytest.raises(FileExistsError):
        write_jsonl(tmp_path / "one.jsonl", rows)
