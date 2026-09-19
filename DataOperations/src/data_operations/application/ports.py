from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Protocol

from data_operations.domain.entities import (
    CollectionCheckpoint,
    CollectorHealthObservation,
    CoverageLimitation,
    DatasetManifest,
    OperationalInterval,
)
from shared.contracts import Candle, MarketSymbol


class OperationsRepository(Protocol):
    async def save_candles(self, candles: Sequence[Candle]) -> int: ...
    async def candle_timestamps(
        self, market: str, interval: str, start: datetime, end: datetime
    ) -> tuple[datetime, ...]: ...
    async def save_health(self, value: CollectorHealthObservation) -> None: ...
    async def health_intervals(
        self, source: str, start: datetime, end: datetime
    ) -> tuple[OperationalInterval, ...]: ...
    async def save_checkpoint(self, value: CollectionCheckpoint) -> None: ...
    async def checkpoint(self, source: str) -> CollectionCheckpoint | None: ...
    async def save_manifest(self, value: DatasetManifest) -> None: ...
    async def table_counts(self) -> dict[str, int]: ...
    async def event_counts(
        self, source: str, asset: str, start: datetime, end: datetime
    ) -> tuple[int, int, datetime | None]: ...
    async def save_coverage_limitation(self, value: CoverageLimitation) -> None: ...


class HistoricalMarketSource(Protocol):
    async def get_candles(
        self,
        market: MarketSymbol,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1440,
    ) -> Sequence[Candle]: ...


Operation = Callable[[], Awaitable[int]]
