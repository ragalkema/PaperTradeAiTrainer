"""As-of alignment using real generation times; never backdate a snapshot."""

from collections.abc import Sequence
from datetime import datetime, timedelta

from data_collector.domain.entities import NewsFeatureSnapshot


def align_news(
    snapshots: Sequence[NewsFeatureSnapshot],
    decisions: Sequence[datetime],
    market: str,
) -> dict[datetime, NewsFeatureSnapshot]:
    ordered = sorted(
        (s for s in snapshots if s.market == market and s.feature_time <= s.generated_at),
        key=lambda s: s.generated_at,
    )
    aligned = {}
    cursor = 0
    latest = None
    for decision in sorted(decisions):
        while cursor < len(ordered) and ordered[cursor].generated_at <= decision:
            latest = ordered[cursor]
            cursor += 1
        if latest and decision - latest.feature_time <= timedelta(minutes=10):
            aligned[decision] = latest
    return aligned
