"""Public-only news cycle: source health, analysis, and honest online snapshots."""

from datetime import UTC, datetime, timedelta
from typing import Any

from data_collector.application.services.news_features import NewsFeatureService
from data_operations.domain.entities import CollectionCheckpoint


def coverage_start(
    checkpoint: CollectionCheckpoint | None, now: datetime, poll_seconds: int
) -> datetime:
    if checkpoint and checkpoint.external_cursor and checkpoint.last_poll_time:
        if timedelta(0) <= now - checkpoint.last_poll_time <= timedelta(seconds=2 * poll_seconds):
            return datetime.fromisoformat(checkpoint.external_cursor)
    return now


async def public_news_once(operations: Any, news: Any, poll_seconds: int = 300) -> int:
    from data_collector.interfaces.cli.main import analyze_news, collect_once

    if await collect_once() != 0:
        # An error return is not a successful collection count.
        await operations.save_checkpoint(
            CollectionCheckpoint("public_news_coverage", None, datetime.now(UTC), None)
        )
        raise RuntimeError("one or more RSS sources failed; snapshots withheld")
    await analyze_news(1000)
    now = datetime.now(UTC)
    checkpoint = await operations.checkpoint("public_news_coverage")
    first = coverage_start(checkpoint, now, poll_seconds)
    await operations.save_checkpoint(
        CollectionCheckpoint("public_news_coverage", now, now, first.isoformat())
    )
    # A 6h feature must not report unobserved downtime as zero news.
    if now - first < timedelta(hours=6):
        return 0
    for market in ("BTC-EUR", "ETH-EUR", "SOL-EUR"):
        await NewsFeatureService(news).generate(market, now, persist=True)
    return 3
