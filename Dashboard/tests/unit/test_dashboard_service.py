from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from dashboard.application.services.dashboard_service import (
    DashboardService,
    format_money,
    format_percent,
    format_score,
)
from dashboard.application.view_models import BotSummary, IntelligenceEvent


@pytest.mark.unit
def test_formatters_never_fabricate_missing_values() -> None:
    assert format_money(None) == "N/A"
    assert format_percent(None) == "N/A"
    assert format_score(None) == "Not available"
    assert format_money(Decimal("1234.5")) == "€1,234.50"
    assert format_percent(Decimal("0.125")) == "+12.50%"


@pytest.mark.unit
def test_leaderboard_sorts_return_descending_and_missing_last() -> None:
    bots = (
        BotSummary("missing", "Missing", "baseline"),
        BotSummary("low", "Low", "baseline", percentage_return=Decimal("-0.1")),
        BotSummary("high", "High", "baseline", percentage_return=Decimal("0.2")),
    )
    assert [bot.bot_id for bot in DashboardService.rank_bots(bots)] == ["high", "low", "missing"]


def event(
    event_id: str,
    when: datetime,
    impact: Decimal | None,
    assets: tuple[str, ...] = ("BTC",),
) -> IntelligenceEvent:
    return IntelligenceEvent(
        event_id, "news", when, event_id, assets=assets, estimated_impact=impact
    )


@pytest.mark.unit
def test_top_five_filters_window_asset_future_and_orders_deterministically() -> None:
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    events = (
        event("old", now - timedelta(hours=25), Decimal("1")),
        event("future", now + timedelta(seconds=1), Decimal("1")),
        event("eth", now - timedelta(hours=1), Decimal(".99"), ("ETH",)),
        event("missing", now - timedelta(hours=1), None),
        event("tie-b", now - timedelta(hours=2), Decimal(".8")),
        event("tie-a", now - timedelta(hours=2), Decimal(".8")),
        event("top", now - timedelta(hours=3), Decimal(".9")),
        event("four", now - timedelta(hours=4), Decimal(".7")),
        event("five", now - timedelta(hours=5), Decimal(".6")),
        event("six", now - timedelta(hours=6), Decimal(".5")),
    )
    ranked = DashboardService.top_intelligence(events, now=now, asset="btc")
    assert [item.event_id for item in ranked] == ["top", "tie-a", "tie-b", "four", "five"]


@pytest.mark.unit
def test_ranking_rejects_naive_reference_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        DashboardService.top_intelligence((), now=datetime(2026, 1, 1))
