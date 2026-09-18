from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from data_collector.application.services.asset_detection import AssetDetector
from data_collector.application.services.normalization import (
    FutureTimestampError,
    NewsNormalizer,
    canonical_url,
)
from data_collector.domain.entities import RawNewsItem


def raw(
    *, published: datetime, received: datetime, title: str = "Bitcoin and ETH rise"
) -> RawNewsItem:
    return RawNewsItem(
        uuid4(),
        "source",
        title,
        "HTTPS://Example.com/item/?utm_source=x&a=1#part",
        published,
        received,
        "a" * 64,
        summary="Solana remains unchanged",
    )


@pytest.mark.unit
def test_detects_supported_assets_without_substring_false_positives() -> None:
    detector = AssetDetector()
    assert set(detector.detect("BTC, Ethereum and Solana update")) == {"BTC", "ETH", "SOL"}
    assert detector.detect("A solution for markets") == {}


@pytest.mark.unit
def test_normalizes_metadata_without_inventing_scores() -> None:
    now = datetime(2026, 9, 18, 12, tzinfo=UTC)
    event = NewsNormalizer().normalize(raw(published=now, received=now), "Example", now)
    assert event.url == "https://example.com/item?a=1"
    assert event.mentioned_assets == ("BTC", "ETH", "SOL")
    assert event.sentiment is None
    assert event.importance is None
    assert event.published_at == event.received_at == event.processed_at


@pytest.mark.unit
def test_future_publication_is_quarantined_by_policy() -> None:
    now = datetime(2026, 9, 18, 12, tzinfo=UTC)
    with pytest.raises(FutureTimestampError):
        NewsNormalizer().normalize(
            raw(published=now + timedelta(minutes=11), received=now), "X", now
        )


@pytest.mark.unit
def test_tracking_parameters_are_removed() -> None:
    assert canonical_url("https://x.test/a/?b=2&utm_medium=r#x") == "https://x.test/a?b=2"
