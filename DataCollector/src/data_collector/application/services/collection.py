"""Coordinate source collection, immutable storage, and safe normalization."""

import logging
from dataclasses import dataclass

from data_collector.application.ports import NewsSourcePort, NewsWritePort
from data_collector.application.services.normalization import FutureTimestampError, NewsNormalizer
from data_collector.domain.entities import RawNewsStatus, SourceHealth

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionResult:
    source_id: str
    fetched: int
    stored_raw: int
    normalized: int
    duplicates: int
    quarantined: int
    failed: bool = False


class NewsCollectionService:
    def __init__(self, repository: NewsWritePort, normalizer: NewsNormalizer | None = None) -> None:
        self._repository = repository
        self._normalizer = normalizer or NewsNormalizer()

    async def collect(self, adapter: NewsSourcePort) -> CollectionResult:
        source = adapter.source
        await self._repository.register_source(source)
        try:
            items = await adapter.fetch_latest()
        except Exception:
            logger.exception("news_source_fetch_failed source=%s", source.source_id)
            await self._repository.update_source_health(source.source_id, SourceHealth.FAILED)
            return CollectionResult(source.source_id, 0, 0, 0, 0, 0, failed=True)
        stored = normalized = duplicates = quarantined = 0
        for raw in items:
            if not await self._repository.add_raw(raw):
                duplicates += 1
                continue
            stored += 1
            try:
                event = self._normalizer.normalize(raw, source.name)
            except FutureTimestampError as exc:
                quarantined += 1
                await self._repository.set_raw_status(
                    raw.raw_item_id, RawNewsStatus.QUARANTINED, str(exc)
                )
                continue
            if await self._repository.add_event(event):
                normalized += 1
                await self._repository.set_raw_status(raw.raw_item_id, RawNewsStatus.PROCESSED)
            else:
                duplicates += 1
                await self._repository.set_raw_status(raw.raw_item_id, RawNewsStatus.DUPLICATE)
        await self._repository.update_source_health(source.source_id, SourceHealth.HEALTHY)
        return CollectionResult(
            source.source_id, len(items), stored, normalized, duplicates, quarantined
        )
