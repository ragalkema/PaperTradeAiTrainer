"""Async SQLAlchemy adapter for immutable raw and normalized news queries."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import overload
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from data_collector.domain.entities import (
    MarketAssociation,
    NewsEvent,
    NewsSource,
    NewsSourceKind,
    RawNewsItem,
    RawNewsStatus,
    SourceHealth,
)
from data_collector.infrastructure.persistence.models import (
    NewsEventModel,
    NewsMarketAssociationModel,
    NewsSourceModel,
    RawNewsItemModel,
)


class SqlAlchemyNewsRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def register_source(self, source: NewsSource) -> None:
        async with self._sessions.begin() as session:
            existing = await session.get(NewsSourceModel, source.source_id)
            if existing is None:
                session.add(NewsSourceModel(**_source_values(source)))
            else:
                existing.name = source.name
                existing.kind = source.kind.value
                existing.enabled = source.enabled
                existing.priority = source.priority
                existing.poll_interval_seconds = source.poll_interval_seconds
                existing.feed_url = source.feed_url

    async def update_source_health(self, source_id: str, health: SourceHealth) -> None:
        now = datetime.now(UTC)
        values: dict[str, object] = {"health": health.value}
        values["last_success" if health is SourceHealth.HEALTHY else "last_failure"] = now
        async with self._sessions.begin() as session:
            await session.execute(
                update(NewsSourceModel)
                .where(NewsSourceModel.source_id == source_id)
                .values(**values)
            )

    async def add_raw(self, item: RawNewsItem) -> bool:
        try:
            async with self._sessions.begin() as session:
                session.add(RawNewsItemModel(**_raw_values(item)))
        except IntegrityError:
            return False
        return True

    async def set_raw_status(
        self, raw_item_id: UUID, status: RawNewsStatus, reason: str | None = None
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(RawNewsItemModel)
                .where(RawNewsItemModel.raw_item_id == raw_item_id)
                .values(status=status.value, quarantine_reason=reason)
            )

    async def add_event(self, event: NewsEvent) -> bool:
        try:
            async with self._sessions.begin() as session:
                session.add(NewsEventModel(**_event_values(event)))
        except IntegrityError:
            return False
        return True

    async def add_association(self, value: MarketAssociation) -> None:
        async with self._sessions.begin() as session:
            session.add(NewsMarketAssociationModel(**_association_values(value)))

    async def recent_news(
        self, *, since: datetime, asset: str | None = None, limit: int = 200
    ) -> tuple[NewsEvent, ...]:
        if since.tzinfo is None:
            raise ValueError("since must be timezone-aware")
        _limit(limit)
        fetch_limit = min(limit * 10, 2_000) if asset else limit
        query = (
            select(NewsEventModel)
            .where(NewsEventModel.received_at >= since)
            .order_by(desc(NewsEventModel.received_at), NewsEventModel.news_event_id)
            .limit(fetch_limit)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        events = tuple(_to_event(item) for item in rows)
        if asset:
            asset_name = asset.upper()
            events = tuple(item for item in events if asset_name in item.mentioned_assets)
        return events[:limit]

    async def event(self, news_event_id: UUID) -> NewsEvent | None:
        async with self._sessions() as session:
            item = await session.get(NewsEventModel, news_event_id)
        return _to_event(item) if item else None

    async def associations(self, news_event_id: UUID) -> tuple[MarketAssociation, ...]:
        query = (
            select(NewsMarketAssociationModel)
            .where(NewsMarketAssociationModel.news_event_id == news_event_id)
            .order_by(NewsMarketAssociationModel.market, NewsMarketAssociationModel.window_minutes)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_association(item) for item in rows)

    async def sources(self) -> tuple[NewsSource, ...]:
        query = select(NewsSourceModel).order_by(desc(NewsSourceModel.priority))
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_source(item) for item in rows)


def _limit(value: int) -> None:
    if not 1 <= value <= 1_000:
        raise ValueError("limit must be between 1 and 1000")


def _source_values(value: NewsSource) -> dict[str, object]:
    return {
        "source_id": value.source_id,
        "name": value.name,
        "kind": value.kind.value,
        "enabled": value.enabled,
        "priority": value.priority,
        "poll_interval_seconds": value.poll_interval_seconds,
        "feed_url": value.feed_url,
        "health": value.health.value,
        "last_success": value.last_success,
        "last_failure": value.last_failure,
    }


def _raw_values(value: RawNewsItem) -> dict[str, object]:
    return {
        "raw_item_id": value.raw_item_id,
        "source_id": value.source_id,
        "external_id": value.external_id,
        "title": value.title,
        "summary": value.summary,
        "url": value.url,
        "author": value.author,
        "published_at": value.published_at,
        "received_at": value.received_at,
        "content_hash": value.content_hash,
        "raw_metadata": value.raw_metadata,
        "version": value.version,
        "status": value.status.value,
        "quarantine_reason": value.quarantine_reason,
    }


def _event_values(value: NewsEvent) -> dict[str, object]:
    return {
        "news_event_id": value.news_event_id,
        "raw_item_id": value.raw_item_id,
        "source_id": value.source_id,
        "source_name": value.source_name,
        "title": value.title,
        "summary": value.summary,
        "url": value.url,
        "author": value.author,
        "published_at": value.published_at,
        "received_at": value.received_at,
        "processed_at": value.processed_at,
        "mentioned_assets": list(value.mentioned_assets),
        "asset_relevance": {key: str(item) for key, item in value.asset_relevance.items()},
        "importance": value.importance,
        "sentiment": value.sentiment,
        "language": value.language,
        "duplicate_group_id": value.duplicate_group_id,
        "story_cluster_id": value.story_cluster_id,
    }


def _association_values(value: MarketAssociation) -> dict[str, object]:
    return {
        "association_id": value.association_id,
        "news_event_id": value.news_event_id,
        "market": value.market,
        "window_minutes": value.window_minutes,
        "event_price": value.event_price,
        "post_event_price": value.post_event_price,
        "price_return": value.price_return,
        "volume_before": value.volume_before,
        "volume_after": value.volume_after,
        "observed_at": value.observed_at,
    }


def _to_source(item: NewsSourceModel) -> NewsSource:
    return NewsSource(
        item.source_id,
        item.name,
        NewsSourceKind(item.kind),
        item.enabled,
        item.priority,
        item.poll_interval_seconds,
        item.feed_url,
        SourceHealth(item.health),
        _utc(item.last_success),
        _utc(item.last_failure),
    )


def _to_event(item: NewsEventModel) -> NewsEvent:
    return NewsEvent(
        item.news_event_id,
        item.raw_item_id,
        item.source_id,
        item.source_name,
        item.title,
        item.url,
        _utc(item.published_at),
        _utc(item.received_at),
        _utc(item.processed_at),
        tuple(item.mentioned_assets),
        {key: Decimal(value) for key, value in item.asset_relevance.items()},
        item.language,
        item.summary,
        item.author,
        item.importance,
        item.sentiment,
        item.duplicate_group_id,
        item.story_cluster_id,
    )


def _to_association(item: NewsMarketAssociationModel) -> MarketAssociation:
    return MarketAssociation(
        item.association_id,
        item.news_event_id,
        item.market,
        item.window_minutes,
        item.event_price,
        item.post_event_price,
        item.price_return,
        _utc(item.observed_at),
        item.volume_before,
        item.volume_after,
    )


@overload
def _utc(value: datetime) -> datetime: ...


@overload
def _utc(value: None) -> None: ...


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
