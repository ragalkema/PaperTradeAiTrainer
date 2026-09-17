"""Source-neutral single and multi-bot runtime."""

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from shared.contracts import MarketState, PerformanceMetrics

from ai_trainer.application.ports import PaperSessionPort, TradingBot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BotRuntime:
    """One bot paired with one independent paper account."""

    bot: TradingBot
    session: PaperSessionPort


class MultiBotRunner:
    """Broadcast identical ordered observations to isolated bot runtimes."""

    def __init__(
        self,
        bots: Mapping[str, TradingBot],
        session_factory: Callable[[], PaperSessionPort],
    ) -> None:
        if not bots:
            raise ValueError("at least one bot is required")
        for bot in bots.values():
            bot.reset()
        self._runtimes = {
            name: BotRuntime(bot=bot, session=session_factory()) for name, bot in bots.items()
        }

    def run(self, states: Iterable[MarketState]) -> dict[str, PerformanceMetrics]:
        previous = None
        processed = 0
        for state in states:
            if previous is not None and state.timestamp < previous:
                raise ValueError("market states must be chronological")
            previous = state.timestamp
            processed += 1
            for name, runtime in self._runtimes.items():
                runtime.session.update_market(state)
                runtime.bot.observe(state)
                action = runtime.bot.decide()
                logger.debug(
                    "bot_action bot=%s market=%s action=%s", name, state.market, action.action
                )
                result = runtime.session.execute(action)
                runtime.bot.on_trade_result(result)
        if processed == 0:
            raise ValueError("at least one market state is required")
        return {name: runtime.session.metrics() for name, runtime in self._runtimes.items()}
