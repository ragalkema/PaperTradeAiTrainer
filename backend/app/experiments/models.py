"""Minimal experiment metadata contract."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExperimentSpec(BaseModel):
    """Inputs required to identify and reproduce an experiment."""

    model_config = ConfigDict(frozen=True)
    experiment_id: UUID
    bot_id: str
    bot_version: str
    strategy: str
    starting_balance: Decimal
    start_time: datetime
    end_time: datetime
    market: str
    configuration: dict[str, Any]
    random_seed: int
    feature_version: str
    code_version: str
    model_version: str | None = None
