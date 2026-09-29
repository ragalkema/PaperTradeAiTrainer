"""Recover interrupted raw ingestion atomically, without backdating availability."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from data_collector.application.services.normalization import FutureTimestampError, NewsNormalizer
from data_collector.domain.entities import RawNewsItem
from data_collector.infrastructure.persistence.models import (
    NewsEventModel,
    NewsSourceModel,
    RawNewsItemModel,
)
from data_collector.infrastructure.persistence.repository import _event_values


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def recover_pending_news(
    sessions: async_sessionmaker[AsyncSession],
    *,
    apply: bool = False,
    now: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    if now.tzinfo is None or not 1 <= limit <= 1000:
        raise ValueError("aware time and limit in 1..1000 required")
    results = []
    async with sessions.begin() as session:
        # Do not compete with items currently being processed by a live collection cycle.
        rows = (
            await session.scalars(
                select(RawNewsItemModel)
                .where(
                    RawNewsItemModel.status == "received",
                    RawNewsItemModel.received_at < now - timedelta(minutes=10),
                )
                .order_by(RawNewsItemModel.received_at, RawNewsItemModel.raw_item_id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for raw in rows:
            source = await session.get(NewsSourceModel, raw.source_id)
            if source is None:
                raise ValueError("raw item references missing source")
            existing = await session.scalar(
                select(NewsEventModel).where(NewsEventModel.raw_item_id == raw.raw_item_id)
            )
            status = "processed"
            reason = None
            event = None
            if existing is None:
                item = RawNewsItem(
                    raw.raw_item_id,
                    raw.source_id,
                    raw.title,
                    raw.url,
                    utc(raw.published_at),
                    utc(raw.received_at),
                    raw.content_hash,
                    raw.external_id,
                    raw.summary,
                    raw.author,
                    raw.raw_metadata,
                    raw.version,
                )
                try:
                    event = NewsNormalizer().normalize(item, source.name, processed_at=now)
                except FutureTimestampError as exc:
                    status, reason = "quarantined", str(exc)
                if event:
                    duplicate = await session.scalar(
                        select(NewsEventModel.news_event_id).where(
                            NewsEventModel.duplicate_group_id == event.duplicate_group_id
                        )
                    )
                    if duplicate:
                        status = "duplicate"
                    elif apply:
                        session.add(NewsEventModel(**_event_values(event)))
                        await session.flush()
            results.append(
                {
                    "raw_item_id": str(raw.raw_item_id),
                    "source": raw.source_id,
                    "received_at": utc(raw.received_at).isoformat(),
                    "status": status,
                    "processed_at": utc(existing.processed_at).isoformat()
                    if existing
                    else now.isoformat()
                    if status == "processed"
                    else None,
                    "applied": apply,
                }
            )
            if apply:
                raw.status, raw.quarantine_reason = status, reason
    return results
