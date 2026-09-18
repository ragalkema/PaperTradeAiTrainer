"""Research-only impact analysis using future observations; never an online dependency."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from data_collector.domain.entities import (
    MarketAssociation,
    NewsIntelligence,
    RetrospectiveImpact,
)

IMPACT_VERSION = "heuristic_v1"
REACTION_WINDOWS = (5, 15, 30, 60, 240, 1440)


class ReactionRepository(Protocol):
    async def intelligence_for_event(self, news_event_id: UUID) -> tuple[NewsIntelligence, ...]: ...
    async def associations(self, news_event_id: UUID) -> tuple[MarketAssociation, ...]: ...
    async def upsert_impact(self, value: RetrospectiveImpact) -> None: ...


class RetrospectiveImpactAnalyzer:
    """Scores temporal association, not causation, and only over mature observations."""

    def analyze(
        self,
        intelligence: NewsIntelligence,
        reactions: tuple[MarketAssociation, ...],
        calculated_at: datetime,
    ) -> RetrospectiveImpact:
        if not reactions:
            raise ValueError("at least one mature market reaction is required")
        available = tuple(sorted({item.window_minutes for item in reactions}))
        pending = tuple(item for item in REACTION_WINDOWS if item not in available)
        absolute_return = max((abs(item.price_return) for item in reactions), default=Decimal("0"))
        return_signal = min(Decimal("1"), absolute_return / Decimal("0.08"))
        volume_values = []
        for item in reactions:
            if (
                item.volume_before is not None
                and item.volume_after is not None
                and item.volume_before > 0
            ):
                volume_values.append(abs(item.volume_after / item.volume_before - 1))
        volume_signal = min(Decimal("1"), max(volume_values, default=Decimal("0")))
        components = {
            "relevance": intelligence.relevance,
            "importance": intelligence.importance,
            "novelty": intelligence.novelty,
            "absolute_return": return_signal,
            "abnormal_volume": volume_signal,
        }
        # Missing future windows are excluded, not scored as zero. This prevents recency penalties.
        online = (intelligence.relevance + intelligence.importance + intelligence.novelty) / 3
        response = (return_signal * Decimal("0.75")) + (volume_signal * Decimal("0.25"))
        score = min(Decimal("1"), online * Decimal("0.45") + response * Decimal("0.55"))
        return RetrospectiveImpact(
            intelligence.news_event_id,
            intelligence.asset,
            score,
            available,
            pending,
            IMPACT_VERSION,
            calculated_at,
            components,
        )


class MarketReactionUpdateService:
    def __init__(
        self, repository: ReactionRepository, analyzer: RetrospectiveImpactAnalyzer | None = None
    ) -> None:
        self._repository = repository
        self._analyzer = analyzer or RetrospectiveImpactAnalyzer()

    async def update_event(self, news_event_id: UUID, calculated_at: datetime) -> int:
        intelligence = await self._repository.intelligence_for_event(news_event_id)
        reactions = await self._repository.associations(news_event_id)
        stored = 0
        for value in intelligence:
            market = f"{value.asset}-EUR"
            relevant = tuple(item for item in reactions if item.market == market)
            if not relevant:
                continue
            await self._repository.upsert_impact(
                self._analyzer.analyze(value, relevant, calculated_at)
            )
            stored += 1
        return stored
