from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest
from ai_trainer.domain.entities import DatasetRow
from ai_trainer.evaluation.backtesting.candle_execution import (
    buy_and_hold,
    execution_windows,
    simulate,
)
from ai_trainer.training.supervised.bot_research import Costs
from ai_trainer.training.tuning.chronological import tune, tuning_folds
from shared.contracts import Candle, MarketSymbol


def bars() -> tuple[Candle, ...]:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            MarketSymbol("BTC-EUR"),
            "1h",
            start + timedelta(hours=i),
            Decimal(100),
            Decimal(110),
            Decimal(50),
            Decimal(100),
            Decimal(10),
        )
        for i in range(12)
    )


def test_delayed_execution_intratrade_loss_fees_and_no_overlap() -> None:
    candles = bars()
    rows = tuple(DatasetRow(c.timestamp, {}, {}) for c in candles[:6])
    windows = execution_windows(candles, [r.timestamp for r in rows], 3)
    assert windows[rows[0].timestamp].entry_at == rows[0].timestamp + timedelta(hours=1)
    assert windows[rows[0].timestamp].exit_at == rows[0].timestamp + timedelta(hours=4)
    costs = Costs()
    result = simulate(rows, [0.1] * len(rows), 0, costs, windows)
    assert result["trades"] == 2
    assert result["net_return"] == pytest.approx((1 + 0.1 * costs.net(0)) ** 2 - 1)
    assert result["max_drawdown"] > 0.05  # Terminal returns alone miss the 50% intratrade drop.
    assert result["fees_fraction_initial_capital"] > 0
    assert result["slippage_fraction_initial_capital"] > 0
    missing = execution_windows(candles[:2] + candles[3:], [r.timestamp for r in rows], 3)
    assert rows[0].timestamp not in missing


def test_entry_uses_later_open_and_buy_hold_trades_only_once() -> None:
    candles = bars()
    altered = tuple(replace(c, open=Decimal(105)) if i == 1 else c for i, c in enumerate(candles))
    window = execution_windows(altered, [candles[0].timestamp], 3)[candles[0].timestamp]
    assert window.gross_return == pytest.approx(100 / 105 - 1)
    assert buy_and_hold(candles, Costs())["trades"] == 1


def test_optuna_uses_purged_chronological_folds_and_persists(tmp_path: Path) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = tuple(
        DatasetRow(
            start + timedelta(hours=i),
            {"market_x": float(i % 7)},
            {},
            float(np.sin(i) * 0.01),
            start + timedelta(hours=i + 25),
        )
        for i in range(600)
    )
    for train, stop, held in tuning_folds(rows):
        assert rows[train[-1]].target_at < rows[stop[0]].timestamp
        assert rows[stop[-1]].target_at < rows[held[0]].timestamp
    params, report = tune(rows, ["market_x"], 2, tmp_path / "study.db", "test")
    assert report["trials"] == 2
    assert params and (tmp_path / "study.db").exists()
    assert report["latest_input_time"] == rows[-1].timestamp.isoformat()
