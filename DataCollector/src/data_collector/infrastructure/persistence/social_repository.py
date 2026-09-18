"""SQLAlchemy persistence for provider-neutral social intelligence."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import and_, desc, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from data_collector.domain.entities import (
    OnlineSocialItem,
    RawSocialPost,
    SocialAccountCategory,
    SocialEngagementSnapshot,
    SocialEvent,
    SocialEventType,
    SocialFeatureSnapshot,
    SocialIntelligence,
    SocialMarketImpact,
    SocialMarketReaction,
    SocialPostType,
    TrackedSocialAccount,
    VerificationStatus,
)
from data_collector.infrastructure.persistence.models import (
    RawSocialPostModel,
    SocialEngagementSnapshotModel,
    SocialEventModel,
    SocialFeatureSnapshotModel,
    SocialIntelligenceModel,
    SocialMarketImpactModel,
    SocialMarketReactionModel,
    TrackedSocialAccountModel,
)


class SqlAlchemySocialRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def tracked_accounts(self, enabled_only: bool = True) -> tuple[TrackedSocialAccount, ...]:
        query = select(TrackedSocialAccountModel).order_by(
            desc(TrackedSocialAccountModel.priority), TrackedSocialAccountModel.username
        )
        if enabled_only:
            query = query.where(TrackedSocialAccountModel.enabled.is_(True))
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_account(x) for x in rows)

    async def add_account(self, value: TrackedSocialAccount) -> None:
        async with self._sessions.begin() as session:
            session.add(
                TrackedSocialAccountModel(
                    **{field.name: getattr(value, field.name) for field in fields(value)}
                )
            )

    async def set_account_enabled(self, username: str, enabled: bool) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(TrackedSocialAccountModel)
                .where(TrackedSocialAccountModel.username == username)
                .values(enabled=enabled, updated_at=datetime.now(UTC))
            )

    async def add_raw_social(self, value: RawSocialPost) -> bool:
        try:
            async with self._sessions.begin() as session:
                session.add(
                    RawSocialPostModel(
                        **{field.name: getattr(value, field.name) for field in fields(value)}
                    )
                )
        except IntegrityError:
            return False
        return True

    async def add_social_event(self, value: SocialEvent) -> bool:
        values = {field.name: getattr(value, field.name) for field in fields(value)}
        values["post_type"] = value.post_type.value
        values["mentioned_assets"] = list(value.mentioned_assets)
        values["asset_relevance"] = {k: str(v) for k, v in value.asset_relevance.items()}
        try:
            async with self._sessions.begin() as session:
                session.add(SocialEventModel(**values))
        except IntegrityError:
            return False
        return True

    async def add_engagement(self, value: SocialEngagementSnapshot) -> bool:
        try:
            async with self._sessions.begin() as session:
                session.add(
                    SocialEngagementSnapshotModel(
                        **{field.name: getattr(value, field.name) for field in fields(value)}
                    )
                )
        except IntegrityError:
            return False
        return True

    async def add_social_intelligence(self, value: SocialIntelligence) -> bool:
        versions = {
            "sentiment": value.sentiment_version,
            "relevance": value.relevance_version,
            "importance": value.importance_version,
            "classifier": value.classifier_version,
            "novelty": value.novelty_version,
            "influence": value.influence_version,
        }
        values = {
            "intelligence_id": value.intelligence_id,
            "social_event_id": value.social_event_id,
            "asset": value.asset,
            "relevance": value.relevance,
            "sentiment": value.sentiment,
            "sentiment_confidence": value.sentiment_confidence,
            "importance": value.importance,
            "event_type": value.event_type.value,
            "event_confidence": value.event_confidence,
            "novelty": value.novelty,
            "account_influence": value.account_influence,
            "verification_status": value.verification_status.value,
            "versions": versions,
            "processed_at": value.processed_at,
            "explanation": {k: list(v) for k, v in value.explanation.items()},
        }
        try:
            async with self._sessions.begin() as session:
                session.add(SocialIntelligenceModel(**values))
        except IntegrityError:
            return False
        return True

    async def unanalyzed_social_events(self, limit: int = 200) -> tuple[SocialEvent, ...]:
        query = (
            select(SocialEventModel)
            .where(
                ~exists().where(
                    SocialIntelligenceModel.social_event_id == SocialEventModel.social_event_id
                )
            )
            .order_by(SocialEventModel.received_at)
            .limit(limit)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_event(x) for x in rows)

    async def prior_social_events(
        self, before: datetime, lookback: timedelta
    ) -> tuple[SocialEvent, ...]:
        query = (
            select(SocialEventModel)
            .where(
                and_(
                    SocialEventModel.received_at < before,
                    SocialEventModel.received_at >= before - lookback,
                )
            )
            .order_by(SocialEventModel.received_at)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_event(x) for x in rows)

    async def recent_social(self, since: datetime, limit: int = 200) -> tuple[SocialEvent, ...]:
        query = (
            select(SocialEventModel)
            .where(SocialEventModel.received_at >= since)
            .order_by(desc(SocialEventModel.received_at))
            .limit(limit)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_event(x) for x in rows)

    async def social_intelligence_for_event(self, event_id: UUID) -> tuple[SocialIntelligence, ...]:
        async with self._sessions() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(SocialIntelligenceModel).where(
                            SocialIntelligenceModel.social_event_id == event_id
                        )
                    )
                ).all()
            )
        return tuple(_intel(x) for x in rows)

    async def get_social_available_at(
        self, market: str, decision_time: datetime, lookback: timedelta
    ) -> tuple[OnlineSocialItem, ...]:
        asset = market.split("-", 1)[0]
        query = (
            select(SocialEventModel, SocialIntelligenceModel)
            .join(SocialIntelligenceModel)
            .where(
                and_(
                    SocialIntelligenceModel.asset == asset,
                    SocialEventModel.received_at <= decision_time,
                    SocialEventModel.processed_at <= decision_time,
                    SocialEventModel.received_at >= decision_time - lookback,
                )
            )
            .order_by(SocialEventModel.received_at)
        )
        async with self._sessions() as session:
            rows = tuple((await session.execute(query)).all())
            result = []
            for event, intel in rows:
                engagement = await session.scalar(
                    select(SocialEngagementSnapshotModel)
                    .where(
                        and_(
                            SocialEngagementSnapshotModel.social_event_id == event.social_event_id,
                            SocialEngagementSnapshotModel.observed_at <= decision_time,
                        )
                    )
                    .order_by(desc(SocialEngagementSnapshotModel.observed_at))
                    .limit(1)
                )
                result.append(
                    OnlineSocialItem(
                        _event(event),
                        _intel(intel),
                        _engagement(engagement) if engagement else None,
                    )
                )
        return tuple(result)

    async def add_social_feature_snapshot(self, value: SocialFeatureSnapshot) -> None:
        features = {
            k: (str(v) if isinstance(v, Decimal) else v)
            for k, v in ((field.name, getattr(value, field.name)) for field in fields(value))
            if k
            not in {
                "market",
                "feature_time",
                "generated_at",
                "feature_version",
                "analyzer_versions",
            }
        }
        async with self._sessions.begin() as session:
            session.add(
                SocialFeatureSnapshotModel(
                    snapshot_id=uuid5(
                        NAMESPACE_URL,
                        f"social-feature:{value.market}:{value.feature_time}:{value.feature_version}",
                    ),
                    market=value.market,
                    feature_time=value.feature_time,
                    generated_at=value.generated_at,
                    feature_version=value.feature_version,
                    analyzer_versions=list(value.analyzer_versions),
                    features=features,
                )
            )

    async def social_feature_snapshots(
        self, market: str, start: datetime, end: datetime
    ) -> tuple[SocialFeatureSnapshot, ...]:
        query = (
            select(SocialFeatureSnapshotModel)
            .where(
                and_(
                    SocialFeatureSnapshotModel.market == market,
                    SocialFeatureSnapshotModel.feature_time >= start,
                    SocialFeatureSnapshotModel.feature_time <= end,
                )
            )
            .order_by(SocialFeatureSnapshotModel.feature_time)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(_social_feature(row) for row in rows)

    async def add_social_reaction(self, value: SocialMarketReaction) -> None:
        values = {field.name: getattr(value, field.name) for field in fields(value)}
        async with self._sessions.begin() as session:
            session.add(SocialMarketReactionModel(**values))

    async def social_reactions(self, event_id: UUID) -> tuple[SocialMarketReaction, ...]:
        query = (
            select(SocialMarketReactionModel)
            .where(SocialMarketReactionModel.social_event_id == event_id)
            .order_by(SocialMarketReactionModel.window_minutes)
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(
            SocialMarketReaction(
                x.reaction_id,
                x.social_event_id,
                x.market,
                x.window_minutes,
                x.event_price,
                x.post_price,
                x.price_return,
                _utc(x.observed_at),
                x.volume_before,
                x.volume_after,
            )
            for x in rows
        )

    async def upsert_social_impact(self, value: SocialMarketImpact) -> None:
        values = {
            "social_event_id": value.social_event_id,
            "asset": value.asset,
            "score": value.score,
            "available_windows": list(value.available_windows),
            "pending_windows": list(value.pending_windows),
            "analyzer_version": value.analyzer_version,
            "calculated_at": value.calculated_at,
            "components": {k: str(v) for k, v in value.components.items()},
        }
        async with self._sessions.begin() as session:
            existing = await session.get(
                SocialMarketImpactModel, (value.social_event_id, value.asset)
            )
            if existing is None:
                session.add(SocialMarketImpactModel(**values))
            else:
                for key, item in values.items():
                    setattr(existing, key, item)

    async def social_impacts(self, event_id: UUID) -> tuple[SocialMarketImpact, ...]:
        query = select(SocialMarketImpactModel).where(
            SocialMarketImpactModel.social_event_id == event_id
        )
        async with self._sessions() as session:
            rows = tuple((await session.scalars(query)).all())
        return tuple(
            SocialMarketImpact(
                x.social_event_id,
                x.asset,
                x.score,
                tuple(x.available_windows),
                tuple(x.pending_windows),
                x.analyzer_version,
                _utc(x.calculated_at),
                {k: Decimal(v) for k, v in x.components.items()},
            )
            for x in rows
        )


def _utc(x: datetime) -> datetime:
    return x.replace(tzinfo=UTC) if x.tzinfo is None else x.astimezone(UTC)


def _account(x: TrackedSocialAccountModel) -> TrackedSocialAccount:
    return TrackedSocialAccount(
        x.account_id,
        x.provider,
        x.provider_user_id,
        x.username,
        x.display_name,
        x.enabled,
        SocialAccountCategory(x.category),
        x.priority,
        _utc(x.created_at),
        _utc(x.updated_at),
        x.followers,
        x.typical_engagement,
        x.posts_per_day,
    )


def _event(x: SocialEventModel) -> SocialEvent:
    return SocialEvent(
        x.social_event_id,
        x.raw_post_id,
        x.provider,
        x.source_account_id,
        x.external_post_id,
        x.username,
        x.text,
        _utc(x.created_at),
        _utc(x.received_at),
        _utc(x.processed_at),
        x.language,
        tuple(x.mentioned_assets),
        {k: Decimal(v) for k, v in x.asset_relevance.items()},
        SocialPostType(x.post_type),
        x.reply_to,
        x.quote_of,
        x.repost_of,
        x.story_cluster_id,
    )


def _intel(x: SocialIntelligenceModel) -> SocialIntelligence:
    return SocialIntelligence(
        x.intelligence_id,
        x.social_event_id,
        x.asset,
        x.relevance,
        x.sentiment,
        x.sentiment_confidence,
        x.importance,
        SocialEventType(x.event_type),
        x.event_confidence,
        x.novelty,
        x.account_influence,
        VerificationStatus(x.verification_status),
        x.versions["sentiment"],
        x.versions["relevance"],
        x.versions["importance"],
        x.versions["classifier"],
        x.versions["novelty"],
        x.versions["influence"],
        _utc(x.processed_at),
        {k: tuple(v) for k, v in x.explanation.items()},
    )


def _engagement(x: SocialEngagementSnapshotModel) -> SocialEngagementSnapshot:
    return SocialEngagementSnapshot(
        x.snapshot_id,
        x.social_event_id,
        _utc(x.observed_at),
        x.likes,
        x.replies,
        x.reposts,
        x.quotes,
        x.bookmarks,
        x.views,
    )


def _social_feature(value: SocialFeatureSnapshotModel) -> SocialFeatureSnapshot:
    item = value.features

    def decimal(name: str) -> Decimal | None:
        raw = item.get(name)
        return Decimal(str(raw)) if raw is not None else None

    return SocialFeatureSnapshot(
        value.market,
        _utc(value.feature_time),
        _utc(value.generated_at),
        value.feature_version,
        tuple(value.analyzer_versions),
        int(item["post_count_15m"]),
        int(item["post_count_1h"]),
        int(item["post_count_6h"]),
        int(item["unique_accounts_1h"]),
        decimal("mean_sentiment_15m"),
        decimal("mean_sentiment_1h"),
        decimal("mean_sentiment_6h"),
        decimal("weighted_sentiment_1h"),
        decimal("max_relevance_1h"),
        decimal("max_importance_1h"),
        decimal("max_novelty_1h"),
        int(item["high_influence_post_count_1h"]),
        int(item["breaking_post_count_15m"]),
        decimal("social_activity_zscore"),
        decimal("engagement_velocity_1h"),
    )
