"""Future news API/RSS adapters; APIs and feeds are preferred over scraping."""

from data_collector.infrastructure.news.registry import DEFAULT_SOURCES, NewsSourceRegistry


def default_source_registry() -> NewsSourceRegistry:
    return NewsSourceRegistry(DEFAULT_SOURCES)


__all__ = ["DEFAULT_SOURCES", "NewsSourceRegistry", "default_source_registry"]
