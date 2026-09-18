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
from data_collector.application.ports.social import OnlineSocialQueryPort, SocialSourcePort

__all__ = [
    "EventClassifier",
    "ImportanceAnalyzer",
    "NewsQueryPort",
    "NewsSourcePort",
    "NewsWritePort",
    "NoveltyAnalyzer",
    "OnlineIntelligenceQueryPort",
    "OnlineSocialQueryPort",
    "RetrospectiveResearchPort",
    "SentimentAnalyzer",
    "SocialSourcePort",
]
