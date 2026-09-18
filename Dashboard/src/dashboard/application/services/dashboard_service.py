"""Application service for reads, formatting, and deterministic ranking."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from dashboard.application.ports import DashboardDataPort
from dashboard.application.view_models import BotSummary, DashboardSnapshot, IntelligenceEvent


class DashboardService:
    def __init__(self, data: DashboardDataPort) -> None:
        self._data = data

    def snapshot(self) -> DashboardSnapshot:
        return self._data.snapshot()

    @staticmethod
    def rank_bots(bots: tuple[BotSummary, ...]) -> tuple[BotSummary, ...]:
        return tuple(
            sorted(
                bots,
                key=lambda bot: (
                    bot.percentage_return is None,
                    -(bot.percentage_return or Decimal("0")),
                    bot.name.casefold(),
                ),
            )
        )

    @staticmethod
    def top_intelligence(
        events: tuple[IntelligenceEvent, ...],
        *,
        now: datetime | None = None,
        asset: str | None = None,
        limit: int = 5,
    ) -> tuple[IntelligenceEvent, ...]:
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        cutoff = current - timedelta(hours=24)
        eligible = (
            event
            for event in events
            if cutoff <= event.occurred_at <= current
            and (asset is None or asset.upper() in {item.upper() for item in event.assets})
        )
        return tuple(
            sorted(
                eligible,
                key=lambda event: (
                    event.estimated_impact is None,
                    -(event.estimated_impact or Decimal("-1")),
                    -event.occurred_at.timestamp(),
                    event.event_id,
                ),
            )[:limit]
        )

    @staticmethod
    def top_importance(
        events: tuple[IntelligenceEvent, ...], limit: int = 5
    ) -> tuple[IntelligenceEvent, ...]:
        return tuple(
            sorted(
                (item for item in events if item.importance is not None),
                key=lambda item: (
                    -(item.importance or Decimal("0")),
                    -item.occurred_at.timestamp(),
                    item.event_id,
                ),
            )[:limit]
        )

    @staticmethod
    def top_relevance(
        events: tuple[IntelligenceEvent, ...], asset: str | None = None, limit: int = 5
    ) -> tuple[IntelligenceEvent, ...]:
        eligible = (
            item
            for item in events
            if item.relevance is not None and (asset is None or asset in item.assets)
        )
        return tuple(
            sorted(
                eligible,
                key=lambda item: (
                    -(item.relevance or Decimal("0")),
                    -item.occurred_at.timestamp(),
                    item.event_id,
                ),
            )[:limit]
        )


def format_money(value: Decimal | None, currency: str = "EUR") -> str:
    if value is None:
        return "N/A"
    symbol = "€" if currency == "EUR" else f"{currency} "
    return f"{symbol}{value:,.2f}"


def format_percent(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2%}"


def format_score(value: Decimal | None) -> str:
    if value is None:
        return "Not available"
    return f"{value:.0%}"
