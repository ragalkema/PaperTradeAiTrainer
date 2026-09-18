"""Research-only social market impact; never imported by online features."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from data_collector.domain.entities import (
    SocialIntelligence,
    SocialMarketImpact,
    SocialMarketReaction,
)

VERSION = "social_market_impact_v1"
WINDOWS = (5, 15, 30, 60, 240, 1440)


class SocialRetrospectiveImpactAnalyzer:
    def analyze(
        self,
        intelligence: SocialIntelligence,
        reactions: tuple[SocialMarketReaction, ...],
        calculated_at: datetime,
    ) -> SocialMarketImpact:
        if not reactions:
            raise ValueError("at least one mature reaction is required")
        available = tuple(sorted({x.window_minutes for x in reactions}))
        returns = min(Decimal("1"), max(abs(x.price_return) for x in reactions) / Decimal("0.08"))
        volumes = [
            abs(x.volume_after / x.volume_before - 1)
            for x in reactions
            if x.volume_before and x.volume_after is not None
        ]
        volume = min(Decimal("1"), max(volumes, default=Decimal("0")))
        online = (
            intelligence.relevance
            + intelligence.importance
            + intelligence.novelty
            + intelligence.account_influence
        ) / 4
        score = min(
            Decimal("1"),
            online * Decimal("0.45")
            + (returns * Decimal("0.75") + volume * Decimal("0.25")) * Decimal("0.55"),
        )
        return SocialMarketImpact(
            intelligence.social_event_id,
            intelligence.asset,
            score,
            available,
            tuple(x for x in WINDOWS if x not in available),
            VERSION,
            calculated_at,
            {
                "relevance": intelligence.relevance,
                "importance": intelligence.importance,
                "novelty": intelligence.novelty,
                "account_influence": intelligence.account_influence,
                "absolute_return": returns,
                "abnormal_volume": volume,
            },
        )


class SocialReactionUpdateService:
    def __init__(self, repository: Any) -> None:
        self._repository = repository
        self._analyzer = SocialRetrospectiveImpactAnalyzer()

    async def update_event(self, event_id: object, calculated_at: datetime) -> int:
        intelligence = await self._repository.social_intelligence_for_event(event_id)
        reactions = await self._repository.social_reactions(event_id)
        stored = 0
        for value in intelligence:
            relevant = tuple(x for x in reactions if x.market.startswith(f"{value.asset}-"))
            if relevant:
                await self._repository.upsert_social_impact(
                    self._analyzer.analyze(value, relevant, calculated_at)
                )
                stored += 1
        return stored
