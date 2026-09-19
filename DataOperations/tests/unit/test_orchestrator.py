import asyncio
from typing import cast

from data_operations.application.orchestrator import DataOperationsRunner
from data_operations.application.ports import OperationsRepository


class HealthSink:
    def __init__(self) -> None:
        self.values = []

    async def save_health(self, value):
        self.values.append(value)


def test_partial_failure_does_not_stop_other_collectors() -> None:
    asyncio.run(_partial_failure())


async def _partial_failure() -> None:
    sink = HealthSink()
    stop = asyncio.Event()
    successes = 0

    async def broken():
        raise RuntimeError("boom")

    async def healthy():
        nonlocal successes
        successes += 1
        if successes >= 2:
            stop.set()
        return 1

    await asyncio.wait_for(
        DataOperationsRunner(
            cast(OperationsRepository, sink),
            {"broken": (broken, 0.001), "healthy": (healthy, 0.001)},
        ).run(stop),
        1,
    )
    assert successes >= 2
    assert {x.status.value for x in sink.values} >= {"healthy", "offline"}
