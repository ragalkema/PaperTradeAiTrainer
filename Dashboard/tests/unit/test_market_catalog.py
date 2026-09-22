import pytest
from dashboard.market_catalog import FEATURED_MARKETS, MARKET_SYMBOLS, TRACKED_ASSETS


@pytest.mark.unit
def test_market_catalog_drives_complete_unique_eur_dashboard_selection() -> None:
    assert FEATURED_MARKETS == ("BTC-EUR", "ETH-EUR", "XRP-EUR", "SOL-EUR")
    assert len(MARKET_SYMBOLS) >= 10
    assert len(MARKET_SYMBOLS) == len(set(MARKET_SYMBOLS))
    assert all(symbol.endswith("-EUR") for symbol in MARKET_SYMBOLS)
    assert TRACKED_ASSETS == tuple(symbol.removesuffix("-EUR") for symbol in MARKET_SYMBOLS)
