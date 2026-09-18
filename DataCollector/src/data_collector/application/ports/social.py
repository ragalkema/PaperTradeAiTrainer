"""Provider-neutral social collection and query ports."""

from datetime import datetime, timedelta
from typing import Protocol

from data_collector.domain.entities import (
    RawSocialPost,
    SocialFeatureSnapshot,
    TrackedSocialAccount,
)


class SocialSourcePort(Protocol):
    async def fetch_recent_posts(
        self,
        accounts: tuple[TrackedSocialAccount, ...],
        *,
        start_time: datetime | None = None,
        pagination_token: str | None = None,
    ) -> tuple[tuple[RawSocialPost, ...], str | None]: ...


class OnlineSocialQueryPort(Protocol):
    async def get_social_available_at(
        self, market: str, decision_time: datetime, lookback: timedelta
    ) -> tuple[object, ...]: ...
    async def add_social_feature_snapshot(self, value: SocialFeatureSnapshot) -> None: ...
