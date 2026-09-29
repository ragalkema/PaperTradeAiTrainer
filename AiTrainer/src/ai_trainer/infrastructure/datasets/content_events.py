"""Read existing processed content locally; no provider calls or engagement hindsight."""

from datetime import UTC, datetime

from data_collector.infrastructure.persistence.models import NewsEventModel, SocialEventModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ai_trainer.application.services.event_reactions import ContentEvent


def _utc(time: datetime) -> datetime:
    # SQLite loses timezone metadata; persisted event times use UTC by contract.
    return time.replace(tzinfo=UTC) if time.tzinfo is None else time.astimezone(UTC)


async def read_content_events(
    sessions: async_sessionmaker[AsyncSession],
    start: datetime,
    end: datetime,
    cutoff: datetime,
) -> list[ContentEvent]:
    async with sessions() as session:
        news = (
            await session.scalars(
                select(NewsEventModel).where(
                    NewsEventModel.published_at >= start,
                    NewsEventModel.published_at < end,
                    NewsEventModel.received_at <= cutoff,
                    NewsEventModel.processed_at <= cutoff,
                )
            )
        ).all()
        posts = (
            await session.scalars(
                select(SocialEventModel).where(
                    SocialEventModel.created_at >= start,
                    SocialEventModel.created_at < end,
                    SocialEventModel.received_at <= cutoff,
                    SocialEventModel.processed_at <= cutoff,
                    SocialEventModel.provider.in_(("x", "twitter")),
                )
            )
        ).all()
    return [
        ContentEvent(
            str(event.news_event_id),
            "news",
            event.source_id,
            event.title + ("\n" + event.summary if event.summary else ""),
            _utc(event.published_at),
            _utc(event.received_at),
            _utc(event.processed_at),
            tuple(event.mentioned_assets),
            str(event.story_cluster_id) if event.story_cluster_id else None,
        )
        for event in news
    ] + [
        ContentEvent(
            str(post.social_event_id),
            "x",
            post.username,
            post.text,
            _utc(post.created_at),
            _utc(post.received_at),
            _utc(post.processed_at),
            tuple(post.mentioned_assets),
            str(post.story_cluster_id) if post.story_cluster_id else None,
        )
        for post in posts
    ]
