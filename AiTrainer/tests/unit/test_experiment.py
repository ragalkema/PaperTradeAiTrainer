"""Experiment reproducibility invariant tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from ai_trainer.domain.entities import ExperimentSpec


@pytest.mark.unit
def test_experiment_records_reproducibility_metadata() -> None:
    start = datetime.now(UTC)
    spec = ExperimentSpec(
        uuid4(),
        "baseline",
        "1",
        "dataset-v1",
        "features-v1",
        Decimal("10000"),
        start,
        start + timedelta(days=1),
        {"interval": "1m"},
        42,
        "abc123",
    )
    assert spec.random_seed == 42
    with pytest.raises(ValueError, match="after"):
        ExperimentSpec(uuid4(), "bot", "1", "d", "f", Decimal("1"), start, start, {}, 1, "abc")
