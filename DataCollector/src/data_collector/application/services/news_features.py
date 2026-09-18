"""Reproducible decision-time news features with no retrospective dependency."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from data_collector.application.ports import OnlineIntelligenceQueryPort
from data_collector.domain.entities import NewsFeatureSnapshot, OnlineNewsItem

FEATURE_VERSION = "online_news_features_v1"


class NewsFeatureService:
    """Depends only on the online port by construction; market reactions are inaccessible."""

    def __init__(self, repository: OnlineIntelligenceQueryPort) -> None:
        self._repository = repository

    async def generate(
        self,
        market: str,
        feature_time: datetime,
        generated_at: datetime | None = None,
        persist: bool = False,
    ) -> NewsFeatureSnapshot:
        if feature_time.tzinfo is None:
            raise ValueError("feature_time must be timezone-aware")
        items = await self._repository.get_news_available_at(
            market, feature_time, timedelta(hours=6)
        )
        snapshot = calculate_features(
            market, feature_time, items, generated_at or datetime.now(UTC)
        )
        if persist:
            await self._repository.add_feature_snapshot(snapshot)
        return snapshot


def calculate_features(
    market: str, feature_time: datetime, items: tuple[OnlineNewsItem, ...], generated_at: datetime
) -> NewsFeatureSnapshot:
    def window(minutes: int) -> tuple[OnlineNewsItem, ...]:
        cutoff = feature_time - timedelta(minutes=minutes)
        return tuple(
            item
            for item in items
            if cutoff <= item.event.received_at <= feature_time
            and item.event.processed_at <= feature_time
        )

    w15, w60, w360 = window(15), window(60), window(360)

    def mean(values: list[Decimal]) -> Decimal | None:
        return sum(values, Decimal("0")) / len(values) if values else None

    weights = [
        (item.intelligence.sentiment, item.intelligence.relevance * item.intelligence.importance)
        for item in w60
    ]
    denominator = sum((weight for _, weight in weights), Decimal("0"))
    weighted = (
        sum((value * weight for value, weight in weights), Decimal("0")) / denominator
        if denominator
        else None
    )
    return NewsFeatureSnapshot(
        market,
        feature_time,
        generated_at,
        FEATURE_VERSION,
        tuple(
            sorted(
                {
                    version
                    for item in items
                    for version in (
                        item.intelligence.sentiment_version,
                        item.intelligence.importance_version,
                        item.intelligence.classifier_version,
                        item.intelligence.novelty_version,
                    )
                }
            )
        ),
        (15, 60, 360),
        len(w15),
        len(w60),
        len(w360),
        max((item.intelligence.relevance for item in w60), default=None),
        mean([item.intelligence.sentiment for item in w15]),
        mean([item.intelligence.sentiment for item in w60]),
        mean([item.intelligence.sentiment for item in w360]),
        weighted,
        max((item.intelligence.importance for item in w60), default=None),
        mean([item.intelligence.importance for item in w60]),
        max((item.intelligence.novelty for item in w60), default=None),
        sum(item.intelligence.importance >= Decimal("0.75") for item in w15),
    )
