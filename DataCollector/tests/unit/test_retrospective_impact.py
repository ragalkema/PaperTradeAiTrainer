from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.application.services.retrospective_impact import RetrospectiveImpactAnalyzer
from data_collector.domain.entities import MarketAssociation, NewsEventType, NewsIntelligence


def intelligence(now: datetime) -> NewsIntelligence:
    return NewsIntelligence(
        uuid4(),
        uuid4(),
        "BTC",
        Decimal("0.9"),
        Decimal("0.2"),
        Decimal("0.7"),
        Decimal("0.8"),
        Decimal("0.8"),
        NewsEventType.SECURITY,
        Decimal("0.8"),
        (),
        Decimal("1"),
        Decimal("0.8"),
        uuid4(),
        "s1",
        "i1",
        "c1",
        "n1",
        now,
    )


@pytest.mark.unit
def test_impact_uses_available_windows_and_marks_pending() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    info = intelligence(now)
    reaction = MarketAssociation(
        uuid4(),
        info.news_event_id,
        "BTC-EUR",
        5,
        Decimal("100"),
        Decimal("104"),
        Decimal("0.04"),
        now,
        Decimal("10"),
        Decimal("20"),
    )
    value = RetrospectiveImpactAnalyzer().analyze(info, (reaction,), now)
    assert value.available_windows == (5,)
    assert 15 in value.pending_windows and 1440 in value.pending_windows
    assert Decimal("0") <= value.score <= 1
    assert value.analyzer_version == "heuristic_v1"


@pytest.mark.unit
def test_no_reaction_does_not_fabricate_impact() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="mature"):
        RetrospectiveImpactAnalyzer().analyze(intelligence(now), (), now)
