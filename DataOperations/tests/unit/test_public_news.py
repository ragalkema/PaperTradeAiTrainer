from datetime import UTC, datetime, timedelta

from data_operations.application.public_news import coverage_start
from data_operations.domain.entities import CollectionCheckpoint


def test_news_warmup_survives_short_restart_but_resets_after_outage() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = now - timedelta(hours=5)
    checkpoint = CollectionCheckpoint("public_news_coverage", now, now, first.isoformat())
    assert coverage_start(checkpoint, now + timedelta(minutes=5), 300) == first
    later = now + timedelta(minutes=11)
    assert coverage_start(checkpoint, later, 300) == later
    assert coverage_start(None, now, 300) == now
