"""Composition root for a public-data historical baseline comparison."""

import argparse
import asyncio
import subprocess
from decimal import Decimal

from ai_trainer.application.services import HistoricalExperimentRunner
from ai_trainer.bots.baselines import BuyAndHoldBot, MovingAverageBot, RandomBot
from paper_trading import PaperTradingSession
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from paper_trading.infrastructure.configuration import get_settings
from paper_trading.infrastructure.logging import configure_logging
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
    runner = HistoricalExperimentRunner(
        bots,
        lambda: PaperTradingSession(starting_balance, fee_rate, slippage),
    )
    result = runner.run(
        candles,
        starting_balance=starting_balance,
        fee_rate=fee_rate,
        slippage_rate=slippage,
        random_seed=args.seed,
        bot_configuration={
            "RandomBot": {"seed": args.seed, "buy_value": "100"},
            "BuyAndHoldBot": {"buy_value": "1000"},
            "MovingAverageBot": {"short": 3, "long": 5, "buy_value": "1000"},
        },
        git_commit=_git_commit(),
    )
    print(result.table())


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
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
