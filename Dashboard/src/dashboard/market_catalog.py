"""Single source of truth for markets shown by the desktop dashboard."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackedMarket:
    symbol: str
    featured: bool = False

    @property
    def asset(self) -> str:
        return self.symbol.partition("-")[0]


# Liquid/trending EUR markets on Bitvavo, reviewed on 2026-09-22. Keeping the
# list explicit makes startup deterministic; trend discovery does not belong in
# the presentation layer.
TRACKED_MARKETS: tuple[TrackedMarket, ...] = (
    TrackedMarket("BTC-EUR", featured=True),
    TrackedMarket("ETH-EUR", featured=True),
    TrackedMarket("XRP-EUR", featured=True),
    TrackedMarket("SOL-EUR", featured=True),
    TrackedMarket("TAO-EUR"),
    TrackedMarket("ADA-EUR"),
    TrackedMarket("SUI-EUR"),
    TrackedMarket("PEPE-EUR"),
    TrackedMarket("HYPE-EUR"),
    TrackedMarket("NEAR-EUR"),
    TrackedMarket("AVAX-EUR"),
    TrackedMarket("LINK-EUR"),
    TrackedMarket("DOGE-EUR"),
)

MARKET_SYMBOLS = tuple(item.symbol for item in TRACKED_MARKETS)
FEATURED_MARKETS = tuple(item.symbol for item in TRACKED_MARKETS if item.featured)
TRACKED_ASSETS = tuple(item.asset for item in TRACKED_MARKETS)
