"""Local content research and read-only prospective logging commands."""

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from shared.contracts import Candle

from ai_trainer.interfaces.cli.reaction_dataset import utc


def register(commands: Any) -> None:
    compare = commands.add_parser("compare-content", help="Matched market vs market+text research")
    compare.add_argument("--market", default="ETH-EUR")
    compare.add_argument("--start", default="2026-09-18")
    compare.add_argument("--as-of")
    compare.add_argument("--validation-start")
    compare.add_argument("--test-start")
    compare.add_argument("--output", type=Path)
    shadow = commands.add_parser("shadow-content", help="Log frozen predictions; no orders")
    shadow.add_argument("--models", nargs="+", type=Path, required=True)
    shadow.add_argument(
        "--journal", type=Path, default=Path("experiments/results/content-shadow.db")
    )
    shadow.add_argument("--watch", action="store_true", help="Repeat every five minutes")


async def load_local(market: str, start: datetime, cutoff: datetime) -> tuple[Any, list[Candle]]:
    from data_collector.infrastructure.persistence.session import data_collector_session_factory
    from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
    from data_operations.infrastructure.session import operations_session_factory

    from ai_trainer.infrastructure.datasets.content_events import read_content_events

    events = await read_content_events(data_collector_session_factory, start, cutoff, cutoff)
    candles = await SqlAlchemyOperationsRepository(operations_session_factory).candles(
        market, "1h", start - timedelta(hours=24), cutoff
    )
    return events, list(candles)


async def compare(args: argparse.Namespace) -> int:
    from ai_trainer.training.supervised.content_comparison import run_comparison

    now = datetime.now(UTC)
    cutoff = utc(args.as_of) if args.as_of else now
    start = utc(args.start)
    if not start < cutoff <= now:
        raise ValueError("require start < as-of <= now")
    if bool(args.validation_start) != bool(args.test_start):
        raise ValueError("provide both split boundaries or neither")
    events, candles = await load_local(args.market, start, cutoff)
    output = args.output or Path("experiments/results") / f"content-{args.market}-{uuid4()}"
    report = run_comparison(
        events,
        candles,
        args.market,
        cutoff,
        output,
        utc(args.validation_start) if args.validation_start else None,
        utc(args.test_start) if args.test_start else None,
    )
    print(json.dumps({"output": str(output), **report}, indent=2))
    return 0


async def shadow_once(args: argparse.Namespace) -> None:
    from ai_trainer.infrastructure.models.content_shadow import ShadowJournal
    from ai_trainer.training.supervised.content_comparison import observations

    journal = ShadowJournal(args.journal)
    # Group models by market to read identical observations once for both baselines.
    markets: dict[str, list[Path]] = {}
    for path in args.models:
        model = json.loads(path.read_text(encoding="utf-8"))
        markets.setdefault(model["market"], []).append(path)
    inserted = 0
    skips = []
    for market, paths in markets.items():
        decision = datetime.now(UTC)
        events, candles = await load_local(market, decision - timedelta(days=35), decision)
        journal.settle(candles, decision)
        samples = observations(events, candles, market, [decision])
        if not samples:
            skips.append(f"{market}: no fresh content or incomplete 24h market context")
            continue
        for path in paths:
            try:
                inserted += journal.record(path, samples[0], datetime.now(UTC))
            except ValueError as exc:
                skips.append(f"{market}: {exc}")
    print(
        json.dumps(
            {
                "recorded_at": datetime.now(UTC).isoformat(),
                "inserted": inserted,
                "skips": skips,
                **journal.summary(),
            }
        ),
        flush=True,
    )


async def shadow(args: argparse.Namespace) -> int:
    while True:
        try:
            await shadow_once(args)
        except Exception as exc:
            if not args.watch:
                raise
            # Avoid database credentials or provider payloads in persistent log messages.
            print(
                json.dumps({"error_type": type(exc).__name__, "status": "retry_in_300s"}),
                flush=True,
            )
        if not args.watch:
            return 0
        await asyncio.sleep(300)
