"""Delayed spot execution and conservative OHLC mark-to-market accounting."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from shared.contracts import Candle

from ai_trainer.domain.entities import DatasetRow


class CostModel(Protocol):
    @property
    def fee_per_side(self) -> float: ...

    @property
    def spread_slippage_per_side(self) -> float: ...

    def net(self, gross: float) -> float: ...


@dataclass(frozen=True)
class ExecutionWindow:
    entry_at: datetime
    exit_at: datetime
    bars: tuple[Candle, ...]
    exit_open: float

    @property
    def gross_return(self) -> float:
        return self.exit_open / float(self.bars[0].open) - 1


def execution_windows(
    candles: Sequence[Candle],
    decision_times: Sequence[datetime],
    horizon: int,
) -> dict[datetime, ExecutionWindow]:
    """Wait one full bar after the completed decision; require every held bar.

    Candle timestamps denote OPEN time. The decision is the preceding candle CLOSE.
    An explicit one-hour latency prevents assuming a fill at an already observed close.
    """
    if any(c.interval != "1h" for c in candles) or horizon < 1:
        raise ValueError("one-hour candles and positive horizon required")
    by_time = {c.timestamp: c for c in candles}
    if len(by_time) != len(candles):
        raise ValueError("duplicate execution candles")
    output = {}
    for time in decision_times:
        entry = time + timedelta(hours=1)
        times = [entry + timedelta(hours=i) for i in range(horizon + 1)]
        if not all(t in by_time for t in times):
            continue
        output[time] = ExecutionWindow(
            entry, times[-1], tuple(by_time[t] for t in times[:-1]), float(by_time[times[-1]].open)
        )
    return output


def simulate(
    rows: Sequence[DatasetRow],
    predictions: Sequence[float],
    edge: float,
    costs: CostModel,
    windows: dict[datetime, ExecutionWindow],
    *,
    allocation: float = 0.1,
) -> dict[str, float | int]:
    """One position; horizon exit; fee/slippage applied on each actual notional.

    Drawdown is a conservative OHLC bound: each bar's high precedes its low for
    risk measurement only. No claim about the actual intrabar price order is made.
    """
    if not rows or len(rows) != len(predictions) or not 0 < allocation <= 1:
        raise ValueError("nonempty matched predictions and allocation in (0,1] required")
    fee, slip = costs.fee_per_side, costs.spread_slippage_per_side
    if not 0 <= fee < 1 or not 0 <= slip < 1:
        raise ValueError("invalid execution costs")
    equity = peak = 1.0
    drawdown = fees = friction = 0.0
    trades = wins = missing = 0
    available = rows[0].timestamp
    for row, prediction in zip(rows, predictions, strict=True):
        if not math.isfinite(prediction):
            raise ValueError("nonfinite prediction")
        if row.timestamp < available or costs.net(prediction) <= edge:
            continue
        window = windows.get(row.timestamp)
        if window is None:
            missing += 1
            continue
        budget = equity * allocation
        cash = equity - budget
        opening = float(window.bars[0].open)
        fill = opening * (1 + slip)
        quantity = budget / (fill * (1 + fee))
        entry_fee = quantity * fill * fee
        fees += entry_fee
        friction += quantity * opening * slip
        for bar in window.bars:
            # Liquidation-value marks include exit friction and fees.
            high = cash + quantity * float(bar.high) * (1 - slip) * (1 - fee)
            low = cash + quantity * float(bar.low) * (1 - slip) * (1 - fee)
            peak = max(peak, high)
            drawdown = max(drawdown, 1 - low / peak)
        exit_fill = window.exit_open * (1 - slip)
        exit_fee = quantity * exit_fill * fee
        fees += exit_fee
        friction += quantity * window.exit_open * slip
        settled = cash + quantity * exit_fill - exit_fee
        wins += settled > equity
        equity = settled
        peak = max(peak, equity)
        drawdown = max(drawdown, 1 - equity / peak)
        trades += 1
        available = window.exit_at
    return {
        "net_return": equity - 1,
        "max_drawdown": drawdown,
        "trades": trades,
        "wins_after_costs": wins,
        "fees_fraction_initial_capital": fees,
        "slippage_fraction_initial_capital": friction,
        "skipped_missing_execution": missing,
    }


def buy_and_hold(candles: Sequence[Candle], costs: CostModel) -> dict[str, float | int]:
    if len(candles) < 2:
        raise ValueError("at least two candles required")
    first, last = candles[0], candles[-1]
    row = DatasetRow(first.timestamp, {}, {}, 0, last.timestamp)
    window = ExecutionWindow(first.timestamp, last.timestamp, tuple(candles[:-1]), float(last.open))
    return simulate((row,), (1.0,), 0, costs, {row.timestamp: window})
