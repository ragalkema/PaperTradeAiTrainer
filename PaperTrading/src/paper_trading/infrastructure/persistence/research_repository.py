"""Async PostgreSQL repository implementing PaperTrading application ports."""

from dataclasses import fields
from datetime import UTC, datetime
from typing import Any, overload
from uuid import UUID

from shared.contracts import ActionType, MarketSymbol
from sqlalchemy import Select, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from paper_trading.application.services.performance import PerformanceMetricsService
from paper_trading.domain.entities import (
    BotDecisionRecord,
    BotDefinitionRecord,
    BotStatus,
    DecisionContextRecord,
    ExperimentRecord,
    ExperimentStatus,
    PaperSessionRecord,
    PaperTradeRecord,
    PerformanceReport,
    PortfolioSnapshotRecord,
    PositionRecord,
    PositionStatus,
    SessionBotRecord,
    SessionStatus,
)
from paper_trading.infrastructure.persistence.models import (
    BotDecisionModel,
    BotDefinitionModel,
    ExperimentModel,
    PaperSessionModel,
    PaperTradeModel,
    PortfolioSnapshotModel,
    PositionModel,
    SessionBotModel,
)


class SqlAlchemyResearchRepository:
    """One transaction per command/query with bounded chronological result sets."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def _add(self, model: object) -> None:
        async with self._sessions.begin() as session:
            session.add(model)

    async def add_session(self, value: PaperSessionRecord) -> None:
        await self._add(PaperSessionModel(**_session_values(value)))

    async def add_bot_definition(self, value: BotDefinitionRecord) -> None:
        async with self._sessions.begin() as session:
            await session.merge(BotDefinitionModel(**_bot_values(value)))

    async def add_session_bot(self, value: SessionBotRecord) -> None:
        await self._add(SessionBotModel(**_session_bot_values(value)))

    async def add_snapshot(self, value: PortfolioSnapshotRecord) -> None:
        await self._add(PortfolioSnapshotModel(**_snapshot_values(value)))

    async def add_position(self, value: PositionRecord) -> None:
        await self._add(PositionModel(**_position_values(value)))

    async def add_trade(self, value: PaperTradeRecord) -> None:
        await self._add(PaperTradeModel(**_trade_values(value)))

    async def add_decision(self, value: BotDecisionRecord) -> None:
        await self._add(BotDecisionModel(**_decision_values(value)))

    async def add_experiment(self, value: ExperimentRecord) -> None:
        await self._add(ExperimentModel(**_experiment_values(value)))

    async def set_session_status(
        self, session_id: UUID, status: SessionStatus, ended_at: datetime | None = None
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(PaperSessionModel)
                .where(PaperSessionModel.session_id == session_id)
                .values(status=status.value, ended_at=ended_at)
            )

    async def set_experiment_status(
        self,
        experiment_id: UUID,
        status: ExperimentStatus,
        ended_at: datetime | None = None,
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(ExperimentModel)
                .where(ExperimentModel.experiment_id == experiment_id)
                .values(status=status.value, ended_at=ended_at)
            )

    async def _scalars(self, query: Select[tuple[Any]]) -> tuple[Any, ...]:
        async with self._sessions() as session:
            return tuple((await session.scalars(query)).all())

    async def active_sessions(self, limit: int = 50) -> tuple[PaperSessionRecord, ...]:
        _valid_limit(limit)
        query = (
            select(PaperSessionModel)
            .where(PaperSessionModel.status.in_(["created", "running", "paused"]))
            .order_by(desc(PaperSessionModel.created_at))
            .limit(limit)
        )
        return tuple(_to_session(item) for item in await self._scalars(query))

    async def session(self, session_id: UUID) -> PaperSessionRecord | None:
        async with self._sessions() as session:
            item = await session.get(PaperSessionModel, session_id)
        return _to_session(item) if item else None

    async def session_bots(self, session_id: UUID) -> tuple[SessionBotRecord, ...]:
        query = select(SessionBotModel).where(SessionBotModel.session_id == session_id)
        return tuple(_to_session_bot(item) for item in await self._scalars(query))

    async def bot_definitions(self, bot_ids: tuple[UUID, ...]) -> tuple[BotDefinitionRecord, ...]:
        if not bot_ids:
            return ()
        query = select(BotDefinitionModel).where(BotDefinitionModel.bot_id.in_(bot_ids))
        return tuple(_to_bot(item) for item in await self._scalars(query))

    async def current_portfolio(self, session_bot_id: UUID) -> PortfolioSnapshotRecord | None:
        query = (
            select(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.session_bot_id == session_bot_id)
            .order_by(desc(PortfolioSnapshotModel.timestamp))
            .limit(1)
        )
        rows = await self._scalars(query)
        return _to_snapshot(rows[0]) if rows else None

    async def portfolio_history(
        self, session_bot_id: UUID, start: datetime | None = None, limit: int = 2_000
    ) -> tuple[PortfolioSnapshotRecord, ...]:
        _valid_limit(limit, 10_000)
        query = select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.session_bot_id == session_bot_id
        )
        if start is not None:
            query = query.where(PortfolioSnapshotModel.timestamp >= start)
        query = query.order_by(PortfolioSnapshotModel.timestamp).limit(limit)
        return tuple(_to_snapshot(item) for item in await self._scalars(query))

    async def open_positions(self, session_bot_id: UUID) -> tuple[PositionRecord, ...]:
        query = (
            select(PositionModel)
            .where(
                PositionModel.session_bot_id == session_bot_id,
                PositionModel.status == "open",
            )
            .order_by(desc(PositionModel.recorded_at))
            .limit(2_000)
        )
        newest: dict[str, PositionRecord] = {}
        for item in await self._scalars(query):
            record = _to_position(item)
            newest.setdefault(str(record.market), record)
        return tuple(newest.values())

    async def recent_trades(
        self, session_id: UUID | None = None, limit: int = 200
    ) -> tuple[PaperTradeRecord, ...]:
        _valid_limit(limit, 5_000)
        query = select(PaperTradeModel)
        if session_id is not None:
            query = query.where(PaperTradeModel.session_id == session_id)
        query = query.order_by(desc(PaperTradeModel.executed_at)).limit(limit)
        return tuple(_to_trade(item) for item in await self._scalars(query))

    async def decisions(
        self, session_bot_id: UUID, limit: int = 500
    ) -> tuple[BotDecisionRecord, ...]:
        _valid_limit(limit, 5_000)
        query = (
            select(BotDecisionModel)
            .where(BotDecisionModel.session_bot_id == session_bot_id)
            .order_by(desc(BotDecisionModel.timestamp))
            .limit(limit)
        )
        return tuple(_to_decision(item) for item in await self._scalars(query))

    async def experiments(self, limit: int = 100) -> tuple[ExperimentRecord, ...]:
        _valid_limit(limit)
        query = select(ExperimentModel).order_by(desc(ExperimentModel.created_at)).limit(limit)
        return tuple(_to_experiment(item) for item in await self._scalars(query))

    async def experiment(self, experiment_id: UUID) -> ExperimentRecord | None:
        async with self._sessions() as session:
            item = await session.get(ExperimentModel, experiment_id)
        return _to_experiment(item) if item else None

    async def performance(self, session_bot_id: UUID) -> PerformanceReport | None:
        async with self._sessions() as session:
            participant = await session.get(SessionBotModel, session_bot_id)
        if participant is None:
            return None
        snapshots = await self.portfolio_history(session_bot_id, limit=10_000)
        query = (
            select(PaperTradeModel)
            .where(PaperTradeModel.session_bot_id == session_bot_id)
            .order_by(PaperTradeModel.executed_at)
            .limit(10_000)
        )
        trades = tuple(_to_trade(item) for item in await self._scalars(query))
        return PerformanceMetricsService.calculate(snapshots, trades, participant.starting_balance)


def _valid_limit(value: int, maximum: int = 2_000) -> None:
    if not 1 <= value <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")


def _session_values(value: PaperSessionRecord) -> dict[str, object]:
    result = _field_values(value)
    result.update(markets=[str(item) for item in value.markets], status=value.status.value)
    return result


def _bot_values(value: BotDefinitionRecord) -> dict[str, object]:
    return _field_values(value)


def _session_bot_values(value: SessionBotRecord) -> dict[str, object]:
    result = _field_values(value)
    result["status"] = value.status.value
    return result


def _snapshot_values(value: PortfolioSnapshotRecord) -> dict[str, object]:
    return _field_values(value)


def _position_values(value: PositionRecord) -> dict[str, object]:
    result = _field_values(value)
    result.update(market=str(value.market), status=value.status.value)
    return result


def _trade_values(value: PaperTradeRecord) -> dict[str, object]:
    result = _field_values(value)
    result.update(market=str(value.market), side=value.side.value)
    return result


def _decision_values(value: BotDecisionRecord) -> dict[str, object]:
    context = value.context
    return {
        "decision_id": value.decision_id,
        "session_id": value.session_id,
        "session_bot_id": value.session_bot_id,
        "timestamp": value.timestamp,
        "market": str(value.market),
        "action": value.action.value,
        "requested_size": value.requested_size,
        "confidence": value.confidence,
        "explanation_reference": value.explanation_reference,
        "executed_trade_id": value.executed_trade_id,
        **_field_values(context),
    }


def _experiment_values(value: ExperimentRecord) -> dict[str, object]:
    result = _field_values(value)
    result.update(markets=[str(item) for item in value.markets], status=value.status.value)
    return result


def _field_values(value: object) -> dict[str, object]:
    return {item.name: getattr(value, item.name) for item in fields(value)}  # type: ignore[arg-type]


def _to_session(item: PaperSessionModel) -> PaperSessionRecord:
    return PaperSessionRecord(
        item.session_id,
        item.name,
        _utc(item.created_at),
        SessionStatus(item.status),
        item.starting_balance,
        tuple(MarketSymbol(v) for v in item.markets),
        item.fee_rate,
        item.slippage_rate,
        item.mode,
        _utc(item.started_at),
        _utc(item.ended_at),
        item.experiment_id,
    )


def _to_bot(item: BotDefinitionModel) -> BotDefinitionRecord:
    return BotDefinitionRecord(
        item.bot_id, item.name, item.bot_type, item.version, item.configuration
    )


def _to_session_bot(item: SessionBotModel) -> SessionBotRecord:
    return SessionBotRecord(
        item.session_bot_id,
        item.session_id,
        item.bot_id,
        item.starting_balance,
        BotStatus(item.status),
        _utc(item.created_at),
        item.participant_configuration,
    )


def _to_snapshot(item: PortfolioSnapshotModel) -> PortfolioSnapshotRecord:
    return PortfolioSnapshotRecord(
        item.snapshot_id,
        item.session_bot_id,
        _utc(item.timestamp),
        item.cash,
        item.asset_value,
        item.portfolio_value,
        item.realized_pnl,
        item.unrealized_pnl,
        item.fees_paid,
    )


def _to_position(item: PositionModel) -> PositionRecord:
    return PositionRecord(
        item.position_id,
        item.session_bot_id,
        _utc(item.recorded_at),
        MarketSymbol(item.market),
        item.side,
        item.quantity,
        item.average_entry_price,
        item.current_price,
        item.realized_pnl,
        item.unrealized_pnl,
        _utc(item.opened_at),
        PositionStatus(item.status),
        _utc(item.closed_at),
    )


def _to_trade(item: PaperTradeModel) -> PaperTradeRecord:
    return PaperTradeRecord(
        item.trade_id,
        item.session_id,
        item.session_bot_id,
        MarketSymbol(item.market),
        ActionType(item.side),
        item.requested_quantity,
        item.executed_quantity,
        item.market_price,
        item.execution_price,
        item.gross_value,
        item.fee,
        item.slippage_cost,
        item.realized_pnl,
        _utc(item.executed_at),
    )


def _to_decision(item: BotDecisionModel) -> BotDecisionRecord:
    context = DecisionContextRecord(
        _utc(item.market_timestamp),
        item.price,
        item.bid,
        item.ask,
        item.spread,
        item.portfolio_value,
        item.cash,
        item.position_quantity,
        item.feature_snapshot_reference,
        item.news_snapshot_reference,
        item.social_snapshot_reference,
    )
    return BotDecisionRecord(
        item.decision_id,
        item.session_id,
        item.session_bot_id,
        _utc(item.timestamp),
        MarketSymbol(item.market),
        ActionType(item.action),
        item.requested_size,
        context,
        item.confidence,
        item.explanation_reference,
        item.executed_trade_id,
    )


def _to_experiment(item: ExperimentModel) -> ExperimentRecord:
    return ExperimentRecord(
        item.experiment_id,
        item.name,
        item.description,
        _utc(item.created_at),
        ExperimentStatus(item.status),
        tuple(MarketSymbol(v) for v in item.markets),
        _utc(item.start_period),
        _utc(item.end_period),
        item.starting_balance,
        item.fee_rate,
        item.slippage_rate,
        item.random_seed,
        item.dataset_version,
        item.feature_version,
        item.git_commit,
        _utc(item.started_at),
        _utc(item.ended_at),
    )


@overload
def _utc(value: datetime) -> datetime: ...


@overload
def _utc(value: None) -> None: ...


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
