"""Run multiple bots against the same chronological candles."""

import logging
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal

from shared.contracts import Candle, MarketState

from ai_trainer.application.ports import PaperSessionPort, TradingBot
from ai_trainer.application.services.bot_runner import MultiBotRunner
from ai_trainer.domain.entities import HistoricalExperimentConfig, HistoricalExperimentResult

logger = logging.getLogger(__name__)


class HistoricalExperimentRunner:
    """Deterministic historical comparison without claiming predictive value."""

    def __init__(
        self,
        bots: Mapping[str, TradingBot],
        session_factory: Callable[[], PaperSessionPort],
    ) -> None:
        self._bots = dict(bots)
        self._runner = MultiBotRunner(self._bots, session_factory)

    def run(
        self,
        candles: Sequence[Candle],
        *,
        starting_balance: Decimal,
        fee_rate: Decimal,
        slippage_rate: Decimal,
        random_seed: int,
        bot_configuration: dict[str, dict[str, str | int]],
        git_commit: str | None = None,
    ) -> HistoricalExperimentResult:
        if not candles:
            raise ValueError("at least one candle is required")
        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        market = ordered[0].market
        interval = ordered[0].interval
        if any(candle.market != market or candle.interval != interval for candle in ordered):
            raise ValueError("all candles must have one market and interval")
        logger.info(
            "experiment_started market=%s interval=%s observations=%s",
            market,
            interval,
            len(ordered),
        )
        states = [
            MarketState(
                candle.market,
                candle.timestamp,
                candle.close,
                candle.close,
                candle.close,
                candle.volume,
            )
            for candle in ordered
        ]
        metrics = self._runner.run(states)
        config = HistoricalExperimentConfig(
            market,
            interval,
            ordered[0].timestamp,
            ordered[-1].timestamp,
            starting_balance,
            fee_rate,
            slippage_rate,
            random_seed,
            bot_configuration,
            git_commit,
        )
        result = HistoricalExperimentResult(config, metrics)
        logger.info("experiment_finished market=%s bots=%s", market, len(metrics))
        return result
