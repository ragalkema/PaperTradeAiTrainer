import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from data_collector.application.services.reference_dataset import (
    DatasetTargets,
    ExistingIntelligenceAssessor,
    ReferenceCandidate,
    ReferenceDatasetBuilder,
)


def candidate(identifier: str, score: str) -> ReferenceCandidate:
    value = Decimal(score)
    return ReferenceCandidate(
        identifier,
        "news",
        "source",
        None,
        f"Unique content {identifier}",
        datetime(2026, 1, 1, tzinfo=UTC),
        "BTC",
        value,
        value,
        value,
        value,
        Decimal("0"),
    )


@pytest.mark.unit
def test_builder_deduplicates_balances_and_reports_real_shortfall() -> None:
    candidates = (
        candidate("high-1", "0.95"),
        candidate("high-2", "0.90"),
        candidate("mid", "0.50"),
        candidate("low-1", "0.10"),
        candidate("low-2", "0.20"),
        candidate("low-2", "0.20"),
    )

    rows, report = asyncio.run(
        ReferenceDatasetBuilder().build(
            candidates,
            ExistingIntelligenceAssessor(),
            DatasetTargets(total=8, influential=2, low_value=3),
        )
    )

    assert len(rows) == 5
    assert len({row["candidate_id"] for row in rows}) == 5
    assert report.influential == 2
    assert report.low_value == 2
    assert report.review == 1
    assert report.shortfall == 3
    assert all(row["label_origin"] == "existing_online_intelligence_v1" for row in rows)
