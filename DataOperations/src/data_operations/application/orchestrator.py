"""Failure-isolated long-running scheduling with graceful cancellation."""

import asyncio
import logging
from collections.abc import Mapping
from datetime import UTC, datetime

from data_operations.application.ports import Operation, OperationsRepository
from data_operations.domain.entities import CollectorHealthObservation, HealthStatus

logger = logging.getLogger(__name__)


class DataOperationsRunner:
    def __init__(
        self, repository: OperationsRepository, operations: Mapping[str, tuple[Operation, float]]
    ) -> None:
        self._repository, self._operations = repository, dict(operations)

    async def run(self, stop: asyncio.Event | None = None) -> None:
        shutdown = stop or asyncio.Event()
        tasks = [
            asyncio.create_task(self._worker(name, operation, seconds, shutdown), name=name)
            for name, (operation, seconds) in self._operations.items()
        ]
        logger.info("collector_started workers=%s", len(tasks))
        try:
            await shutdown.wait()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            now = datetime.now(UTC)
            await asyncio.gather(
                *(
                    self._repository.save_health(
                        CollectorHealthObservation(
                            name, now, HealthStatus.OFFLINE, error_category="graceful_shutdown"
                        )
                    )
                    for name in self._operations
                )
            )
            logger.info("collector_stopped")

    async def _worker(
        self, name: str, operation: Operation, seconds: float, stop: asyncio.Event
    ) -> None:
        while not stop.is_set():
            started = datetime.now(UTC)
            try:
                count = await operation()
                status = HealthStatus.HEALTHY
                error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("source_failed source=%s", name)
                count = 0
                status = HealthStatus.OFFLINE
                error = type(exc).__name__
            latency = int((datetime.now(UTC) - started).total_seconds() * 1000)
            await self._repository.save_health(
                CollectorHealthObservation(name, datetime.now(UTC), status, latency, count, error)
            )
            try:
                await asyncio.wait_for(stop.wait(), timeout=seconds)
            except TimeoutError:
                pass
