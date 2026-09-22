"""Bounded public market query adapter; it never exposes order capabilities."""

import asyncio
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, cast
from uuid import UUID

from data_collector.application.ports import NewsQueryPort
from data_collector.domain.entities import (
    MarketAssociation,
    NewsIntelligence,
    RetrospectiveImpact,
    SocialEvent,
    SocialIntelligence,
    SocialMarketImpact,
    SocialMarketReaction,
)
from data_operations.application.ports import OperationsRepository
from data_operations.application.readiness import ReadinessQueryService
from data_operations.domain.entities import OperationalInterval
from paper_trading.application.ports import ResearchQueryPort
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from shared.contracts import MarketSymbol

from dashboard.application.view_models import (
    BotSummary,
    ConnectionState,
    DashboardSnapshot,
    DataHealthSummary,
    DecisionSummary,
    ExperimentSummary,
    IntelligenceEvent,
    MarketSummary,
    MLModelSummary,
    MLResearchSummary,
    PortfolioSummary,
    PositionSummary,
    SessionSummary,
    TradeSummary,
)
from dashboard.market_catalog import MARKET_SYMBOLS

logger = logging.getLogger(__name__)


class DashboardNewsQueryPort(NewsQueryPort, Protocol):
    async def intelligence_for_event(self, news_event_id: UUID) -> tuple[NewsIntelligence, ...]: ...
    async def impact_for_event(self, news_event_id: UUID) -> tuple[RetrospectiveImpact, ...]: ...
    async def associations(self, news_event_id: UUID) -> tuple[MarketAssociation, ...]: ...


class DashboardSocialQueryPort(Protocol):
    async def recent_social(self, since: datetime, limit: int = 200) -> tuple[SocialEvent, ...]: ...
    async def social_intelligence_for_event(
        self, event_id: UUID
    ) -> tuple[SocialIntelligence, ...]: ...
    async def social_impacts(self, event_id: UUID) -> tuple[SocialMarketImpact, ...]: ...
    async def social_reactions(self, event_id: UUID) -> tuple[SocialMarketReaction, ...]: ...


class DashboardOperationsPort(Protocol):
    async def candle_timestamps(
        self, market: str, interval: str, start: datetime, end: datetime
    ) -> tuple[datetime, ...]: ...
    async def health_intervals(
        self, source: str, start: datetime, end: datetime
    ) -> tuple[OperationalInterval, ...]: ...
    async def table_counts(self) -> dict[str, int]: ...
    async def event_counts(
        self, source: str, asset: str, start: datetime, end: datetime
    ) -> tuple[int, int, datetime | None]: ...


