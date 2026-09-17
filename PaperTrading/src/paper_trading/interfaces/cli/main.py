"""Development CLI for public prices and isolated paper sessions."""

import argparse
import asyncio
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from shared.contracts import BotAction, MarketSymbol

from paper_trading.application.services import PaperTradingSession
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter, MarketDataError
from paper_trading.infrastructure.configuration import get_settings
from paper_trading.infrastructure.logging import configure_logging
from paper_trading.infrastructure.persistence import (
    AppendOnlyRawMarketStore,
    JsonlCandleRepository,
)

BANNER = """PaperTradeAiTrainer
-------------------
PAPER TRADING ONLY
NO REAL ORDERS ARE EXECUTED
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public market data and paper-only trading")
    subcommands = parser.add_subparsers(dest="command")
    price = subcommands.add_parser("price", help="retrieve one public market price")
    price.add_argument("market", nargs="?", default="BTC-EUR")
    candles = subcommands.add_parser("candles", help="retrieve and persist public candles")
    candles.add_argument("market", nargs="?", default="BTC-EUR")
    candles.add_argument("interval", nargs="?", default="1h")
    candles.add_argument("--limit", type=int, default=100)
    candles.add_argument("--start", type=datetime.fromisoformat)
    candles.add_argument("--end", type=datetime.fromisoformat)
    subcommands.add_parser("trade", help="start an interactive paper-trading session")
    return parser


async def run_price(market_value: str) -> None:
    market = MarketSymbol(market_value)
    store = AppendOnlyRawMarketStore(Path("data/raw/market"))
    async with BitvavoMarketDataAdapter(raw_store=store) as adapter:
        state = await adapter.get_current_state(market)
    print(f"{state.market} last={state.current_price} bid={state.bid} ask={state.ask}")


async def run_candles(args: argparse.Namespace) -> None:
    market = MarketSymbol(args.market)
    raw_store = AppendOnlyRawMarketStore(Path("data/raw/market"))
    repository = JsonlCandleRepository(Path("data/normalized/market/candles.jsonl"))
    async with BitvavoMarketDataAdapter(raw_store=raw_store) as adapter:
        candles = await adapter.get_candles(
            market,
            args.interval,
            start=args.start,
            end=args.end,
            limit=args.limit,
        )
    inserted = await repository.save(list(candles))
    print(f"Retrieved {len(candles)} candles; persisted {inserted} new records.")


async def run_interactive() -> None:
    settings = get_settings()
    session = PaperTradingSession(
        settings.paper_starting_balance,
        settings.paper_fee_rate,
        settings.paper_slippage_rate,
    )
    store = AppendOnlyRawMarketStore(Path("data/raw/market"))
    adapter = BitvavoMarketDataAdapter(raw_store=store)
    print(BANNER)
    try:
        while True:
            command = (await asyncio.to_thread(input, "paper> ")).strip().split()
            if not command:
                continue
            verb = command[0].lower()
            if verb in {"quit", "exit"}:
                break
            try:
                if verb == "price" and len(command) == 2:
                    state = await adapter.get_current_state(MarketSymbol(command[1]))
                    session.update_market(state)
                    print(
                        f"{state.market}: bid={state.bid} ask={state.ask} "
                        f"last={state.current_price}"
                    )
                elif verb == "buy" and len(command) == 3:
                    market = MarketSymbol(command[1])
                    session.update_market(await adapter.get_current_state(market))
                    print(session.execute(BotAction.buy(market, Decimal(command[2]))))
                elif verb == "sell" and len(command) == 3:
                    market = MarketSymbol(command[1])
                    session.update_market(await adapter.get_current_state(market))
                    print(session.execute(BotAction.sell(market, Decimal(command[2]))))
                elif verb == "portfolio":
                    print(session.portfolio())
                elif verb == "history":
                    for trade in session.history:
                        print(trade)
                else:
                    print(
                        "Commands: price MARKET | buy MARKET EUR | sell MARKET QTY | "
                        "portfolio | history | quit"
                    )
            except (ValueError, InvalidOperation, MarketDataError) as exc:
                print(f"Error: {exc}")
    finally:
        await adapter.aclose()


def main() -> None:
    configure_logging(get_settings().log_level)
    args = build_parser().parse_args()
    try:
        if args.command == "price":
            asyncio.run(run_price(args.market))
        elif args.command == "candles":
            asyncio.run(run_candles(args))
        else:
            asyncio.run(run_interactive())
    except KeyboardInterrupt:
        print("\nPaper session closed.")


if __name__ == "__main__":
    main()
