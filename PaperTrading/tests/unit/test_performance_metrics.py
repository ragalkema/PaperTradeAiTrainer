from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from paper_trading.application.services.performance import PerformanceMetricsService
from paper_trading.domain.entities import PaperTradeRecord, PortfolioSnapshotRecord
from shared.contracts import ActionType, MarketSymbol


def snapshot(minute: int, value: str) -> PortfolioSnapshotRecord:
    amount = Decimal(value)
    return PortfolioSnapshotRecord(
        uuid4(),
        uuid4(),
        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minute),
        amount,
        Decimal("0"),
        amount,
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    )


def trade(pnl: str) -> PaperTradeRecord:
    return PaperTradeRecord(
        uuid4(),
        uuid4(),
        uuid4(),
        MarketSymbol("BTC-EUR"),
        ActionType.SELL,
        Decimal("1"),
        Decimal("1"),
        Decimal("100"),
        Decimal("100"),
        Decimal("100"),
        Decimal("1"),
        Decimal("0"),
        Decimal(pnl),
        datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.unit
def test_drawdown_uses_equity_curve_and_current_peak() -> None:
    snapshots = (
        snapshot(0, "10000"),
        snapshot(1, "11000"),
        snapshot(2, "9900"),
        snapshot(3, "10500"),
    )
    report = PerformanceMetricsService.calculate(
        snapshots, (trade("200"), trade("-50")), Decimal("10000")
    )
    assert report.maximum_drawdown == Decimal("0.1")
    assert report.current_drawdown == Decimal("500") / Decimal("11000")
    assert report.win_rate == Decimal("0.5")
    assert report.profit_factor == Decimal("4")
    assert report.average_winning_trade == Decimal("200")
    assert report.average_losing_trade == Decimal("-50")


@pytest.mark.unit
def test_empty_history_returns_safe_zero_metrics() -> None:
    report = PerformanceMetricsService.calculate((), (), Decimal("10000"))
    assert report.current_value == Decimal("10000")
    assert report.maximum_drawdown == 0
    assert report.profit_factor is None
