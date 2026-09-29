"""Reproducible local JSONL export of content and seven price-reaction horizons."""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared.contracts import Candle

from ai_trainer.application.services.event_reactions import (
    HORIZONS,
    VERSION,
    assign_splits,
    build_reaction_rows,
    trainable_samples,
)


def register(commands: Any) -> None:
    parser = commands.add_parser("build-event-reactions", help="Label local news/X price reactions")
    parser.add_argument("--start", required=True, help="Inclusive publication time, ISO UTC")
    parser.add_argument("--end", help="Exclusive publication time; defaults to as-of")
    parser.add_argument("--as-of", help="Observation cutoff; defaults to now")
    parser.add_argument("--markets", nargs="+", default=["BTC-EUR", "ETH-EUR", "SOL-EUR"])
    parser.add_argument("--validation-start")
    parser.add_argument("--test-start")
    parser.add_argument("--output", type=Path)


def utc(value: str) -> datetime:
    time = datetime.fromisoformat(value)
    return time.replace(tzinfo=UTC) if time.tzinfo is None else time.astimezone(UTC)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(
                json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
            )
    return sha256(path.read_bytes()).hexdigest()


async def run(args: argparse.Namespace) -> int:
    from data_collector.infrastructure.persistence.session import data_collector_session_factory
    from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
    from data_operations.infrastructure.session import operations_session_factory

    from ai_trainer.infrastructure.datasets.content_events import read_content_events

    now = datetime.now(UTC)
    cutoff = utc(args.as_of) if args.as_of else now
    start, end = utc(args.start), utc(args.end) if args.end else cutoff
    if not start < end <= cutoff <= now:
        raise ValueError("require start < end <= as-of <= now")
    if bool(args.validation_start) != bool(args.test_start):
        raise ValueError("provide both validation-start and test-start, or neither")
    validation = utc(args.validation_start) if args.validation_start else None
    test = utc(args.test_start) if args.test_start else None
    if validation and test and not start < validation < test < cutoff:
        raise ValueError("require start < validation-start < test-start < as-of")
    events = await read_content_events(data_collector_session_factory, start, end, cutoff)
    repository = SqlAlchemyOperationsRepository(operations_session_factory)
    candles: list[Candle] = []
    for market in sorted(set(args.markets)):
        candles.extend(
            await repository.candles(
                market,
                "1h",
                start.replace(minute=0, second=0, microsecond=0),
                cutoff,
            )
        )
    rows = build_reaction_rows(events, candles, args.markets, cutoff)
    if validation and test:
        assign_splits(rows, validation, test)
    output = args.output or Path("experiments/results") / f"event-reactions-{uuid4()}"
    output.mkdir(parents=True, exist_ok=False)
    checksums = {"events.jsonl": write_jsonl(output / "events.jsonl", rows)}
    counts = {}
    for horizon in HORIZONS:
        samples = trainable_samples(rows, horizon)
        name = f"training_{horizon}.jsonl"
        checksums[name] = write_jsonl(output / name, samples)
        counts[horizon] = {
            "status": dict(Counter(row["targets"][horizon]["status"] for row in rows)),
            "exported_samples": len(samples),
            "distinct_price_windows": len(
                {
                    (
                        row["metadata"]["market"],
                        row["target"]["entry_at"],
                        row["target"]["target_at"],
                    )
                    for row in samples
                }
            ),
            "classes": dict(Counter(row["target"]["class"] for row in samples)),
            "splits": dict(Counter(row["target"].get("split", "unassigned") for row in samples)),
        }
    manifest = {
        "version": VERSION,
        "as_of": cutoff.isoformat(),
        "publication_start": start.isoformat(),
        "publication_end": end.isoformat(),
        "markets": sorted(set(args.markets)),
        "horizons_hours": HORIZONS,
        "source_events": {
            kind: sum(event.source_type == kind for event in events) for kind in ("news", "x")
        },
        "events_with_market_rows": len(
            {(r["features"]["source_type"], r["metadata"]["event_id"]) for r in rows}
        ),
        "event_market_rows": len(rows),
        "horizons": counts,
        "sha256": checksums,
        "validation_start": validation.isoformat() if validation else None,
        "test_start": test.isoformat() if test else None,
        "feature_allowlist": ["text", "source", "source_type", "asset"],
        "limitations": [
            "Observed association, not causation; long horizons have many confounding events.",
            "Hourly resolution; entry at strictly next opening, not exact publication price.",
            "Gross returns, no execution costs; these are labels, not simulated strategy P&L.",
            "Pending and missing candles are not zero returns or negative examples.",
            "News text is stored title/summary, not necessarily the full article.",
            "No final engagement or retrospective intelligence included as features.",
            "Content/asset mapping assumed available at processed_at; no edit history.",
            "Market candles used as retrospective outcomes, not reconstructed ingestion history.",
            "Without split flags, the trainer must handle chronological purging/group isolation.",
            "Overlapping event windows are not independent; no random row split.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), **manifest}, indent=2))
    return 0
