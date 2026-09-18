"""Buffer point-in-time experiment facts and persist them through an application port."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol, cast
from uuid import UUID, uuid4

from shared.contracts import ActionType, AssetSymbol, BotAction, MarketState, TradeResult

from paper_trading.application.ports import ResearchWritePort
from paper_trading.application.services.recording_policy import RecordingPolicy
from paper_trading.domain.entities import (
    BotDecisionRecord,
    DecisionContextRecord,
    PaperTradeRecord,
    PortfolioSnapshotRecord,
    PositionRecord,
    PositionStatus,
)


class PortfolioObservation(Protocol):
    cash: Decimal
    portfolio_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees_paid: Decimal
    asset_balances: dict[AssetSymbol, Decimal]
    asset_values: dict[AssetSymbol, Decimal]
    asset_cost_basis: dict[AssetSymbol, Decimal]


class ResearchRunRecorder:
    """Synchronous runner observer with an explicit asynchronous flush boundary."""

    def __init__(
        self,
        session_id: UUID,
        session_bots: dict[str, UUID],
        policy: RecordingPolicy | None = None,
    ) -> None:
        self.session_id = session_id
        self.session_bots = session_bots
        self.policy = policy or RecordingPolicy()
        self.snapshots: list[PortfolioSnapshotRecord] = []
        self.trades: list[PaperTradeRecord] = []
        self.decisions: list[BotDecisionRecord] = []
        self.positions: list[PositionRecord] = []
        self._last_snapshot: dict[str, datetime] = {}
        self._last_hold: dict[str, datetime] = {}
        self._opened_at: dict[tuple[str, str], datetime] = {}

    def on_step(
        self,
        bot_name: str,
        state: MarketState,
        action: BotAction,
        result: TradeResult,
        portfolio: object,
    ) -> None:
        session_bot_id = self.session_bots[bot_name]
        cash = _decimal_attr(portfolio, "cash")
        portfolio_value = _decimal_attr(portfolio, "portfolio_value")
        realized = _decimal_attr(portfolio, "realized_pnl")
        unrealized = _decimal_attr(portfolio, "unrealized_pnl")
        fees = _decimal_attr(portfolio, "fees_paid")
        observation = cast(PortfolioObservation, portfolio)
        balances = observation.asset_balances
        values = observation.asset_values
        cost_basis = observation.asset_cost_basis
        position = balances.get(state.market.base, Decimal("0"))
        asset_value = sum(values.values(), Decimal("0"))

        trade: PaperTradeRecord | None = None
        if result.accepted and result.trade_id is not None:
            trade = PaperTradeRecord(
                result.trade_id,
                self.session_id,
                session_bot_id,
                result.market,
                result.action,
                action.quantity,
                result.quantity,
                result.market_price or state.current_price,
                result.execution_price or state.current_price,
                result.quantity * (result.execution_price or state.current_price),
                result.fee,
                result.slippage,
                result.realized_pnl,
                result.timestamp,
            )
            self.trades.append(trade)

        if self.policy.should_record_decision(
            action.action, state.timestamp, self._last_hold.get(bot_name)
        ):
            context = DecisionContextRecord(
                state.timestamp,
                state.current_price,
                state.bid,
                state.ask,
                state.spread,
                portfolio_value,
                cash,
                position,
            )
            requested_size = (
                action.requested_value if action.action is ActionType.BUY else action.quantity
            )
            self.decisions.append(
                BotDecisionRecord(
                    uuid4(),
                    self.session_id,
                    session_bot_id,
                    state.timestamp,
                    state.market,
                    action.action,
                    requested_size,
                    context,
                    executed_trade_id=trade.trade_id if trade else None,
                )
            )
            if action.action is ActionType.HOLD:
                self._last_hold[bot_name] = state.timestamp

        if self.policy.should_snapshot(state.timestamp, self._last_snapshot.get(bot_name)):
            self.snapshots.append(
                PortfolioSnapshotRecord(
                    uuid4(),
                    session_bot_id,
                    state.timestamp,
                    cash,
                    asset_value,
                    portfolio_value,
                    realized,
                    unrealized,
                    fees,
                )
            )
            self._last_snapshot[bot_name] = state.timestamp
            for asset, quantity in balances.items():
                if quantity <= 0:
                    continue
                key = (bot_name, str(asset))
                opened_at = self._opened_at.setdefault(key, state.timestamp)
                basis = cost_basis.get(asset, Decimal("0"))
                current_price = state.current_price if asset == state.market.base else Decimal("0")
                current_value = values.get(asset, Decimal("0"))
                self.positions.append(
                    PositionRecord(
                        uuid4(),
                        session_bot_id,
                        state.timestamp,
                        state.market,
                        "long",
                        quantity,
                        basis / quantity if quantity else Decimal("0"),
                        current_price,
                        realized,
                        current_value - basis,
                        opened_at,
                        PositionStatus.OPEN,
                    )
                )

    async def flush(self, repository: ResearchWritePort) -> None:
        for trade in self.trades:
            await repository.add_trade(trade)
        for decision in self.decisions:
            await repository.add_decision(decision)
        for snapshot in self.snapshots:
            await repository.add_snapshot(snapshot)
        for position in self.positions:
            await repository.add_position(position)


def _decimal_attr(value: object, name: str) -> Decimal:
    result = getattr(value, name)
    if not isinstance(result, Decimal):
        raise TypeError(f"portfolio {name} must be Decimal")
    return result
