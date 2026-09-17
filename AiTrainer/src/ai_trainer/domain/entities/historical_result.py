"""Reproducible historical experiment output."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from shared.contracts import MarketSymbol, PerformanceMetrics


@dataclass(frozen=True, slots=True)
class HistoricalExperimentConfig:
    market: MarketSymbol
    interval: str
    start: datetime
    end: datetime
    starting_balance: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    random_seed: int
    bot_configuration: dict[str, dict[str, str | int]]
    git_commit: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalExperimentResult:
    config: HistoricalExperimentConfig
    bot_metrics: dict[str, PerformanceMetrics]

    def table(self) -> str:
        lines = [
            f"Experiment: {self.config.market}",
            f"Period: {self.config.start.isoformat()} to {self.config.end.isoformat()}",
            f"Starting balance: EUR {self.config.starting_balance}",
            "",
            f"{'Bot':<20} {'Return':>10} {'Max DD':>10} {'Trades':>8} {'Fees':>12}",
            "-" * 64,
        ]
        for name, metrics in self.bot_metrics.items():
            lines.append(
                f"{name:<20} {metrics.percentage_return:>9.2%} "
                f"{metrics.maximum_drawdown:>9.2%} {metrics.trade_count:>8} "
                f"{metrics.fees_paid:>12.2f}"
            )
        lines.append("Historical results do not predict future profitability.")
        return "\n".join(lines)
