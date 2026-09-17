"""Application-level paper-trading session."""

import logging
from decimal import Decimal

from shared.contracts import BotAction, MarketState, PerformanceMetrics, TradeResult

from paper_trading.domain.entities import PaperTrade, PortfolioSnapshot
from paper_trading.domain.services import DeterministicPaperExchange
from paper_trading.domain.value_objects import ExecutionConfig

logger = logging.getLogger(__name__)


class PaperTradingSession:
    """One isolated account, market view, and virtual execution history."""

    def __init__(
        self,
        starting_balance: Decimal = Decimal("10000"),
        fee_rate: Decimal = Decimal("0.0025"),
        slippage_rate: Decimal = Decimal("0.0005"),
    ) -> None:
        self._exchange = DeterministicPaperExchange(
            starting_balance,
            ExecutionConfig(fee_rate=fee_rate, slippage_rate=slippage_rate),
        )

    def update_market(self, state: MarketState) -> None:
        self._exchange.update_market(state)
        logger.debug(
            "market_update market=%s timestamp=%s", state.market, state.timestamp.isoformat()
        )

    def execute(self, action: BotAction) -> TradeResult:
        result = self._exchange.execute(action)
        if result.trade_id is not None:
            logger.info(
                "paper_trade market=%s side=%s quantity=%s fee=%s",
                result.market,
                result.action,
                result.quantity,
                result.fee,
            )
        elif not result.accepted:
            logger.warning(
                "paper_trade_rejected market=%s side=%s reason=%s",
                result.market,
                result.action,
                result.reason,
            )
        return result

    def portfolio(self) -> PortfolioSnapshot:
        return self._exchange.snapshot()

    def metrics(self) -> PerformanceMetrics:
        return self._exchange.metrics()

    @property
    def history(self) -> tuple[PaperTrade, ...]:
        return self._exchange.trades
