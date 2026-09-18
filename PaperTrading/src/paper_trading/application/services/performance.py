"""Performance calculations over persisted facts, independent of presentation/storage."""

from decimal import Decimal

from paper_trading.domain.entities import (
    PaperTradeRecord,
    PerformanceReport,
    PortfolioSnapshotRecord,
)


class PerformanceMetricsService:
    @staticmethod
    def calculate(
        snapshots: tuple[PortfolioSnapshotRecord, ...],
        trades: tuple[PaperTradeRecord, ...],
        starting_value: Decimal,
    ) -> PerformanceReport:
        if starting_value <= 0:
            raise ValueError("starting_value must be positive")
        ordered = tuple(sorted(snapshots, key=lambda item: (item.timestamp, item.snapshot_id)))
        current = ordered[-1] if ordered else None
        current_value = current.portfolio_value if current else starting_value
        realized = current.realized_pnl if current else Decimal("0")
        unrealized = current.unrealized_pnl if current else Decimal("0")
        fees = current.fees_paid if current else sum((item.fee for item in trades), Decimal("0"))
        closed = [item.realized_pnl for item in trades if item.realized_pnl != 0]
        wins = [value for value in closed if value > 0]
        losses = [value for value in closed if value < 0]
        peak = starting_value
        maximum_drawdown = Decimal("0")
        for snapshot in ordered:
            peak = max(peak, snapshot.portfolio_value)
            maximum_drawdown = max(
                maximum_drawdown,
                (peak - snapshot.portfolio_value) / peak if peak else Decimal("0"),
            )
        current_drawdown = (peak - current_value) / peak if peak else Decimal("0")
        gross_profit = sum(wins, Decimal("0"))
        gross_loss = abs(sum(losses, Decimal("0")))
        return PerformanceReport(
            starting_value=starting_value,
            current_value=current_value,
            absolute_pnl=current_value - starting_value,
            percentage_return=(current_value - starting_value) / starting_value,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            fees_paid=fees,
            trade_count=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=Decimal(len(wins)) / Decimal(len(closed)) if closed else Decimal("0"),
            average_winning_trade=gross_profit / len(wins) if wins else None,
            average_losing_trade=sum(losses, Decimal("0")) / len(losses) if losses else None,
            largest_win=max(wins) if wins else None,
            largest_loss=min(losses) if losses else None,
            maximum_drawdown=maximum_drawdown,
            current_drawdown=current_drawdown,
            profit_factor=gross_profit / gross_loss if gross_loss else None,
        )
