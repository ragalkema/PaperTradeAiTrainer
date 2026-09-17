"""External-content time and content invariants."""

from datetime import UTC, datetime, timedelta

import pytest
from data_collector.domain.entities import ExternalContent
from data_collector.domain.enums import SourceType
from data_collector.domain.value_objects import EventTimes


@pytest.mark.unit
def test_external_content_preserves_availability_times() -> None:
    published = datetime.now(UTC)
    times = EventTimes(published, published + timedelta(seconds=1))
    item = ExternalContent("article-1", SourceType.NEWS, "Market update", times)
    assert item.times.published_at < item.times.received_at


@pytest.mark.unit
def test_receipt_cannot_precede_publication() -> None:
    published = datetime.now(UTC)
    with pytest.raises(ValueError, match="must not precede"):
        EventTimes(published, published - timedelta(seconds=1))
