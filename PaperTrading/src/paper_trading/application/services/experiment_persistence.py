"""Create and finalize a reproducible persisted experiment aggregate."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from shared.contracts import MarketSymbol

from paper_trading.application.ports import ResearchWritePort
from paper_trading.application.services.recording_policy import RecordingPolicy
from paper_trading.application.services.research_recorder import ResearchRunRecorder
from paper_trading.domain.entities import (
    BotDefinitionRecord,
    BotStatus,
    ExperimentRecord,
    ExperimentStatus,
    PaperSessionRecord,
    SessionBotRecord,
    SessionStatus,
)


@dataclass(frozen=True, slots=True)
class BotRegistration:
    name: str
    bot_type: str
    version: str
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExperimentRegistration:
    name: str
    description: str
    markets: tuple[MarketSymbol, ...]
    start_period: datetime
    end_period: datetime
    starting_balance: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    random_seed: int
    bots: tuple[BotRegistration, ...]
    dataset_version: str | None = None
    feature_version: str | None = None
    git_commit: str | None = None


@dataclass(frozen=True, slots=True)
class PersistedExperimentRun:
    experiment_id: UUID
    session_id: UUID
    recorder: ResearchRunRecorder


class ExperimentPersistenceService:
    def __init__(self, repository: ResearchWritePort) -> None:
        self._repository = repository

    async def start(
        self,
        registration: ExperimentRegistration,
        policy: RecordingPolicy | None = None,
    ) -> PersistedExperimentRun:
        if not registration.bots:
            raise ValueError("at least one bot is required")
        if registration.end_period <= registration.start_period:
            raise ValueError("end_period must be after start_period")
        now = datetime.now(UTC)
        experiment_id, session_id = uuid4(), uuid4()
        experiment = ExperimentRecord(
            experiment_id,
            registration.name,
            registration.description,
            now,
            ExperimentStatus.RUNNING,
            registration.markets,
            registration.start_period,
            registration.end_period,
            registration.starting_balance,
            registration.fee_rate,
            registration.slippage_rate,
            registration.random_seed,
            registration.dataset_version,
            registration.feature_version,
            registration.git_commit,
            started_at=now,
        )
        session = PaperSessionRecord(
            session_id,
            registration.name,
            now,
            SessionStatus.RUNNING,
            registration.starting_balance,
            registration.markets,
            registration.fee_rate,
            registration.slippage_rate,
            started_at=now,
            experiment_id=experiment_id,
        )
        await self._repository.add_experiment(experiment)
        await self._repository.add_session(session)
        participant_ids: dict[str, UUID] = {}
        for bot in registration.bots:
            bot_id = uuid5(
                NAMESPACE_URL,
                f"papertradeaitrainer:{bot.name}:{bot.bot_type}:{bot.version}",
            )
            session_bot_id = uuid4()
            await self._repository.add_bot_definition(
                BotDefinitionRecord(bot_id, bot.name, bot.bot_type, bot.version, bot.configuration)
            )
            await self._repository.add_session_bot(
                SessionBotRecord(
                    session_bot_id,
                    session_id,
                    bot_id,
                    registration.starting_balance,
                    BotStatus.RUNNING,
                    now,
                    bot.configuration,
                )
            )
            participant_ids[bot.name] = session_bot_id
        return PersistedExperimentRun(
            experiment_id, session_id, ResearchRunRecorder(session_id, participant_ids, policy)
        )

    async def complete(self, run: PersistedExperimentRun) -> None:
        await run.recorder.flush(self._repository)
        ended_at = _latest_recorded_time(run.recorder) or datetime.now(UTC)
        await self._repository.set_session_status(run.session_id, SessionStatus.COMPLETED, ended_at)
        await self._repository.set_session_bots_status(run.session_id, BotStatus.COMPLETED)
        await self._repository.set_experiment_status(
            run.experiment_id, ExperimentStatus.COMPLETED, ended_at
        )

    async def fail(self, run: PersistedExperimentRun) -> None:
        ended_at = datetime.now(UTC)
        await self._repository.set_session_status(run.session_id, SessionStatus.FAILED, ended_at)
        await self._repository.set_session_bots_status(run.session_id, BotStatus.FAILED)
        await self._repository.set_experiment_status(
            run.experiment_id, ExperimentStatus.FAILED, ended_at
        )


def _latest_recorded_time(recorder: ResearchRunRecorder) -> datetime | None:
    times = [item.timestamp for item in recorder.snapshots]
    return max(times) if times else None
