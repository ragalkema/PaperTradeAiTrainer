"""Transparent feature-group-specific research readiness."""

from datetime import datetime, timedelta

from data_operations.application.gaps import INTERVALS, MarketGapDetector
from data_operations.application.ports import OperationsRepository
from data_operations.domain.entities import (
    GroupReadiness,
    HealthStatus,
    MarketGapReport,
    ReadinessPolicy,
    ResearchReadinessReport,
    SourceCoverage,
)


class ResearchDataQualityService:
    def assess(
        self,
        market: MarketGapReport,
        news: SourceCoverage,
        social: SourceCoverage,
        canonical_rows: int,
        unusable_fraction: float,
        policy: ReadinessPolicy | None = None,
    ) -> ResearchReadinessReport:
        policy = policy or ReadinessPolicy()
        period_ok = market.end - market.start >= policy.minimum_period
        market_checks = {
            "minimum_period": period_ok,
            "market_coverage": market.coverage >= policy.minimum_market_coverage,
            "maximum_market_gap": all(
                x.observations * INTERVALS[market.interval] < policy.maximum_market_gap
                for x in market.missing_ranges
            ),
            "canonical_rows": canonical_rows >= policy.minimum_canonical_rows,
            "usable_features": unusable_fraction <= policy.maximum_unusable_feature_fraction,
        }
        groups = []
        for name, sources in (
            ("market_only", ()),
            ("market_news", (news,)),
            ("market_social", (social,)),
            ("market_news_social", (news, social)),
        ):
            checks = dict(market_checks)
            for source in sources:
                checks[f"{source.source}_operational_coverage"] = (
                    source.operational_coverage >= policy.minimum_collector_coverage
                )
            reasons = tuple(key for key, passed in checks.items() if not passed)
            groups.append(GroupReadiness(name, not reasons, checks, reasons))
        return ResearchReadinessReport(
            market.market,
            market.interval,
            market.start,
            market.end,
            policy.version,
            market.coverage,
            news.operational_coverage,
            social.operational_coverage,
            canonical_rows,
            tuple(groups),
        )


class ReadinessQueryService:
    def __init__(self, repository: OperationsRepository) -> None:
        self._repository = repository

    async def report(
        self,
        market: str,
        interval: str,
        start: datetime,
        end: datetime,
        policy: ReadinessPolicy | None = None,
    ) -> ResearchReadinessReport:
        policy = policy or ReadinessPolicy()
        present = await self._repository.candle_timestamps(market, interval, start, end)
        gaps = MarketGapDetector().detect(market, interval, start, end, present)

        async def source(name: str) -> SourceCoverage:
            intervals = await self._repository.health_intervals(name, start, end)
            seconds = sum(
                (x.end - x.start).total_seconds()
                for x in intervals
                if x.status is HealthStatus.HEALTHY
            )
            total, relevant, first = await self._repository.event_counts(
                name, market.split("-", 1)[0], start, end
            )
            return SourceCoverage(
                name, seconds, (end - start).total_seconds(), total, relevant, first
            )

        news = await source("news")
        social = await source("social")
        return ResearchDataQualityService().assess(gaps, news, social, gaps.present, 0.0, policy)


def longest_ready_period(
    intervals: tuple[tuple[datetime, datetime], ...], minimum: timedelta
) -> tuple[datetime, datetime] | None:
    if not intervals:
        return None
    ordered = sorted(intervals)
    merged: list[tuple[datetime, datetime]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    candidates = [x for x in merged if x[1] - x[0] >= minimum]
    return max(candidates, key=lambda x: x[1] - x[0]) if candidates else None
