"""Chronological online analysis orchestration for new and persisted events."""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from data_collector.application.ports import (
    EventClassifier,
    ImportanceAnalyzer,
    NoveltyAnalyzer,
    OnlineIntelligenceQueryPort,
    SentimentAnalyzer,
)
from data_collector.domain.entities import NewsEvent, NewsIntelligence


class NewsIntelligenceService:
    def __init__(
        self,
        repository: OnlineIntelligenceQueryPort,
        sentiment: SentimentAnalyzer,
        importance: ImportanceAnalyzer,
        classifier: EventClassifier,
        novelty: NoveltyAnalyzer,
    ) -> None:
        self._repository = repository
        self._sentiment = sentiment
        self._importance = importance
        self._classifier = classifier
        self._novelty = novelty

    async def analyze_pending(self, limit: int = 200) -> int:
        events = sorted(
            await self._repository.unanalyzed_events(limit),
            key=lambda item: (item.received_at, item.news_event_id),
        )
        count = 0
        for event in events:
            count += await self.analyze_event(event)
        return count

    async def analyze_event(self, event: NewsEvent) -> int:
        processed_at = max(datetime.now(UTC), event.processed_at)
        prior = await self._repository.prior_events(event.received_at, timedelta(days=3))
        classification = self._classifier.classify(event)
        importance = self._importance.analyze(event, classification)
        novelty = self._novelty.analyze(event, prior)
        await self._repository.set_story_cluster(event.news_event_id, novelty.story_cluster_id)
        stored = 0
        for sentiment in self._sentiment.analyze(event, processed_at):
            value = NewsIntelligence(
                uuid5(
                    NAMESPACE_URL,
                    f"intelligence:{event.news_event_id}:{sentiment.asset}:{sentiment.model_version}:{importance.model_version}:{classification.model_version}:{novelty.model_version}",
                ),
                event.news_event_id,
                sentiment.asset,
                event.asset_relevance[sentiment.asset],
                sentiment.score,
                sentiment.confidence,
                importance.score,
                importance.confidence,
                classification.event_type,
                classification.confidence,
                classification.secondary_tags,
                novelty.score,
                novelty.confidence,
                novelty.story_cluster_id,
                sentiment.model_version,
                importance.model_version,
                classification.model_version,
                novelty.model_version,
                processed_at,
                {
                    "importance": importance.explanation,
                    "classification": classification.explanation,
                    "novelty": novelty.explanation,
                },
            )
            stored += int(await self._repository.add_intelligence(value))
        return stored
