"""Deterministic virtual market-order execution engine."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.contracts import (
    ActionType,
    AssetSymbol,
    BotAction,
    MarketState,
    MarketSymbol,
    PerformanceMetrics,
    TradeResult,
)

from paper_trading.domain.entities import PaperTrade, PortfolioSnapshot, VirtualPortfolio
from paper_trading.domain.value_objects import ExecutionConfig


class DeterministicPaperExchange:
    """Network-free paper exchange supporting spot BUY, SELL, and HOLD actions."""

    ACCOUNTING_TOLERANCE = Decimal("1e-24")

    def __init__(
        self,
        starting_balance: Decimal,
        config: ExecutionConfig | None = None,
    ) -> None:
        if not starting_balance.is_finite() or starting_balance <= 0:
            raise ValueError("starting_balance must be finite and positive")
        self.config = config or ExecutionConfig()
        self._portfolio = VirtualPortfolio(starting_balance, starting_balance)
        self._markets: dict[MarketSymbol, MarketState] = {}
        self._trades: list[PaperTrade] = []
        self._equity_curve: list[Decimal] = [starting_balance]

    def update_market(self, state: MarketState) -> None:
        previous = self._markets.get(state.market)
        if previous is not None and state.timestamp < previous.timestamp:
            raise ValueError("market state timestamp moved backwards")
        self._markets[state.market] = state
        self._record_equity(state.timestamp)

    def execute(self, action: BotAction) -> TradeResult:
        state = self._markets.get(action.market)
        if state is None:
            raise ValueError(f"no market state available for {action.market}")
        if action.action is ActionType.HOLD:
            return TradeResult(True, action.action, action.market, state.timestamp)
        result = (
            self._buy(action, state)
            if action.action is ActionType.BUY
            else self._sell(action, state)
        )
        self._record_equity(state.timestamp)
        self.validate_invariants()
        return result

    def _buy(self, action: BotAction, state: MarketState) -> TradeResult:
        execution_price = state.ask * (Decimal("1") + self.config.slippage_rate)
        requested = action.requested_value
        fee = requested * self.config.fee_rate
        total_cost = requested + fee
        if total_cost > self._portfolio.cash:
            return self._rejected(action, state, "insufficient cash")
        quantity = requested / execution_price
        asset = action.market.base
        self._portfolio.cash -= total_cost
        self._portfolio.balances[asset] = (
            self._portfolio.balances.get(asset, Decimal("0")) + quantity
        )
        self._portfolio.cost_basis[asset] = (
            self._portfolio.cost_basis.get(asset, Decimal("0")) + total_cost
        )
        self._portfolio.fees_paid += fee
        slippage = quantity * (execution_price - state.ask)
        return self._filled(action, state, quantity, execution_price, fee, slippage, Decimal("0"))

    def _sell(self, action: BotAction, state: MarketState) -> TradeResult:
        asset = action.market.base
        owned = self._portfolio.balances.get(asset, Decimal("0"))
        if action.quantity > owned:
            return self._rejected(action, state, "insufficient asset balance")
        execution_price = state.bid * (Decimal("1") - self.config.slippage_rate)
        proceeds = action.quantity * execution_price
        fee = proceeds * self.config.fee_rate
        net_proceeds = proceeds - fee
        total_basis = self._portfolio.cost_basis.get(asset, Decimal("0"))
        allocated_basis = total_basis * (action.quantity / owned)
        realized_pnl = net_proceeds - allocated_basis
        remaining = owned - action.quantity
        self._portfolio.cash += net_proceeds
        self._portfolio.realized_pnl += realized_pnl
        self._portfolio.fees_paid += fee
        self._portfolio.balances[asset] = remaining
        self._portfolio.cost_basis[asset] = total_basis - allocated_basis
        slippage = action.quantity * (state.bid - execution_price)
        return self._filled(
            action, state, action.quantity, execution_price, fee, slippage, realized_pnl
        )

    def _filled(
        self,
        action: BotAction,
        state: MarketState,
        quantity: Decimal,
        execution_price: Decimal,
        fee: Decimal,
        slippage: Decimal,
        realized_pnl: Decimal,
    ) -> TradeResult:
        trade_id = UUID(int=len(self._trades) + 1)
        market_price = state.ask if action.action is ActionType.BUY else state.bid
        requested_value = (
            action.requested_value if action.action is ActionType.BUY else quantity * market_price
        )
        trade = PaperTrade(
            trade_id,
            state.timestamp,
            action.market,
            action.action,
            quantity,
            requested_value,
            market_price,
            execution_price,
            fee,
            slippage,
            realized_pnl,
        )
        self._trades.append(trade)
        return TradeResult(
            True,
            action.action,
            action.market,
            state.timestamp,
            quantity,
            requested_value,
            market_price,
            execution_price,
            fee,
            slippage,
            realized_pnl,
            trade_id,
        )

    @staticmethod
    def _rejected(action: BotAction, state: MarketState, reason: str) -> TradeResult:
        return TradeResult(
            False,
            action.action,
            action.market,
            state.timestamp,
            action.quantity,
            action.requested_value,
            reason=reason,
        )

    def snapshot(self, timestamp: datetime | None = None) -> PortfolioSnapshot:
        if timestamp is None:
            timestamp = max((state.timestamp for state in self._markets.values()), default=None)
        if timestamp is None:
            raise ValueError("portfolio cannot be valued before a market update")
        values: dict[AssetSymbol, Decimal] = {}
        unrealized = Decimal("0")
        for asset, quantity in self._portfolio.balances.items():
            state = self._state_for_asset(asset)
            value = quantity * state.current_price
            values[asset] = value
            unrealized += value - self._portfolio.cost_basis.get(asset, Decimal("0"))
        total = self._portfolio.cash + sum(values.values(), Decimal("0"))
        return PortfolioSnapshot(
            timestamp,
            self._portfolio.starting_balance,
            self._portfolio.cash,
            dict(self._portfolio.balances),
            values,
            unrealized,
            self._portfolio.realized_pnl,
            total,
            self._portfolio.fees_paid,
        )

    def _state_for_asset(self, asset: AssetSymbol) -> MarketState:
        matches = [state for market, state in self._markets.items() if market.base == asset]
        if not matches:
            raise ValueError(f"no price available for {asset}")
        return max(matches, key=lambda state: state.timestamp)

    @property
    def trades(self) -> tuple[PaperTrade, ...]:
        return tuple(self._trades)

    def metrics(self) -> PerformanceMetrics:
        snapshot = self.snapshot()
        pnl = snapshot.portfolio_value - snapshot.starting_balance
        sells = [trade for trade in self._trades if trade.side is ActionType.SELL]
        wins = sum(trade.realized_pnl > 0 for trade in sells)
        losses = sum(trade.realized_pnl < 0 for trade in sells)
        closed = wins + losses
        return PerformanceMetrics(
            snapshot.starting_balance,
            snapshot.portfolio_value,
            pnl,
            pnl / snapshot.starting_balance,
            len(self._trades),
            snapshot.fees_paid,
            wins,
            losses,
            Decimal(wins) / Decimal(closed) if closed else Decimal("0"),
            self._maximum_drawdown(),
        )

    def _record_equity(self, timestamp: datetime) -> None:
        if self._markets:
            self._equity_curve.append(self.snapshot(timestamp).portfolio_value)

    def _maximum_drawdown(self) -> Decimal:
        peak = self._equity_curve[0]
        maximum = Decimal("0")
        for value in self._equity_curve:
            peak = max(peak, value)
            if peak > 0:
                maximum = max(maximum, (peak - value) / peak)
        return maximum

    def validate_invariants(self) -> None:
        if self._portfolio.cash < 0:
            raise RuntimeError("paper portfolio cash became negative")
        if any(quantity < 0 for quantity in self._portfolio.balances.values()):
            raise RuntimeError("paper portfolio asset balance became negative")
        if self._portfolio.fees_paid != sum((trade.fee for trade in self._trades), Decimal("0")):
            raise RuntimeError("paper portfolio fee accounting is inconsistent")
        remaining_basis = sum(self._portfolio.cost_basis.values(), Decimal("0"))
        conservation_delta = (
            self._portfolio.cash
            + remaining_basis
            - (self._portfolio.starting_balance + self._portfolio.realized_pnl)
        )
        if abs(conservation_delta) > self.ACCOUNTING_TOLERANCE:
            raise RuntimeError("paper portfolio conservation invariant failed")
        for asset, balance in self._portfolio.balances.items():
            bought = sum(
                (
                    trade.quantity
                    for trade in self._trades
                    if trade.market.base == asset and trade.side is ActionType.BUY
                ),
                Decimal("0"),
            )
            sold = sum(
                (
                    trade.quantity
                    for trade in self._trades
                    if trade.market.base == asset and trade.side is ActionType.SELL
                ),
                Decimal("0"),
            )
            if abs(balance - (bought - sold)) > self.ACCOUNTING_TOLERANCE:
                raise RuntimeError("paper portfolio asset conservation invariant failed")
