"""DataCollector application boundaries."""

from data_collector.application.ports.intelligence import (
    EventClassifier,
    ImportanceAnalyzer,
    NoveltyAnalyzer,
    OnlineIntelligenceQueryPort,
    RetrospectiveResearchPort,
    SentimentAnalyzer,
)
from data_collector.application.ports.news import NewsQueryPort, NewsSourcePort, NewsWritePort

__all__ = [
    "EventClassifier",
    "ImportanceAnalyzer",
    "NewsQueryPort",
    "NewsSourcePort",
    "NewsWritePort",
    "NoveltyAnalyzer",
    "OnlineIntelligenceQueryPort",
    "RetrospectiveResearchPort",
    "SentimentAnalyzer",
]
