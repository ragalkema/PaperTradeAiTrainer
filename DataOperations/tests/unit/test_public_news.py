import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from data_operations.application.public_news import coverage_start, public_news_once
from data_operations.domain.entities import CollectionCheckpoint


def test_news_warmup_survives_short_restart_but_resets_after_outage() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = now - timedelta(hours=5)
    checkpoint = CollectionCheckpoint("public_news_coverage", now, now, first.isoformat())
    assert coverage_start(checkpoint, now + timedelta(minutes=5), 300) == first
    later = now + timedelta(minutes=11)
    assert coverage_start(checkpoint, later, 300) == later
    assert coverage_start(None, now, 300) == now


def test_partial_collection_analyzes_good_content_but_does_not_claim_full_coverage(monkeypatch):
    from data_collector.interfaces.cli import main as collector

    analyze = AsyncMock(return_value=12)
    monkeypatch.setattr(collector, "collect_once", AsyncMock(return_value=1))
    monkeypatch.setattr(collector, "analyze_news", analyze)
    operations = AsyncMock()
    with pytest.raises(RuntimeError, match="sources failed"):
        asyncio.run(public_news_once(operations, AsyncMock()))
    analyze.assert_awaited_once_with(1000)
    checkpoint = operations.save_checkpoint.call_args.args[0]
    assert checkpoint.external_cursor is None
    operations.checkpoint.assert_not_awaited()
