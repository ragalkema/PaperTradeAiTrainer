"""Read-only projection of persisted intelligence into dataset candidates."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from data_collector.application.services.reference_dataset import ReferenceCandidate
from data_collector.infrastructure.persistence.models import (
    NewsEventModel,
    NewsIntelligenceModel,
    SocialEventModel,
    SocialIntelligenceModel,
)


class SqlAlchemyReferenceCandidateRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def candidates(self, limit: int = 20_000) -> tuple[ReferenceCandidate, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        news_query = (
            select(NewsEventModel, NewsIntelligenceModel)
            .outerjoin(NewsIntelligenceModel)
            .order_by(NewsEventModel.received_at.desc())
            .limit(limit)
        )
        social_query = (
            select(SocialEventModel, SocialIntelligenceModel)
            .join(SocialIntelligenceModel)
            .order_by(SocialEventModel.received_at.desc())
            .limit(limit)
        )
        async with self._sessions() as session:
            news = tuple((await session.execute(news_query)).all())
            social = tuple((await session.execute(social_query)).all())
        output = []
        for event, intel in news:
            output.append(
                ReferenceCandidate(
                    f"news:{event.news_event_id}:{intel.asset if intel else 'NONE'}",
                    "news",
                    event.source_name,
                    event.author,
                    f"{event.title}\n{event.summary or ''}".strip(),
                    event.received_at,
                    intel.asset if intel else "NONE",
                    intel.relevance if intel else Decimal("0"),
                    intel.importance if intel else Decimal("0"),
                    intel.novelty if intel else Decimal("0"),
                    intel.importance_confidence if intel else Decimal("0"),
                    intel.sentiment if intel else Decimal("0"),
                )
            )
        output.extend(
            ReferenceCandidate(
                f"social:{event.social_event_id}:{intel.asset}",
                "social",
                event.provider,
                event.username,
                event.text,
                event.received_at,
                intel.asset,
                intel.relevance,
                intel.importance,
                intel.novelty,
                intel.account_influence,
                intel.sentiment,
            )
            for event, intel in social
        )
        return tuple(output[:limit])
