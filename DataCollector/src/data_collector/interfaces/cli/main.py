"""One-shot command-line entry point for the news collector."""

import argparse
import asyncio
import logging
from datetime import UTC, datetime, timedelta

from data_collector.application.services.collection import NewsCollectionService
from data_collector.application.services.intelligence_pipeline import NewsIntelligenceService
from data_collector.application.services.news_understanding import (
    ChronologicalNoveltyAnalyzer,
    KeywordEventClassifier,
    LexicalAssetSentimentAnalyzer,
    TransparentImportanceAnalyzer,
)
from data_collector.application.services.normalization import NewsNormalizer
from data_collector.application.services.retrospective_impact import MarketReactionUpdateService
from data_collector.infrastructure.news import default_source_registry
from data_collector.infrastructure.persistence import SqlAlchemyNewsRepository
from data_collector.infrastructure.persistence.session import data_collector_session_factory
from data_collector.infrastructure.rss import RssNewsSourceAdapter


async def collect_once() -> int:
    repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    registry = default_source_registry()
    adapters = tuple(RssNewsSourceAdapter(source) for source in registry.enabled())
    try:
        results = await asyncio.gather(
            *(
                NewsCollectionService(repository, NewsNormalizer()).collect(adapter)
                for adapter in adapters
            )
        )
    finally:
        await asyncio.gather(*(adapter.aclose() for adapter in adapters))
    logging.info(
        "news_collection_complete received=%d stored=%d events=%d duplicates=%d quarantined=%d",
        sum(item.fetched for item in results),
        sum(item.stored_raw for item in results),
        sum(item.normalized for item in results),
        sum(item.duplicates for item in results),
        sum(item.quarantined for item in results),
    )
    return 0 if not any(item.failed for item in results) else 1


async def analyze_news(limit: int) -> int:
    repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    service = NewsIntelligenceService(
        repository,
        LexicalAssetSentimentAnalyzer(),
        TransparentImportanceAnalyzer(),
        KeywordEventClassifier(),
        ChronologicalNoveltyAnalyzer(),
    )
    stored = await service.analyze_pending(limit)
    logging.info("news_analysis_complete intelligence_records=%d", stored)
    return 0


async def update_market_reactions(limit: int) -> int:
    repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    events = await repository.recent_news(since=datetime.now(UTC) - timedelta(days=30), limit=limit)
    service = MarketReactionUpdateService(repository)
    stored = sum(
        [await service.update_event(event.news_event_id, datetime.now(UTC)) for event in events]
    )
    logging.info("market_impact_update_complete records=%d", stored)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PaperTradeAiTrainer data collection")
    parser.add_argument("command", choices=("news-once", "analyze-news", "update-market-reactions"))
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "news-once":
        return asyncio.run(collect_once())
    if args.command == "analyze-news":
        return asyncio.run(analyze_news(args.limit))
    return asyncio.run(update_market_reactions(args.limit))
