"""Experiment entities."""

from ai_trainer.domain.entities.experiment import ExperimentSpec
from ai_trainer.domain.entities.historical_result import (
    HistoricalExperimentConfig,
    HistoricalExperimentResult,
)

__all__ = ["ExperimentSpec", "HistoricalExperimentConfig", "HistoricalExperimentResult"]
