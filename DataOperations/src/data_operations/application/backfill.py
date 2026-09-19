"""Restartable, idempotent historical market backfill and targeted repair."""

import logging
from datetime import UTC, datetime

from data_operations.application.gaps import INTERVALS, MarketGapDetector
from data_operations.application.ports import HistoricalMarketSource, OperationsRepository
from data_operations.domain.entities import CollectionCheckpoint
from shared.contracts import MarketSymbol

logger = logging.getLogger(__name__)


class MarketBackfillService:
    def __init__(
        self,
        repository: OperationsRepository,
        source: HistoricalMarketSource,
        page_size: int = 1440,
    ) -> None:
        self._repository, self._source, self._page_size = repository, source, page_size

    async def backfill(self, market: str, interval: str, start: datetime, end: datetime) -> int:
        step = INTERVALS.get(interval)
        if step is None:
            raise ValueError("unsupported interval")
        checkpoint_key = f"market:{market}:{interval}"
        checkpoint = await self._repository.checkpoint(checkpoint_key)
        cursor = (
            max(start, checkpoint.last_successful_event_time + step)
            if checkpoint and checkpoint.last_successful_event_time
            else start
        )
        stored = 0
        logger.info("backfill_started market=%s interval=%s", market, interval)
        while cursor < end:
            page_end = min(end, cursor + step * self._page_size)
            candles = tuple(
                await self._source.get_candles(
                    MarketSymbol(market), interval, cursor, page_end, self._page_size
                )
            )
            valid = tuple(
                x
                for x in candles
                if cursor <= x.timestamp < page_end
                and str(x.market) == market
                and x.interval == interval
            )
            stored += await self._repository.save_candles(valid)
            last = max((x.timestamp for x in valid), default=page_end - step)
            await self._repository.save_checkpoint(
                CollectionCheckpoint(checkpoint_key, last, datetime.now(UTC))
            )
            cursor = page_end
            logger.info("backfill_progress market=%s cursor=%s", market, cursor.isoformat())
        logger.info("backfill_completed market=%s inserted=%s", market, stored)
        return stored

    async def repair(self, market: str, interval: str, start: datetime, end: datetime) -> int:
        present = await self._repository.candle_timestamps(market, interval, start, end)
        report = MarketGapDetector().detect(market, interval, start, end, present)
        stored = 0
        step = INTERVALS[interval]
        for gap in report.missing_ranges:
            candles = await self._source.get_candles(
                MarketSymbol(market),
                interval,
                gap.start,
                gap.end + step,
                min(1440, gap.observations),
            )
            missing = set(report.missing)
            stored += await self._repository.save_candles(
                tuple(x for x in candles if x.timestamp in missing)
            )
        return stored
