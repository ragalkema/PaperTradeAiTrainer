"""Point-in-time social features with engagement selected at the decision time."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from data_collector.domain.entities import OnlineSocialItem, SocialEventType, SocialFeatureSnapshot

FEATURE_VERSION = "online_social_features_v1"


def calculate_social_features(
    market: str,
    feature_time: datetime,
    items: tuple[OnlineSocialItem, ...],
    generated_at: datetime | None = None,
) -> SocialFeatureSnapshot:
    def window(minutes: int) -> tuple[OnlineSocialItem, ...]:
        cutoff = feature_time - timedelta(minutes=minutes)
        return tuple(
            x
            for x in items
            if cutoff <= x.event.received_at <= feature_time
            and x.event.processed_at <= feature_time
        )

    w15, w60, w360 = window(15), window(60), window(360)

    def mean(values: list[Decimal]) -> Decimal | None:
        return sum(values, Decimal("0")) / len(values) if values else None

    weights = [
        (
            x.intelligence.sentiment,
            x.intelligence.relevance * x.intelligence.importance * x.intelligence.account_influence,
        )
        for x in w60
    ]
    den = sum((w for _, w in weights), Decimal("0"))
    weighted = sum((s * w for s, w in weights), Decimal("0")) / den if den else None
    velocities = []
    for item in w60:
        if item.engagement and item.engagement.likes is not None:
            minutes = max(
                Decimal("1"),
                Decimal(
                    str((item.engagement.observed_at - item.event.received_at).total_seconds() / 60)
                ),
            )
            velocities.append(Decimal(item.engagement.likes) / minutes)
    versions = tuple(
        sorted(
            {
                v
                for x in items
                for v in (
                    x.intelligence.sentiment_version,
                    x.intelligence.relevance_version,
                    x.intelligence.importance_version,
                    x.intelligence.classifier_version,
                    x.intelligence.novelty_version,
                    x.intelligence.influence_version,
                )
            }
        )
    )
    return SocialFeatureSnapshot(
        market,
        feature_time,
        generated_at or datetime.now(UTC),
        FEATURE_VERSION,
        versions,
        len(w15),
        len(w60),
        len(w360),
        len({x.event.source_account_id for x in w60}),
        mean([x.intelligence.sentiment for x in w15]),
        mean([x.intelligence.sentiment for x in w60]),
        mean([x.intelligence.sentiment for x in w360]),
        weighted,
        max((x.intelligence.relevance for x in w60), default=None),
        max((x.intelligence.importance for x in w60), default=None),
        max((x.intelligence.novelty for x in w60), default=None),
        sum(x.intelligence.account_influence >= Decimal("0.7") for x in w60),
        sum(x.intelligence.event_type is SocialEventType.BREAKING_NEWS for x in w15),
        None,
        mean(velocities),
    )
