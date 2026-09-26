"""Unified data-operations process and explicit maintenance commands."""

import argparse
import asyncio
import json
import logging
import signal
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from data_collector.infrastructure.configuration import get_data_collector_settings
from data_collector.infrastructure.persistence import (
    SqlAlchemyNewsRepository,
    SqlAlchemySocialRepository,
)
from data_collector.infrastructure.persistence.session import data_collector_session_factory
from data_operations.application.backfill import MarketBackfillService
from data_operations.application.gaps import INTERVALS
from data_operations.application.orchestrator import DataOperationsRunner
from data_operations.application.reactions import ReactionMaturityCoordinator
from data_operations.application.readiness import ReadinessQueryService
from data_operations.domain.entities import (
    CollectorHealthObservation,
    CoverageLimitation,
    HealthStatus,
)
from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
from data_operations.infrastructure.session import operations_session_factory
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from shared.contracts import MarketSymbol


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


async def _market_once(
    repository: SqlAlchemyOperationsRepository,
    adapter: BitvavoMarketDataAdapter,
    market: str,
    interval: str,
) -> int:
    candles = await adapter.get_candles(MarketSymbol(market), interval, limit=2)
    now = datetime.now(UTC)
    return await repository.save_candles(
        [c for c in candles if c.timestamp + INTERVALS[interval] <= now]
    )


async def run_public(once: bool = False) -> int:
    from data_operations.application.public_news import public_news_once

    repository = SqlAlchemyOperationsRepository(operations_session_factory)
    news = SqlAlchemyNewsRepository(data_collector_session_factory)
    settings = get_data_collector_settings()
    async with BitvavoMarketDataAdapter() as adapter:

        async def markets() -> int:
            stored = 0
            for market in ("BTC-EUR", "ETH-EUR", "SOL-EUR"):
                for interval in ("1m", "1h"):
                    stored += await _market_once(repository, adapter, market, interval)
            return stored

        async def collect_news() -> int:
            return await public_news_once(repository, news, settings.news_poll_seconds)

        if once:
            await markets()
            try:
                count = await collect_news()
            except Exception:
                await repository.save_health(
                    CollectorHealthObservation(
                        "news",
                        datetime.now(UTC),
                        HealthStatus.OFFLINE,
                        error_category="public_cycle_failed",
                    )
                )
                raise
            await repository.save_health(
                CollectorHealthObservation(
                    "news", datetime.now(UTC), HealthStatus.HEALTHY, events_received=count
                )
            )
            return 0
        await DataOperationsRunner(
            repository,
            {
                "market": (markets, float(settings.market_poll_seconds)),
                "news": (collect_news, float(settings.news_poll_seconds)),
            },
        ).run()
    return 0


async def run_operations() -> int:
    from data_collector.interfaces.cli.main import (
        analyze_news,
        analyze_social_command,
        collect_once,
        social_once,
        update_market_reactions,
        update_social_reactions,
    )

    settings = get_data_collector_settings()
    repository = SqlAlchemyOperationsRepository(operations_session_factory)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            try:
                loop.add_signal_handler(getattr(signal, name), stop.set)
            except NotImplementedError:
                pass
    adapter = BitvavoMarketDataAdapter()
    started = datetime.now(UTC)
    await repository.save_coverage_limitation(
        CoverageLimitation(
            "news",
            started,
            started,
            "RSS sources do not guarantee historical archives; earlier coverage is unknown.",
            started,
        )
    )
    await repository.save_coverage_limitation(
        CoverageLimitation(
            "social",
            started,
            started,
            "History is limited by official provider access; earlier coverage is unknown.",
            started,
        )
    )
    news_repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    social_repository = SqlAlchemySocialRepository(data_collector_session_factory)

    async def intelligence() -> int:
        return await analyze_news(500) + await analyze_social_command(500)

    async def reactions() -> int:
        created = await ReactionMaturityCoordinator(
            repository, news_repository, social_repository
        ).update(datetime.now(UTC), 500)
        return created + await update_market_reactions(500) + await update_social_reactions(500)

    operations = {
        "market": (
            lambda: _market_once(repository, adapter, "BTC-EUR", "1m"),
            float(settings.market_poll_seconds),
        ),
        "news": (collect_once, float(settings.news_poll_seconds)),
        "intelligence": (intelligence, float(settings.intelligence_poll_seconds)),
        "reactions": (reactions, float(settings.reaction_poll_seconds)),
    }
    if settings.x_api_bearer_token:
        operations["social"] = (social_once, float(settings.social_poll_seconds))
    else:
        await repository.save_health(
            CollectorHealthObservation(
                "social",
                datetime.now(UTC),
                HealthStatus.MISCONFIGURED,
                error_category="missing_credentials",
            )
        )
    try:
        await DataOperationsRunner(repository, operations).run(stop)
    finally:
        await adapter.aclose()
    return 0


async def market_command(args: argparse.Namespace, repair: bool = False) -> int:
    repository = SqlAlchemyOperationsRepository(operations_session_factory)
    async with BitvavoMarketDataAdapter() as adapter:
        service = MarketBackfillService(repository, adapter)
        inserted = await (
            service.repair(args.market, args.interval, _time(args.start), _time(args.end))
            if repair
            else service.backfill(args.market, args.interval, _time(args.start), _time(args.end))
        )
    print(json.dumps({"inserted": inserted, "repair": repair}))
    return 0


async def readiness_command(args: argparse.Namespace) -> int:
    repository = SqlAlchemyOperationsRepository(operations_session_factory)
    start, end = _time(args.start), _time(args.end)
    report = await ReadinessQueryService(repository).report(args.market, args.interval, start, end)
    print(
        json.dumps(
            {
                "market_coverage": report.market_coverage,
                "news_operational_coverage": report.news_operational_coverage,
                "social_operational_coverage": report.social_operational_coverage,
                "groups": [
                    {"name": x.feature_group, "ready": x.ready, "reasons": x.reasons}
                    for x in report.groups
                ],
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PaperTradeAiTrainer research data operations")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run")
    public = commands.add_parser("run-public", help="RSS and market data only; no X/AI calls")
    public.add_argument("--once", action="store_true")
    for name in ("backfill-market", "repair-market-gaps", "readiness"):
        item = commands.add_parser(name)
        item.add_argument("--market", default="BTC-EUR")
        item.add_argument("--interval", default="1h", choices=tuple(INTERVALS))
        item.add_argument("--start", required=True)
        item.add_argument("--end", required=True)
    args = parser.parse_args(argv)
    _configure_logging()
    if args.command == "run-public":
        return asyncio.run(run_public(args.once))
    if args.command == "run":
        return asyncio.run(run_operations())
    if args.command == "readiness":
        return asyncio.run(readiness_command(args))
    return asyncio.run(market_command(args, args.command == "repair-market-gaps"))


def _configure_logging() -> None:
    log_directory = Path("logs")
    log_directory.mkdir(exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    rotating = RotatingFileHandler(
        log_directory / "data-operations.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    rotating.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=(console, rotating))
