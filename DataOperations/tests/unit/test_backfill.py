import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from data_operations.application.backfill import MarketBackfillService
from data_operations.application.ports import OperationsRepository
from shared.contracts import Candle, MarketSymbol


class MemoryRepository:
    def __init__(self, present=()) -> None:
        self.present = set(present)
        self.saved = []
        self.value = None

    async def save_candles(self, candles):
        new = [x for x in candles if x.timestamp not in self.present]
        self.present.update(x.timestamp for x in new)
        self.saved.extend(new)
        return len(new)

    async def candle_timestamps(self, market, interval, start, end):
        return tuple(sorted(x for x in self.present if start <= x < end))

    async def checkpoint(self, source):
        return self.value

    async def save_checkpoint(self, value):
        self.value = value


class Source:
    def __init__(self) -> None:
        self.requests = []

    async def get_candles(self, market, interval, start=None, end=None, limit=1440):
        assert start is not None and end is not None
        self.requests.append((start, end))
        output = []
        cursor = start
        while cursor < end:
            output.append(
                Candle(
                    MarketSymbol(str(market)),
                    interval,
                    cursor,
                    Decimal(1),
                    Decimal(2),
                    Decimal(1),
                    Decimal(2),
                    Decimal(1),
                )
            )
            cursor += timedelta(hours=1)
        return tuple(output)


def test_repair_requests_only_missing_ranges_and_is_idempotent() -> None:
    async def run() -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        present = (start, start + timedelta(hours=3))
        repository = MemoryRepository(present)
        source = Source()
        service = MarketBackfillService(cast(OperationsRepository, repository), source)
        assert await service.repair("BTC-EUR", "1h", start, start + timedelta(hours=4)) == 2
        assert source.requests == [(start + timedelta(hours=1), start + timedelta(hours=3))]
        assert await service.repair("BTC-EUR", "1h", start, start + timedelta(hours=4)) == 0

    asyncio.run(run())


def test_backfill_resumes_after_checkpoint() -> None:
    async def run() -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        repository = MemoryRepository()
        source = Source()
        service = MarketBackfillService(cast(OperationsRepository, repository), source, page_size=2)
        await service.backfill("BTC-EUR", "1h", start, start + timedelta(hours=3))
        source.requests.clear()
        await service.backfill("BTC-EUR", "1h", start, start + timedelta(hours=5))
        assert source.requests[0][0] == start + timedelta(hours=3)

    asyncio.run(run())
