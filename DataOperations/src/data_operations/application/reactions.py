"""Maturity selection for retrospective research windows."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from data_collector.domain.entities import MarketAssociation, SocialMarketReaction

REACTION_WINDOWS = (5, 15, 30, 60, 240, 1440)


def mature_pending_windows(
    event_time: datetime, now: datetime, existing: tuple[int, ...]
) -> tuple[int, ...]:
    """Return only newly matured windows; future windows remain pending."""
    known = set(existing)
    return tuple(
        minutes
        for minutes in REACTION_WINDOWS
        if minutes not in known and event_time + timedelta(minutes=minutes) <= now
    )


class ReactionMaturityCoordinator:
    """Create only market reactions whose observation window has actually matured."""

    def __init__(
        self, market_repository: Any, news_repository: Any, social_repository: Any
    ) -> None:
        self._market, self._news, self._social = (
            market_repository,
            news_repository,
            social_repository,
        )

    async def update(self, now: datetime, limit: int = 500) -> int:
        since = now - timedelta(days=30)
        stored = 0
        for event in await self._news.recent_news(since=since, limit=limit):
            stored += await self._news_event(
                event, await self._news.associations(event.news_event_id), now
            )
        for event in await self._social.recent_social(since, limit):
            stored += await self._social_event(
                event, await self._social.social_reactions(event.social_event_id), now
            )
        return stored

    async def _news_event(self, event: Any, existing: tuple[Any, ...], now: datetime) -> int:
        count = 0
        for asset in event.mentioned_assets:
            market = f"{asset}-EUR"
            known = tuple(x.window_minutes for x in existing if x.market == market)
            for minutes in mature_pending_windows(event.received_at, now, known):
                prices = await self._prices(market, event.received_at, minutes)
                if prices is None:
                    continue
                first, last, before, after = prices
                await self._news.add_association(
                    MarketAssociation(
                        uuid5(
                            NAMESPACE_URL, f"news-reaction:{event.news_event_id}:{market}:{minutes}"
                        ),
                        event.news_event_id,
                        market,
                        minutes,
                        first,
                        last,
                        last / first - 1,
                        event.received_at + timedelta(minutes=minutes),
                        before,
                        after,
                    )
                )
                count += 1
        return count

    async def _social_event(self, event: Any, existing: tuple[Any, ...], now: datetime) -> int:
        count = 0
        for asset in event.mentioned_assets:
            market = f"{asset}-EUR"
            known = tuple(x.window_minutes for x in existing if x.market == market)
            for minutes in mature_pending_windows(event.received_at, now, known):
                prices = await self._prices(market, event.received_at, minutes)
                if prices is None:
                    continue
                first, last, before, after = prices
                await self._social.add_social_reaction(
                    SocialMarketReaction(
                        uuid5(
                            NAMESPACE_URL,
                            f"social-reaction:{event.social_event_id}:{market}:{minutes}",
                        ),
                        event.social_event_id,
                        market,
                        minutes,
                        first,
                        last,
                        last / first - 1,
                        event.received_at + timedelta(minutes=minutes),
                        before,
                        after,
                    )
                )
                count += 1
        return count

    async def _prices(
        self, market: str, event_time: datetime, minutes: int
    ) -> tuple[Decimal, Decimal, Decimal | None, Decimal | None] | None:
        end = event_time + timedelta(minutes=minutes)
        candles = await self._market.candles(
            market, "1m", event_time - timedelta(minutes=1), end + timedelta(minutes=1)
        )
        if len(candles) < 2:
            return None
        return candles[0].close, candles[-1].close, candles[0].volume, candles[-1].volume
