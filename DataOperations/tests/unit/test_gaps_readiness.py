from datetime import UTC, datetime, timedelta

from data_operations.application.gaps import MarketGapDetector
from data_operations.application.readiness import ResearchDataQualityService, longest_ready_period
from data_operations.domain.entities import ReadinessPolicy, SourceCoverage


def test_gap_detector_finds_ranges_without_interpolation() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    present = (start, start + timedelta(hours=1), start + timedelta(hours=4))
    report = MarketGapDetector().detect("BTC-EUR", "1h", start, start + timedelta(hours=5), present)
    assert report.expected == 5 and report.present == 3
    assert report.missing == (start + timedelta(hours=2), start + timedelta(hours=3))
    assert report.missing_ranges[0].observations == 2


def test_zero_events_while_healthy_differs_from_unknown_offline() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=40)
    market = MarketGapDetector().detect(
        "BTC-EUR", "1h", start, end, tuple(start + timedelta(hours=i) for i in range(960))
    )
    healthy = SourceCoverage(
        "news", (end - start).total_seconds(), (end - start).total_seconds(), 0, 0, start
    )
    unknown = SourceCoverage("social", 0, (end - start).total_seconds(), 0, 0, None)
    policy = ReadinessPolicy(minimum_canonical_rows=1)
    report = ResearchDataQualityService().assess(market, healthy, unknown, 960, 0, policy)
    values = {x.feature_group: x for x in report.groups}
    assert values["market_news"].ready
    assert not values["market_social"].ready
    assert healthy.event_count == unknown.event_count == 0


def test_longest_contiguous_period() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = longest_ready_period(
        (
            (start, start + timedelta(days=3)),
            (start + timedelta(days=3), start + timedelta(days=8)),
            (start + timedelta(days=10), start + timedelta(days=12)),
        ),
        timedelta(days=5),
    )
    assert result == (start, start + timedelta(days=8))
