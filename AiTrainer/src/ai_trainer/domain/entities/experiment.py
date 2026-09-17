"""Minimal reproducible experiment specification."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    """Metadata needed to reproduce a future training or backtest run."""

    experiment_id: UUID
    bot_id: str
    bot_version: str
    dataset_version: str
    feature_version: str
    starting_balance: Decimal
    start_time: datetime
    end_time: datetime
    configuration: dict[str, Any]
    random_seed: int
    git_commit: str
    model_version: str | None = None

    def __post_init__(self) -> None:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.starting_balance <= 0:
            raise ValueError("starting_balance must be positive")