class LiveDashboardRepository:
    """Thread-safe latest snapshot backed only by public Bitvavo reads."""

    def __init__(
        self,
        markets: tuple[str, ...] = MARKET_SYMBOLS,
        research: ResearchQueryPort | None = None,
        news: DashboardNewsQueryPort | None = None,
        social: DashboardSocialQueryPort | None = None,
        operations: DashboardOperationsPort | None = None,
    ) -> None:
        self._markets = markets
        self._research = research
        self._news = news
        self._social = social
        self._operations = operations
        initial = tuple(
            MarketSummary(market, state=ConnectionState.CONNECTING) for market in markets
        )
        self._snapshot = DashboardSnapshot(
            markets=initial,
            connections={
                "Bitvavo": ConnectionState.CONNECTING,
                "News": ConnectionState.CONNECTING if news else ConnectionState.DISABLED,
                "Social/X": ConnectionState.CONNECTING if social else ConnectionState.DISABLED,
                "PostgreSQL": ConnectionState.DISCONNECTED,
                "Redis": ConnectionState.DISCONNECTED,
            },
        )
        self._result_root = Path("experiments/results")
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
            social_values: dict[str, object] = {}
            if self._social:
                try:
                    social_values = {"social": asyncio.run(self._fetch_social())}
                    connections["Social/X"] = ConnectionState.CONNECTED
                except Exception:
                    logger.exception("dashboard_social_refresh_failed")
                    connections["Social/X"] = ConnectionState.ERROR
                    errors += ("Social database unavailable. Other data remains live.",)
            operations_values: dict[str, object] = {}
            if self._operations:
                try:
                    operations_values = {"data_health": asyncio.run(self._fetch_data_health())}
                except Exception:
                    logger.exception("dashboard_data_health_refresh_failed")
                    errors += ("Data Operations metrics unavailable.",)
            updated = replace(
                self.snapshot(),
                markets=markets,
                connections=connections,
                errors=errors,
                ml_research=self._load_ml_research(),
                **cast(Any, research_values),
                **cast(Any, news_values),
                **cast(Any, social_values),
                **cast(Any, operations_values),
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

    async def _fetch_data_health(self) -> DataHealthSummary:
        assert self._operations is not None
        from data_operations.application.gaps import MarketGapDetector
        from data_operations.domain.entities import HealthStatus

        end = datetime.now(UTC)
        start = end - timedelta(days=30)
        timestamps, news, social, counts, readiness = await asyncio.gather(
            self._operations.candle_timestamps("BTC-EUR", "1h", start, end),
            self._operations.health_intervals("news", start, end),
            self._operations.health_intervals("social", start, end),
            self._operations.table_counts(),
            ReadinessQueryService(cast(OperationsRepository, self._operations)).report(
                "BTC-EUR", "1h", start, end
            ),
        )
        gap = MarketGapDetector().detect(
            "BTC-EUR",
            "1h",
            start.replace(minute=0, second=0, microsecond=0),
            end.replace(minute=0, second=0, microsecond=0),
            timestamps,
        )
        total = (end - start).total_seconds()

        def uptime(intervals: tuple[OperationalInterval, ...]) -> float:
            seconds = sum(
                (x.end - x.start).total_seconds()
                for x in intervals
                if x.status is HealthStatus.HEALTHY
            )
            return seconds / total

        def bar(intervals: tuple[OperationalInterval, ...]) -> str:
            return "".join(
                "█" if x.status is HealthStatus.HEALTHY else "░" for x in intervals[-48:]
            )

        return DataHealthSummary(
            gap.coverage,
            len(gap.missing),
            uptime(news),
            uptime(social),
            tuple((group.feature_group, group.ready, group.reasons) for group in readiness.groups),
            counts,
            (("Market", "█" * min(48, gap.present)), ("News", bar(news)), ("Social", bar(social))),
        )

    def _load_ml_research(self) -> MLResearchSummary | None:
        paths = sorted(
            self._result_root.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        )
        if not paths:
            return None
        try:
            payload = json.loads(paths[0].read_text(encoding="utf-8"))
            dataset = payload["dataset"]
            models = tuple(
                MLModelSummary(
                    item["name"],
                    item["algorithm"],
                    item["feature_configuration"],
                    item["metrics"]["rmse"],
                    item["metrics"]["mae"],
                    item["metrics"]["pearson"],
                    item["metrics"]["r_squared"],
                    item["metrics"]["spearman"],
                    item["metrics"]["directional_accuracy"],
                    tuple(
                        sorted(
                            item.get("feature_importance", {}).items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:10]
                    ),
                    _downsample(tuple(float(x) for x in item.get("predictions", []))),
                    _downsample(tuple(float(x) for x in item.get("actuals", []))),
                )
                for item in payload.get("models", [])
            )
            validation = payload.get("validation") or {}
            first = payload.get("models", [{}])[0]
            return MLResearchSummary(
                payload["comparison_id"],
                dataset["dataset_id"],
                dataset["market"],
                dataset["interval"],
                dataset["target_version"],
                datetime.fromisoformat(dataset["start_time"]),
                datetime.fromisoformat(dataset["end_time"]),
                validation.get("row_count"),
                validation.get("news_coverage"),
                validation.get("social_coverage"),
                _date_period(first.get("training_period")),
                _date_period(first.get("validation_period")),
                _date_period(first.get("test_period")),
                models,
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.exception("dashboard_ml_research_load_failed")
            return None

    async def _fetch_social(self) -> tuple[IntelligenceEvent, ...]:
        assert self._social is not None
        events = await self._social.recent_social(datetime.now(UTC) - timedelta(hours=24))
        output = []
        for event in events:
            intelligence, impacts, reactions = await asyncio.gather(
                self._social.social_intelligence_for_event(event.social_event_id),
                self._social.social_impacts(event.social_event_id),
                self._social.social_reactions(event.social_event_id),
            )
            impact_by_asset = {x.asset: x for x in impacts}
            for value in intelligence:
                impact = impact_by_asset.get(value.asset)
                available = len(impact.available_windows) if impact else 0
                total = available + len(impact.pending_windows) if impact else 0
                asset_reactions = tuple(
                    (x.window_minutes, x.price_return)
                    for x in reactions
                    if x.market.startswith(f"{value.asset}-")
                )
                output.append(
                    IntelligenceEvent(
                        str(event.social_event_id),
                        "social",
                        event.received_at,
                        event.text,
                        event.username,
                        (value.asset,),
                        value.sentiment,
                        value.relevance,
                        value.importance,
                        impact.score if impact else None,
                        value.account_influence,
                        value.novelty,
                        value.event_type.value,
                        event.created_at,
                        value.processed_at,
                        value.sentiment_confidence,
                        value.event_confidence,
                        f"{available}/{total} windows" if impact else "Pending",
                        asset_reactions,
                        value.explanation.get("importance", ()),
                    )
                )
        return tuple(output)

    async def _fetch_news(self) -> tuple[IntelligenceEvent, ...]:
        assert self._news is not None
        events = await self._news.recent_news(since=datetime.now(UTC) - timedelta(hours=24))
        output = []
        for item in events:
            intelligence, impacts, reactions = await asyncio.gather(
                self._news.intelligence_for_event(item.news_event_id),
                self._news.impact_for_event(item.news_event_id),
                self._news.associations(item.news_event_id),
            )
            impacts_by_asset = {value.asset: value for value in impacts}
            for value in intelligence:
                impact = impacts_by_asset.get(value.asset)
                available = len(impact.available_windows) if impact else 0
                total = available + len(impact.pending_windows) if impact else 0
                output.append(
                    IntelligenceEvent(
                        event_id=str(item.news_event_id),
                        kind="news",
                        occurred_at=item.received_at,
                        title=item.title,
                        source=item.source_name,
                        assets=(value.asset,),
                        sentiment=value.sentiment,
                        relevance=value.relevance,
                        importance=value.importance,
                        estimated_impact=impact.score if impact else None,
                        novelty=value.novelty,
                        event_type=value.event_type.value,
                        published_at=item.published_at,
                        processed_at=value.processed_at,
                        sentiment_confidence=value.sentiment_confidence,
                        event_confidence=value.event_confidence,
                        impact_maturity=f"{available}/{total} windows" if impact else "Pending",
                        reactions=tuple(
                            (reaction.window_minutes, reaction.price_return)
                            for reaction in reactions
                            if reaction.market.startswith(f"{value.asset}-")
                        ),
                        explanation=value.explanation.get("importance", ()),
                    )
                )
        return tuple(output)

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


def _date_period(value: object) -> tuple[datetime, datetime] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    return datetime.fromisoformat(str(value[0])), datetime.fromisoformat(str(value[1]))


def _downsample(values: tuple[float, ...], limit: int = 1_000) -> tuple[float, ...]:
    if len(values) <= limit:
        return values
    step = max(1, len(values) // limit)
    return values[::step][:limit]
