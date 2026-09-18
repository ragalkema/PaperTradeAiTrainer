"""Online analyzer and persistence ports kept separate from retrospective research."""

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from data_collector.domain.entities import (
    AssetSentiment,
    Classification,
    ImportanceResult,
    NewsEvent,
    NewsFeatureSnapshot,
    NewsIntelligence,
    NoveltyResult,
    OnlineNewsItem,
    RetrospectiveImpact,
)


class SentimentAnalyzer(Protocol):
    def analyze(self, event: NewsEvent, processed_at: datetime) -> tuple[AssetSentiment, ...]: ...


class EventClassifier(Protocol):
    def classify(self, event: NewsEvent) -> Classification: ...


class ImportanceAnalyzer(Protocol):
    def analyze(self, event: NewsEvent, classification: Classification) -> ImportanceResult: ...


class NoveltyAnalyzer(Protocol):
    def analyze(self, event: NewsEvent, prior_events: tuple[NewsEvent, ...]) -> NoveltyResult: ...


class OnlineIntelligenceQueryPort(Protocol):
    async def unanalyzed_events(self, limit: int = 200) -> tuple[NewsEvent, ...]: ...
    async def prior_events(
        self, received_before: datetime, lookback: timedelta
    ) -> tuple[NewsEvent, ...]: ...
    async def get_news_available_at(
        self, market: str, decision_time: datetime, lookback: timedelta
    ) -> tuple[OnlineNewsItem, ...]: ...
    async def intelligence_for_event(self, news_event_id: UUID) -> tuple[NewsIntelligence, ...]: ...
    async def add_intelligence(self, value: NewsIntelligence) -> bool: ...
    async def set_story_cluster(self, news_event_id: UUID, story_cluster_id: UUID) -> None: ...
    async def add_feature_snapshot(self, value: NewsFeatureSnapshot) -> None: ...


class RetrospectiveResearchPort(Protocol):
    async def upsert_impact(self, value: RetrospectiveImpact) -> None: ...
    async def impact_for_event(self, news_event_id: UUID) -> tuple[RetrospectiveImpact, ...]: ...
    async def top_impact(
        self, since: datetime, limit: int = 5
    ) -> tuple[RetrospectiveImpact, ...]: ...
