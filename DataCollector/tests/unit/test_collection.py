import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from data_collector.application.services.collection import NewsCollectionService
from data_collector.domain.entities import (
    NewsSource,
    NewsSourceKind,
    RawNewsItem,
    RawNewsStatus,
)


class Source:
    source = NewsSource("test", "Test", NewsSourceKind.RSS, True, 1, 60, "https://test/rss")

    def __init__(self, items: tuple[RawNewsItem, ...]) -> None:
        self.items = items

    async def fetch_latest(self) -> tuple[RawNewsItem, ...]:
        return self.items


class Repository:
    def __init__(self) -> None:
        self.raw_ids: set[object] = set()
        self.groups: set[object] = set()
        self.statuses: list[RawNewsStatus] = []

    async def register_source(self, source: object) -> None:
        pass

    async def update_source_health(self, source_id: str, health: object) -> None:
        pass

    async def add_raw(self, item: RawNewsItem) -> bool:
        if item.raw_item_id in self.raw_ids:
            return False
        self.raw_ids.add(item.raw_item_id)
        return True

    async def set_raw_status(
        self, raw_item_id: object, status: RawNewsStatus, reason: str | None = None
    ) -> None:
        self.statuses.append(status)

    async def add_event(self, event: object) -> bool:
        group = event.duplicate_group_id
        if group in self.groups:
            return False
        self.groups.add(group)
        return True

    async def add_association(self, value: object) -> None:
        pass


def item(title: str, received: datetime, published: datetime | None = None) -> RawNewsItem:
    return RawNewsItem(
        uuid4(), "test", title, "https://test/a", published or received, received, uuid4().hex * 2
    )


@pytest.mark.unit
def test_collection_deduplicates_and_quarantines_future_items() -> None:
    asyncio.run(_collect())


async def _collect() -> None:
    now = datetime.now(UTC)
    repository = Repository()
    result = await NewsCollectionService(repository).collect(
        Source(
            (
                item("BTC rises!", now),
                item("BTC rises", now),
                item("ETH future", now, now + timedelta(hours=1)),
            )
        )
    )
    assert (result.normalized, result.duplicates, result.quarantined) == (1, 1, 1)
    assert repository.statuses == [
        RawNewsStatus.PROCESSED,
        RawNewsStatus.DUPLICATE,
        RawNewsStatus.QUARANTINED,
    ]
