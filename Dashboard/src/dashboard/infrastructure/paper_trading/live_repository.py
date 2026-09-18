"""Bounded public market query adapter; it never exposes order capabilities."""

import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Lock
from typing import Any, cast

from data_collector.application.ports import NewsQueryPort
from paper_trading.application.ports import ResearchQueryPort
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from shared.contracts import MarketSymbol

from dashboard.application.view_models import (
    BotSummary,
    ConnectionState,
    DashboardSnapshot,
    DecisionSummary,
    ExperimentSummary,
    IntelligenceEvent,
    MarketSummary,
    PortfolioSummary,
    PositionSummary,
    SessionSummary,
    TradeSummary,
)

logger = logging.getLogger(__name__)


class LiveDashboardRepository:
    """Thread-safe latest snapshot backed only by public Bitvavo reads."""

    def __init__(
        self,
        markets: tuple[str, ...] = ("BTC-EUR", "ETH-EUR", "SOL-EUR"),
        research: ResearchQueryPort | None = None,
        news: NewsQueryPort | None = None,
    ) -> None:
        self._markets = markets
        self._research = research
        self._news = news
        initial = tuple(
            MarketSummary(market, state=ConnectionState.CONNECTING) for market in markets
        )
        self._snapshot = DashboardSnapshot(
            markets=initial,
            connections={
                "Bitvavo": ConnectionState.CONNECTING,
                "News": ConnectionState.CONNECTING if news else ConnectionState.DISABLED,
                "Social/X": ConnectionState.DISABLED,
                "PostgreSQL": ConnectionState.DISCONNECTED,
                "Redis": ConnectionState.DISCONNECTED,
            },
        )
        self._lock = Lock()

    def snapshot(self) -> DashboardSnapshot:
        with self._lock:
            return self._snapshot

    def refresh(self) -> DashboardSnapshot:
        """Refresh in a worker thread, never the Qt event thread."""
        try:
            markets = asyncio.run(self._fetch())
            connections = dict(self.snapshot().connections)
            connections["Bitvavo"] = ConnectionState.CONNECTED
            research_values: dict[str, object] = {}
            errors: tuple[str, ...] = ()
            if self._research:
                try:
                    research_values = asyncio.run(self._fetch_research())
                    connections["PostgreSQL"] = ConnectionState.CONNECTED
                except Exception:
                    logger.exception("dashboard_research_refresh_failed")
                    connections["PostgreSQL"] = ConnectionState.ERROR
                    errors = ("Research database unavailable. Market data remains live.",)
            news_values: dict[str, object] = {}
            if self._news:
                try:
                    news_values = {"news": asyncio.run(self._fetch_news())}
                    connections["News"] = ConnectionState.CONNECTED
                except Exception:
                    logger.exception("dashboard_news_refresh_failed")
                    connections["News"] = ConnectionState.ERROR
                    errors += ("News database unavailable. Other data remains live.",)
            updated = replace(
                self.snapshot(),
                markets=markets,
                connections=connections,
                errors=errors,
                **cast(Any, research_values),
                **cast(Any, news_values),
            )
        except Exception:  # UI boundary converts details to logs and safe state.
            logger.exception("dashboard_market_refresh_failed")
            previous = self.snapshot()
            connections = dict(previous.connections)
            connections["Bitvavo"] = ConnectionState.ERROR
            markets = tuple(replace(item, state=ConnectionState.ERROR) for item in previous.markets)
            updated = replace(
                previous,
                markets=markets,
                connections=connections,
                errors=("Bitvavo connection unavailable. Retrying automatically.",),
            )
        with self._lock:
            self._snapshot = updated
        return updated

    async def _fetch_news(self) -> tuple[IntelligenceEvent, ...]:
        assert self._news is not None
        events = await self._news.recent_news(since=datetime.now(UTC) - timedelta(hours=24))
        return tuple(
            IntelligenceEvent(
                event_id=str(item.news_event_id),
                kind="news",
                occurred_at=item.received_at,
                title=item.title,
                source=item.source_name,
                assets=item.mentioned_assets,
                sentiment=item.sentiment,
                relevance=max(item.asset_relevance.values(), default=None),
                importance=item.importance,
            )
            for item in events
        )

    async def _fetch(self) -> tuple[MarketSummary, ...]:
        async with BitvavoMarketDataAdapter(timeout_seconds=7) as adapter:

            async def one(name: str) -> MarketSummary:
                symbol = MarketSymbol(name)
                state, candles = await asyncio.gather(
                    adapter.get_current_state(symbol),
                    adapter.get_candles(symbol, "1h", limit=72),
                )
                candle_values = tuple(
                    (c.timestamp, c.open, c.high, c.low, c.close, c.volume) for c in candles
                )
                high: Decimal | None
                low: Decimal | None
                volume: Decimal | None
                change: Decimal | None
                if candles:
                    high = max(c.high for c in candles[-24:])
                    low = min(c.low for c in candles[-24:])
                    volume = sum((c.volume for c in candles[-24:]), start=candles[0].volume * 0)
                    first = candles[-24].open if len(candles) >= 24 else candles[0].open
                    change = (state.current_price - first) / first
                else:
                    high = low = volume = change = None
                return MarketSummary(
                    market=name,
                    timestamp=state.timestamp,
                    current_price=state.current_price,
                    change_24h=change,
                    high_24h=high,
                    low_24h=low,
                    volume_24h=volume,
                    bid=state.bid,
                    ask=state.ask,
                    state=ConnectionState.CONNECTED,
                    candles=candle_values,
                )

            return tuple(await asyncio.gather(*(one(name) for name in self._markets)))

    async def _fetch_research(self) -> dict[str, object]:
        assert self._research is not None
        sessions, experiments = await asyncio.gather(
            self._research.active_sessions(), self._research.experiments()
        )
        result: dict[str, object] = {
            "sessions": tuple(
                SessionSummary(
                    str(item.session_id),
                    item.name,
                    item.status.value,
                    item.started_at,
                    tuple(str(market) for market in item.markets),
                )
                for item in sessions
            ),
            "experiments": tuple(
                ExperimentSummary(
                    str(item.experiment_id),
                    item.name,
                    item.status.value,
                    tuple(str(market) for market in item.markets),
                    item.start_period,
                    item.end_period,
                    item.starting_balance,
                    item.created_at,
                )
                for item in experiments
            ),
        }
        if not sessions:
            return result
        selected = sessions[0]
        participants = await self._research.session_bots(selected.session_id)
        definitions = await self._research.bot_definitions(
            tuple(item.bot_id for item in participants)
        )
        definitions_by_id = {item.bot_id: item for item in definitions}
        portfolios = await asyncio.gather(
            *(self._research.current_portfolio(item.session_bot_id) for item in participants)
        )
        performances = await asyncio.gather(
            *(self._research.performance(item.session_bot_id) for item in participants)
        )
        bots = []
        for participant, portfolio, performance in zip(
            participants, portfolios, performances, strict=True
        ):
            definition = definitions_by_id.get(participant.bot_id)
            bots.append(
                BotSummary(
                    str(participant.session_bot_id),
                    definition.name if definition else str(participant.bot_id),
                    definition.bot_type if definition else "Unknown",
                    definition.version if definition else None,
                    participant.status.value.upper(),
                    portfolio.portfolio_value if portfolio else None,
                    performance.percentage_return if performance else None,
                    performance.maximum_drawdown if performance else None,
                    performance.trade_count if performance else None,
                    performance.fees_paid if performance else None,
                )
            )
        trades = await self._research.recent_trades(selected.session_id)
        names = {
            participant.session_bot_id: (
                definitions_by_id[participant.bot_id].name
                if participant.bot_id in definitions_by_id
                else str(participant.bot_id)
            )
            for participant in participants
        }
        total_capital = sum(
            (item.portfolio_value for item in portfolios if item is not None), Decimal("0")
        )
        total_start = sum((item.starting_balance for item in participants), Decimal("0"))
        result.update(
            bots=tuple(bots),
            portfolio=PortfolioSummary(total_capital, total_capital - total_start),
            trades=tuple(
                TradeSummary(
                    item.executed_at,
                    names.get(item.session_bot_id, "Unknown"),
                    str(item.market),
                    item.side.value,
                    item.execution_price,
                    item.realized_pnl,
                )
                for item in trades
            ),
        )
        if participants:
            participant = participants[0]
            positions, decisions, history = await asyncio.gather(
                self._research.open_positions(participant.session_bot_id),
                self._research.decisions(participant.session_bot_id),
                self._research.portfolio_history(participant.session_bot_id),
            )
            result.update(
                positions=tuple(
                    PositionSummary(
                        str(item.market),
                        item.side,
                        item.quantity,
                        item.average_entry_price,
                        item.current_price,
                        item.unrealized_pnl,
                    )
                    for item in positions
                ),
                decisions=tuple(
                    DecisionSummary(
                        item.timestamp,
                        names.get(item.session_bot_id, "Unknown"),
                        str(item.market),
                        item.action.value,
                        item.requested_size,
                        item.confidence,
                        item.context.price,
                        item.context.portfolio_value,
                        str(item.executed_trade_id) if item.executed_trade_id else None,
                    )
                    for item in decisions
                ),
                portfolio_history=tuple((item.timestamp, item.portfolio_value) for item in history),
            )
        return result
