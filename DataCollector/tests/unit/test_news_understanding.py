from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from data_collector.application.services.news_understanding import (
    ChronologicalNoveltyAnalyzer,
    KeywordEventClassifier,
    LexicalAssetSentimentAnalyzer,
    TransparentImportanceAnalyzer,
)
from data_collector.domain.entities import NewsEvent, NewsEventType


def event(title: str, received: datetime, assets: tuple[str, ...] = ("BTC",)) -> NewsEvent:
    return NewsEvent(
        uuid4(),
        uuid4(),
        "s",
        "Source",
        title,
        "https://x",
        received,
        received,
        received,
        assets,
        {asset: Decimal("0.8") for asset in assets},
        "en",
    )


@pytest.mark.unit
def test_sentiment_is_directional_versioned_and_asset_specific() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    analyzer = LexicalAssetSentimentAnalyzer()
    approved = analyzer.analyze(event("Bitcoin ETF approved", now), now)[0]
    hacked = analyzer.analyze(event("Major Bitcoin exchange hacked", now), now)[0]
    mixed = analyzer.analyze(
        event(
            "Ethereum gains market share as investors rotate out of Bitcoin", now, ("BTC", "ETH")
        ),
        now,
    )
    scores = {item.asset: item.score for item in mixed}
    assert approved.score > 0 > hacked.score
    assert scores["ETH"] > scores["BTC"]
    assert approved.model_version and Decimal("0") <= approved.confidence <= 1


@pytest.mark.unit
def test_classification_and_importance_are_transparent() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    classifier = KeywordEventClassifier()
    importance = TransparentImportanceAnalyzer()
    security = event("Major Bitcoin exchange hack and security breach", now)
    generic = event("Bitcoin market price update", now)
    classified = classifier.classify(security)
    assert classified.event_type is NewsEventType.SECURITY
    assert (
        importance.analyze(security, classified).score
        > importance.analyze(generic, classifier.classify(generic)).score
    )
    assert importance.analyze(security, classified).explanation


@pytest.mark.unit
def test_novelty_only_uses_strictly_prior_articles() -> None:
    start = datetime(2026, 1, 1, 14, tzinfo=UTC)
    first = event("SEC approves spot Bitcoin ETF applications", start)
    later = event("SEC approves spot Bitcoin ETF application", start + timedelta(minutes=20))
    analyzer = ChronologicalNoveltyAnalyzer()
    assert analyzer.analyze(first, (later,)).score == 1
    assert analyzer.analyze(later, (first,)).score < 1
