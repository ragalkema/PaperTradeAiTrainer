"""Async SQLAlchemy adapter for immutable raw and normalized news queries."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import overload
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import and_, desc, exists, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from data_collector.domain.entities import (
    MarketAssociation,
    NewsEvent,
    NewsEventType,
    NewsFeatureSnapshot,
    NewsIntelligence,
    NewsSource,
    NewsSourceKind,
    OnlineNewsItem,
    RawNewsItem,
    RawNewsStatus,
    RetrospectiveImpact,
    SourceHealth,
)
from data_collector.infrastructure.persistence.models import (
    NewsEventModel,
    NewsFeatureSnapshotModel,
    NewsIntelligenceModel,
    NewsMarketAssociationModel,
    NewsMarketImpactModel,
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

    async def unanalyzed_events(self, limit: int = 200) -> tuple[NewsEvent, ...]:
        _limit(limit)
        query = (
            select(NewsEventModel)
            .where(
                func.json_array_length(NewsEventModel.mentioned_assets) > 0,
                ~exists().where(
                    NewsIntelligenceModel.news_event_id == NewsEventModel.news_event_id
                ),
            )
            .order_by(NewsEventModel.received_at, NewsEventModel.news_event_id)
            .limit(limit)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_event(item) for item in rows)

    async def prior_events(
        self, received_before: datetime, lookback: timedelta
    ) -> tuple[NewsEvent, ...]:
        query = (
            select(NewsEventModel)
            .where(
                and_(
                    NewsEventModel.received_at < received_before,
                    NewsEventModel.received_at >= received_before - lookback,
                )
            )
            .order_by(NewsEventModel.received_at)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_event(item) for item in rows)

    async def set_story_cluster(self, news_event_id: UUID, story_cluster_id: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(NewsEventModel)
                .where(NewsEventModel.news_event_id == news_event_id)
                .values(story_cluster_id=story_cluster_id)
            )

    async def add_intelligence(self, value: NewsIntelligence) -> bool:
        try:
            async with self._sessions.begin() as session:
                session.add(NewsIntelligenceModel(**_intelligence_values(value)))
        except IntegrityError:
            return False
        return True

    async def intelligence_for_event(self, news_event_id: UUID) -> tuple[NewsIntelligence, ...]:
        query = (
            select(NewsIntelligenceModel)
            .where(NewsIntelligenceModel.news_event_id == news_event_id)
            .order_by(NewsIntelligenceModel.asset)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_intelligence(item) for item in rows)

    async def get_news_available_at(
        self, market: str, decision_time: datetime, lookback: timedelta
    ) -> tuple[OnlineNewsItem, ...]:
        if decision_time.tzinfo is None:
            raise ValueError("decision_time must be timezone-aware")
        asset = market.split("-", 1)[0].upper()
        query = (
            select(NewsEventModel, NewsIntelligenceModel)
            .join(
                NewsIntelligenceModel,
                NewsIntelligenceModel.news_event_id == NewsEventModel.news_event_id,
            )
            .where(
                and_(
                    NewsIntelligenceModel.asset == asset,
                    NewsEventModel.received_at <= decision_time,
                    NewsEventModel.received_at >= decision_time - lookback,
                    NewsEventModel.processed_at <= decision_time,
                    NewsIntelligenceModel.processed_at <= decision_time,
                )
            )
            .order_by(NewsEventModel.received_at)
        )
        async with self._sessions() as session:
            rows = tuple((await session.execute(query)).all())
        return tuple(
            OnlineNewsItem(_to_event(event), _to_intelligence(value)) for event, value in rows
        )

    async def add_feature_snapshot(self, value: NewsFeatureSnapshot) -> None:
        values = _feature_values(value)
        async with self._sessions.begin() as session:
            existing = await session.get(NewsFeatureSnapshotModel, values["snapshot_id"])
            if existing is None:
                session.add(NewsFeatureSnapshotModel(**values))

    async def feature_snapshots(
        self, market: str, start: datetime, end: datetime
    ) -> tuple[NewsFeatureSnapshot, ...]:
        """Load a whole research interval in one query; never query once per decision row."""
        query = (
            select(NewsFeatureSnapshotModel)
            .where(
                and_(
                    NewsFeatureSnapshotModel.market == market,
                    NewsFeatureSnapshotModel.feature_time >= start,
                    NewsFeatureSnapshotModel.feature_time <= end,
                )
            )
            .order_by(NewsFeatureSnapshotModel.feature_time)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_feature_snapshot(row) for row in rows)

    async def upsert_impact(self, value: RetrospectiveImpact) -> None:
        async with self._sessions.begin() as session:
            existing = await session.get(NewsMarketImpactModel, (value.news_event_id, value.asset))
            values = _impact_values(value)
            if existing is None:
                session.add(NewsMarketImpactModel(**values))
            else:
                for key, item in values.items():
                    setattr(existing, key, item)

    async def impact_for_event(self, news_event_id: UUID) -> tuple[RetrospectiveImpact, ...]:
        query = (
            select(NewsMarketImpactModel)
            .where(NewsMarketImpactModel.news_event_id == news_event_id)
            .order_by(NewsMarketImpactModel.asset)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_impact(item) for item in rows)

    async def top_impact(self, since: datetime, limit: int = 5) -> tuple[RetrospectiveImpact, ...]:
        query = (
            select(NewsMarketImpactModel)
            .join(NewsEventModel)
            .where(NewsEventModel.received_at >= since)
            .order_by(desc(NewsMarketImpactModel.score))
            .limit(limit)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_to_impact(item) for item in rows)


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


def _intelligence_values(value: NewsIntelligence) -> dict[str, object]:
    return {
        "intelligence_id": value.intelligence_id,
        "news_event_id": value.news_event_id,
        "asset": value.asset,
        "relevance": value.relevance,
        "sentiment": value.sentiment,
        "sentiment_confidence": value.sentiment_confidence,
        "importance": value.importance,
        "importance_confidence": value.importance_confidence,
        "event_type": value.event_type.value,
        "event_confidence": value.event_confidence,
        "secondary_tags": [item.value for item in value.secondary_tags],
        "novelty": value.novelty,
        "novelty_confidence": value.novelty_confidence,
        "story_cluster_id": value.story_cluster_id,
        "sentiment_version": value.sentiment_version,
        "importance_version": value.importance_version,
        "classifier_version": value.classifier_version,
        "novelty_version": value.novelty_version,
        "processed_at": value.processed_at,
        "explanation": {key: list(item) for key, item in value.explanation.items()},
    }


def _feature_values(value: NewsFeatureSnapshot) -> dict[str, object]:
    features = {
        name: getattr(value, name)
        for name in (
            "news_count_15m",
            "news_count_1h",
            "news_count_6h",
            "max_relevance_1h",
            "mean_sentiment_15m",
            "mean_sentiment_1h",
            "mean_sentiment_6h",
            "relevance_weighted_sentiment_1h",
            "max_importance_1h",
            "mean_importance_1h",
            "max_novelty_1h",
            "breaking_news_count_15m",
        )
    }
    return {
        "snapshot_id": uuid5(
            NAMESPACE_URL,
            f"news-feature:{value.market}:{value.feature_time.isoformat()}:{value.feature_version}",
        ),
        "market": value.market,
        "feature_time": value.feature_time,
        "generated_at": value.generated_at,
        "feature_version": value.feature_version,
        "analyzer_versions": list(value.analyzer_versions),
        "lookbacks_minutes": list(value.lookbacks_minutes),
        "features": {
            key: str(item) if isinstance(item, Decimal) else item for key, item in features.items()
        },
    }


def _to_feature_snapshot(value: NewsFeatureSnapshotModel) -> NewsFeatureSnapshot:
    item = value.features
    decimal_fields = (
        "max_relevance_1h",
        "mean_sentiment_15m",
        "mean_sentiment_1h",
        "mean_sentiment_6h",
        "relevance_weighted_sentiment_1h",
        "max_importance_1h",
        "mean_importance_1h",
        "max_novelty_1h",
    )
    converted = {
        key: (Decimal(str(item[key])) if item.get(key) is not None else None)
        for key in decimal_fields
    }
    return NewsFeatureSnapshot(
        value.market,
        _utc(value.feature_time),
        _utc(value.generated_at),
        value.feature_version,
        tuple(value.analyzer_versions),
        tuple(value.lookbacks_minutes),
        int(item["news_count_15m"]),
        int(item["news_count_1h"]),
        int(item["news_count_6h"]),
        converted["max_relevance_1h"],
        converted["mean_sentiment_15m"],
        converted["mean_sentiment_1h"],
        converted["mean_sentiment_6h"],
        converted["relevance_weighted_sentiment_1h"],
        converted["max_importance_1h"],
        converted["mean_importance_1h"],
        converted["max_novelty_1h"],
        int(item["breaking_news_count_15m"]),
    )


def _impact_values(value: RetrospectiveImpact) -> dict[str, object]:
    return {
        "news_event_id": value.news_event_id,
        "asset": value.asset,
        "score": value.score,
        "available_windows": list(value.available_windows),
        "pending_windows": list(value.pending_windows),
        "analyzer_version": value.analyzer_version,
        "calculated_at": value.calculated_at,
        "components": {key: str(item) for key, item in value.components.items()},
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


def _to_intelligence(item: NewsIntelligenceModel) -> NewsIntelligence:
    return NewsIntelligence(
        item.intelligence_id,
        item.news_event_id,
        item.asset,
        item.relevance,
        item.sentiment,
        item.sentiment_confidence,
        item.importance,
        item.importance_confidence,
        NewsEventType(item.event_type),
        item.event_confidence,
        tuple(NewsEventType(value) for value in item.secondary_tags),
        item.novelty,
        item.novelty_confidence,
        item.story_cluster_id,
        item.sentiment_version,
        item.importance_version,
        item.classifier_version,
        item.novelty_version,
        _utc(item.processed_at),
        {key: tuple(value) for key, value in item.explanation.items()},
    )


def _to_impact(item: NewsMarketImpactModel) -> RetrospectiveImpact:
    return RetrospectiveImpact(
        item.news_event_id,
        item.asset,
        item.score,
        tuple(item.available_windows),
        tuple(item.pending_windows),
        item.analyzer_version,
        _utc(item.calculated_at),
        {key: Decimal(value) for key, value in item.components.items()},
    )


@overload
def _utc(value: datetime) -> datetime: ...


@overload
def _utc(value: None) -> None: ...


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
