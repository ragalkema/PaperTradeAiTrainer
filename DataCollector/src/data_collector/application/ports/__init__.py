"""Source and persistence ports will be defined with their first use cases."""

from data_collector.application.ports.news import NewsQueryPort, NewsSourcePort, NewsWritePort

__all__ = ["NewsQueryPort", "NewsSourcePort", "NewsWritePort"]
