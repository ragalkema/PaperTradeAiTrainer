"""One-shot command-line entry point for the news collector."""

import argparse
import asyncio
import logging

from data_collector.application.services.collection import NewsCollectionService
from data_collector.application.services.normalization import NewsNormalizer
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


def main() -> int:
    parser = argparse.ArgumentParser(description="PaperTradeAiTrainer data collection")
    parser.add_argument("command", choices=("news-once",))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return asyncio.run(collect_once()) if args.command == "news-once" else 2
