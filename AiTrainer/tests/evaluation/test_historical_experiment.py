"""Multi-bot historical experiment tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from ai_trainer.application.services import HistoricalExperimentRunner
from ai_trainer.bots.baselines import BuyAndHoldBot, MovingAverageBot, RandomBot
from paper_trading import PaperTradingSession
from shared.contracts import Candle, MarketSymbol


def candles() -> list[Candle]:
    market = MarketSymbol("BTC-EUR")
    prices = ("100", "102", "104", "103", "106", "108", "105", "110")
    return [
        Candle(
            market,
            "1h",
            datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
            Decimal(price),
            Decimal(price),
            Decimal(price),
            Decimal(price),
            Decimal("1"),
        )
        for index, price in enumerate(prices)
    ]


def run_experiment() -> object:
    start = Decimal("10000")
    fee = Decimal("0.0025")
    slippage = Decimal("0.0005")
    runner = HistoricalExperimentRunner(
        {
            "RandomBot": RandomBot(Decimal("100"), seed=42),
            "BuyAndHoldBot": BuyAndHoldBot(Decimal("1000")),
            "MovingAverageBot": MovingAverageBot(2, 3, Decimal("1000")),
        },
        lambda: PaperTradingSession(start, fee, slippage),
    )
    return runner.run(
        candles(),
        starting_balance=start,
        fee_rate=fee,
        slippage_rate=slippage,
        random_seed=42,
        bot_configuration={"RandomBot": {"seed": 42}},
        git_commit="abc123",
    )


@pytest.mark.training
def test_all_bots_receive_same_history_with_independent_accounts() -> None:
    result = run_experiment()
    assert set(result.bot_metrics) == {"RandomBot", "BuyAndHoldBot", "MovingAverageBot"}
    assert all(
        metric.starting_balance == Decimal("10000") for metric in result.bot_metrics.values()
    )
    assert result.config.random_seed == 42
    assert "Historical results do not predict" in result.table()


@pytest.mark.training
def test_seeded_historical_experiment_is_reproducible() -> None:
    first = run_experiment()
    second = run_experiment()
    assert first.bot_metrics == second.bot_metrics
