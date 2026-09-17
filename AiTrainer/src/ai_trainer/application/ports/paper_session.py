"""Structural contract required by bot and experiment runners."""

from typing import Protocol

from shared.contracts import BotAction, MarketState, PerformanceMetrics, TradeResult


class PaperSessionPort(Protocol):
    """Minimal paper environment known to AiTrainer."""

    def update_market(self, state: MarketState) -> None: ...

    def execute(self, action: BotAction) -> TradeResult: ...

    def metrics(self) -> PerformanceMetrics: ...
