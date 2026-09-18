"""Collection and chronological social intelligence orchestration."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from data_collector.application.services.social_intelligence import analyze_social, normalize_social
from data_collector.domain.entities import SocialEngagementSnapshot


class SocialCollectionService:
    def __init__(self, repository: Any) -> None:
        self._repository = repository

    async def collect(self, adapter: Any) -> int:
        accounts = await self._repository.tracked_accounts()
        by_username = {x.username.casefold().lstrip("@"): x for x in accounts}
        stored = 0
        for offset in range(0, len(accounts), 25):
            token = None
            for _page in range(10):
                posts, token = await adapter.fetch_recent_posts(
                    accounts[offset : offset + 25], pagination_token=token
                )
                for raw in posts:
                    account = by_username.get(raw.username.casefold().lstrip("@"))
                    if not account or not await self._repository.add_raw_social(raw):
                        continue
                    event = normalize_social(raw, account)
                    created = await self._repository.add_social_event(event)
                    if raw.public_metrics:
                        p = raw.public_metrics
                        await self._repository.add_engagement(
                            SocialEngagementSnapshot(
                                uuid5(
                                    NAMESPACE_URL,
                                    f"engagement:{event.social_event_id}:{raw.received_at.isoformat()}",
                                ),
                                event.social_event_id,
                                raw.received_at,
                                p.get("like_count"),
                                p.get("reply_count"),
                                p.get("retweet_count"),
                                p.get("quote_count"),
                                p.get("bookmark_count"),
                                p.get("impression_count"),
                            )
                        )
                    stored += int(created)
                if not token:
                    break
        return stored


class SocialAnalysisService:
    def __init__(self, repository: Any) -> None:
        self._repository = repository

    async def analyze_pending(self, limit: int = 200) -> int:
        events = await self._repository.unanalyzed_social_events(limit)
        accounts = {x.account_id: x for x in await self._repository.tracked_accounts(False)}
        stored = 0
        for event in sorted(events, key=lambda x: (x.received_at, x.social_event_id)):
            prior = await self._repository.prior_social_events(event.received_at, timedelta(days=3))
            account = accounts[event.source_account_id]
            for result in analyze_social(event, account, prior, datetime.now(UTC)):
                stored += int(await self._repository.add_social_intelligence(result))
        return stored
