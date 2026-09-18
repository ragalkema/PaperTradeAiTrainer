"""Composition root for a public-data historical baseline comparison."""

import argparse
import asyncio
import subprocess
from decimal import Decimal

from ai_trainer.application.services import HistoricalExperimentRunner
from ai_trainer.bots.baselines import BuyAndHoldBot, MovingAverageBot, RandomBot
from paper_trading import PaperTradingSession
from paper_trading.application.services.experiment_persistence import (
    BotRegistration,
    ExperimentPersistenceService,
    ExperimentRegistration,
)
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from paper_trading.infrastructure.configuration import get_settings
from paper_trading.infrastructure.logging import configure_logging
from paper_trading.infrastructure.persistence import SqlAlchemyResearchRepository
from paper_trading.infrastructure.persistence.session import async_session_factory
from shared.contracts import MarketSymbol


async def run(args: argparse.Namespace) -> None:
    market = MarketSymbol(args.market)
    starting_balance = Decimal(args.starting_balance)
    fee_rate = Decimal(args.fee_rate)
    slippage = Decimal(args.slippage)
    async with BitvavoMarketDataAdapter() as adapter:
        candles = await adapter.get_candles(market, args.interval, limit=args.limit)
    bots = {
        "RandomBot": RandomBot(Decimal("100"), seed=args.seed),
        "BuyAndHoldBot": BuyAndHoldBot(Decimal("1000")),
        "MovingAverageBot": MovingAverageBot(3, 5, Decimal("1000")),
    }
    bot_configuration = {
        "RandomBot": {"seed": args.seed, "buy_value": "100"},
        "BuyAndHoldBot": {"buy_value": "1000"},
        "MovingAverageBot": {"short": 3, "long": 5, "buy_value": "1000"},
    }
    persistence_run = None
    persistence_service = None
    if args.persist:
        persistence_service = ExperimentPersistenceService(
            SqlAlchemyResearchRepository(async_session_factory)
        )
        persistence_run = await persistence_service.start(
            ExperimentRegistration(
                args.name,
                "Historical baseline comparison",
                (market,),
                candles[0].timestamp,
                candles[-1].timestamp,
                starting_balance,
                fee_rate,
                slippage,
                args.seed,
                tuple(
                    BotRegistration(name, type(bot).__name__, "1", bot_configuration[name])
                    for name, bot in bots.items()
                ),
                git_commit=_git_commit(),
            )
        )
    runner = HistoricalExperimentRunner(
        bots,
        lambda: PaperTradingSession(starting_balance, fee_rate, slippage),
        persistence_run.recorder if persistence_run else None,
    )
    result = runner.run(
        candles,
        starting_balance=starting_balance,
        fee_rate=fee_rate,
        slippage_rate=slippage,
        random_seed=args.seed,
        bot_configuration=bot_configuration,
        git_commit=_git_commit(),
    )
    print(result.table())
    if persistence_service and persistence_run:
        await persistence_service.complete(persistence_run)
        print(f"Persisted experiment {persistence_run.experiment_id}")


def _git_commit() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() or None


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser(description="Compare baseline bots on public candles")
    parser.add_argument("market", nargs="?", default="BTC-EUR")
    parser.add_argument("interval", nargs="?", default="1h")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--starting-balance", default="10000")
    parser.add_argument("--fee-rate", default="0.0025")
    parser.add_argument("--slippage", default="0.0005")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--persist", action="store_true", help="Persist after Alembic migration")
    parser.add_argument("--name", default="Baseline comparison")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
