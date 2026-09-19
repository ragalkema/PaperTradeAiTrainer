"""Idempotent SQLAlchemy operations repository."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from data_collector.infrastructure.persistence.models import (
    NewsEventModel,
    NewsFeatureSnapshotModel,
    RawNewsItemModel,
    RawSocialPostModel,
    SocialEngagementSnapshotModel,
    SocialEventModel,
    SocialFeatureSnapshotModel,
)
from data_operations.domain.entities import (
    CollectionCheckpoint,
    CollectorHealthObservation,
    CoverageLimitation,
    DatasetManifest,
    HealthStatus,
    OperationalInterval,
)
from data_operations.infrastructure.models import (
    CollectionCheckpointModel,
    CollectorHealthModel,
    CoverageLimitationModel,
    DatasetManifestModel,
    MarketCandleModel,
    OperationsBase,
)
from shared.contracts import Candle, MarketSymbol
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyOperationsRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save_candles(self, candles: Sequence[Candle]) -> int:
        inserted = 0
        async with self._sessions.begin() as session:
            for candle in candles:
                values = {
                    "market": str(candle.market),
                    "interval": candle.interval,
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "received_at": datetime.now(UTC),
                }
                if session.bind and session.bind.dialect.name == "postgresql":
                    statement: Any = (
                        postgres_insert(MarketCandleModel)
                        .values(**values)
                        .on_conflict_do_nothing(index_elements=["market", "interval", "timestamp"])
                    )
                    result = await session.execute(statement.returning(MarketCandleModel.timestamp))
                    inserted += int(result.scalar_one_or_none() is not None)
                elif (
                    await session.get(
                        MarketCandleModel,
                        (values["market"], values["interval"], values["timestamp"]),
                    )
                    is None
                ):
                    session.add(MarketCandleModel(**values))
                    inserted += 1
        return inserted

    async def candle_timestamps(
        self, market: str, interval: str, start: datetime, end: datetime
    ) -> tuple[datetime, ...]:
        query = (
            select(MarketCandleModel.timestamp)
            .where(
                MarketCandleModel.market == market,
                MarketCandleModel.interval == interval,
                MarketCandleModel.timestamp >= start,
                MarketCandleModel.timestamp < end,
            )
            .order_by(MarketCandleModel.timestamp)
        )
        async with self._sessions() as session:
            values = tuple((await session.scalars(query)).all())
        return tuple(_utc(x) for x in values)

    async def candles(
        self, market: str, interval: str, start: datetime, end: datetime
    ) -> tuple[Candle, ...]:
        query = (
            select(MarketCandleModel)
            .where(
                MarketCandleModel.market == market,
                MarketCandleModel.interval == interval,
                MarketCandleModel.timestamp >= start,
                MarketCandleModel.timestamp < end,
            )
            .order_by(MarketCandleModel.timestamp)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(
            Candle(
                MarketSymbol(x.market),
                x.interval,
                _utc(x.timestamp),
                x.open,
                x.high,
                x.low,
                x.close,
                x.volume,
            )
            for x in rows
        )

    async def save_health(self, value: CollectorHealthObservation) -> None:
        async with self._sessions.begin() as session:
            existing = await session.get(CollectorHealthModel, (value.source, value.timestamp))
            if existing is None:
                values = asdict(value)
                values["status"] = value.status.value
                session.add(CollectorHealthModel(**values))

    async def health_intervals(
        self, source: str, start: datetime, end: datetime
    ) -> tuple[OperationalInterval, ...]:
        prior_query = (
            select(CollectorHealthModel)
            .where(
                CollectorHealthModel.source == source,
                CollectorHealthModel.timestamp < start,
            )
            .order_by(CollectorHealthModel.timestamp.desc())
            .limit(1)
        )
        range_query = (
            select(CollectorHealthModel)
            .where(
                CollectorHealthModel.source == source,
                CollectorHealthModel.timestamp >= start,
                CollectorHealthModel.timestamp < end,
            )
            .order_by(CollectorHealthModel.timestamp)
        )
        async with self._sessions() as session:
            prior = (await session.scalars(prior_query)).first()
            rows = tuple((await session.scalars(range_query)).all())
        if prior is not None:
            rows = (prior, *rows)
        result = []
        for index, row in enumerate(rows):
            finish = min(end, _utc(rows[index + 1].timestamp)) if index + 1 < len(rows) else end
            result.append(
                OperationalInterval(
                    source, max(start, _utc(row.timestamp)), finish, HealthStatus(row.status)
                )
            )
        return tuple(result)

    async def save_checkpoint(self, value: CollectionCheckpoint) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(CollectionCheckpointModel, value.source)
            values = asdict(value)
            if row is None:
                session.add(CollectionCheckpointModel(**values))
            else:
                for key, item in values.items():
                    setattr(row, key, item)

    async def checkpoint(self, source: str) -> CollectionCheckpoint | None:
        async with self._sessions() as session:
            row = await session.get(CollectionCheckpointModel, source)
        return (
            CollectionCheckpoint(
                row.source,
                _utc_optional(row.last_successful_event_time),
                _utc(row.last_poll_time),
                row.external_cursor,
                row.last_processed_event,
            )
            if row
            else None
        )

    async def save_manifest(self, value: DatasetManifest) -> None:
        async with self._sessions.begin() as session:
            if await session.get(DatasetManifestModel, value.manifest_id) is None:
                values = asdict(value)
                values["analyzer_versions"] = list(value.analyzer_versions)
                session.add(DatasetManifestModel(**values))

    async def save_coverage_limitation(self, value: CoverageLimitation) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(CoverageLimitationModel, value.source)
            values = asdict(value)
            if row is None:
                session.add(CoverageLimitationModel(**values))
            else:
                for key, item in values.items():
                    if key in {"first_known_complete_time", "unavailable_before"}:
                        continue
                    setattr(row, key, item)

    async def table_counts(self) -> dict[str, int]:
        output = {}
        async with self._sessions() as session:
            for table in OperationsBase.metadata.sorted_tables:
                output[table.name] = int(
                    (await session.scalar(select(func.count()).select_from(table))) or 0
                )
            for model in (
                RawNewsItemModel,
                NewsEventModel,
                RawSocialPostModel,
                SocialEventModel,
                SocialEngagementSnapshotModel,
                NewsFeatureSnapshotModel,
                SocialFeatureSnapshotModel,
            ):
                try:
                    output[model.__tablename__] = int(
                        (await session.scalar(select(func.count()).select_from(model))) or 0
                    )
                except Exception:
                    await session.rollback()
        return output

    async def event_counts(
        self, source: str, asset: str, start: datetime, end: datetime
    ) -> tuple[int, int, datetime | None]:
        model: Any = NewsEventModel if source == "news" else SocialEventModel
        query = (
            select(model)
            .where(model.received_at >= start, model.received_at < end)
            .order_by(model.received_at)
        )
        async with self._sessions() as session:
            try:
                rows = tuple((await session.scalars(query)).all())
            except Exception:
                return 0, 0, None
        return (
            len(rows),
            sum(asset in row.mentioned_assets for row in rows),
            _utc(rows[0].received_at) if rows else None,
        )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _utc_optional(value: datetime | None) -> datetime | None:
    return _utc(value) if value else None
