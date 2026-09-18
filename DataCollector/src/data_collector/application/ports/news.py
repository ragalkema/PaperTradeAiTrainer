"""Application-owned news acquisition and persistence ports."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from data_collector.domain.entities import (
    MarketAssociation,
    NewsEvent,
    NewsSource,
    RawNewsItem,
    RawNewsStatus,
    SourceHealth,
)


class NewsSourcePort(Protocol):
    @property
    def source(self) -> NewsSource: ...
    async def fetch_latest(
        self, received_at: datetime | None = None
    ) -> tuple[RawNewsItem, ...]: ...


class NewsWritePort(Protocol):
    async def register_source(self, source: NewsSource) -> None: ...
    async def update_source_health(self, source_id: str, health: SourceHealth) -> None: ...
    async def add_raw(self, item: RawNewsItem) -> bool: ...
    async def set_raw_status(
        self, raw_item_id: UUID, status: RawNewsStatus, reason: str | None = None
    ) -> None: ...
    async def add_event(self, event: NewsEvent) -> bool: ...
    async def add_association(self, value: MarketAssociation) -> None: ...


class NewsQueryPort(Protocol):
    async def recent_news(
        self,
        *,
        since: datetime,
        asset: str | None = None,
        limit: int = 200,
    ) -> tuple[NewsEvent, ...]: ...
    async def event(self, news_event_id: UUID) -> NewsEvent | None: ...
    async def associations(self, news_event_id: UUID) -> tuple[MarketAssociation, ...]: ...
    async def sources(self) -> tuple[NewsSource, ...]: ...
