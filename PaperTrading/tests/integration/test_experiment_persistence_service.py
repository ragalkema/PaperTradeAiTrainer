import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from paper_trading.application.services.experiment_persistence import (
    BotRegistration,
    ExperimentPersistenceService,
    ExperimentRegistration,
)
from paper_trading.domain.entities import BotStatus, ExperimentStatus, SessionStatus
from shared.contracts import MarketSymbol


class RecordingRepository:
    def __init__(self) -> None:
        self.values: dict[str, list[Any]] = {}
        self.session_status: tuple[SessionStatus, datetime | None] | None = None
        self.experiment_status: tuple[ExperimentStatus, datetime | None] | None = None
        self.bot_status: BotStatus | None = None

    async def _add(self, name: str, value: object) -> None:
        self.values.setdefault(name, []).append(value)

    async def add_session(self, value: object) -> None:
        await self._add("session", value)

    async def add_bot_definition(self, value: object) -> None:
        await self._add("bot", value)

    async def add_session_bot(self, value: object) -> None:
        await self._add("participant", value)

    async def add_snapshot(self, value: object) -> None:
        await self._add("snapshot", value)

    async def add_position(self, value: object) -> None:
        await self._add("position", value)

    async def add_trade(self, value: object) -> None:
        await self._add("trade", value)

    async def add_decision(self, value: object) -> None:
        await self._add("decision", value)

    async def add_experiment(self, value: object) -> None:
        await self._add("experiment", value)

    async def set_session_status(
        self, session_id: object, status: SessionStatus, ended_at: datetime | None = None
    ) -> None:
        self.session_status = status, ended_at

    async def set_experiment_status(
        self, experiment_id: object, status: ExperimentStatus, ended_at: datetime | None = None
    ) -> None:
        self.experiment_status = status, ended_at

    async def set_session_bots_status(self, session_id: object, status: BotStatus) -> None:
        self.bot_status = status


@pytest.mark.integration
def test_service_creates_independent_participants_and_finalizes() -> None:
    repository = RecordingRepository()
    service = ExperimentPersistenceService(repository)  # type: ignore[arg-type]
    start = datetime(2026, 1, 1, tzinfo=UTC)
    registration = ExperimentRegistration(
        "Comparison",
        "Fair baseline",
        (MarketSymbol("BTC-EUR"),),
        start,
        start + timedelta(days=1),
        Decimal("10000"),
        Decimal(".0025"),
        Decimal(".0005"),
        42,
        (BotRegistration("Bot A", "baseline", "1"), BotRegistration("Bot B", "baseline", "1")),
    )

    async def scenario() -> None:
        run = await service.start(registration)
        assert len(repository.values["participant"]) == 2
        assert len(set(run.recorder.session_bots.values())) == 2
        await service.complete(run)

    asyncio.run(scenario())
    assert repository.session_status and repository.session_status[0] is SessionStatus.COMPLETED
    assert (
        repository.experiment_status
        and repository.experiment_status[0] is ExperimentStatus.COMPLETED
    )
    assert repository.bot_status is BotStatus.COMPLETED
