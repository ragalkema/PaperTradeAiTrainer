"""Bounded public market query adapter; it never exposes order capabilities."""

import asyncio
import logging
from dataclasses import replace
from decimal import Decimal
from threading import Lock

from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from shared.contracts import MarketSymbol

from dashboard.application.view_models import (
    ConnectionState,
    DashboardSnapshot,
    MarketSummary,
)

logger = logging.getLogger(__name__)


class LiveDashboardRepository:
    """Thread-safe latest snapshot backed only by public Bitvavo reads."""

    def __init__(self, markets: tuple[str, ...] = ("BTC-EUR", "ETH-EUR", "SOL-EUR")) -> None:
        self._markets = markets
        initial = tuple(
            MarketSummary(market, state=ConnectionState.CONNECTING) for market in markets
        )
        self._snapshot = DashboardSnapshot(
            markets=initial,
            connections={
                "Bitvavo": ConnectionState.CONNECTING,
                "News": ConnectionState.DISABLED,
                "Social/X": ConnectionState.DISABLED,
                "PostgreSQL": ConnectionState.DISCONNECTED,
                "Redis": ConnectionState.DISCONNECTED,
            },
        )
        self._lock = Lock()

    def snapshot(self) -> DashboardSnapshot:
        with self._lock:
            return self._snapshot

    def refresh(self) -> DashboardSnapshot:
        """Refresh in a worker thread, never the Qt event thread."""
        try:
            markets = asyncio.run(self._fetch())
            connections = dict(self.snapshot().connections)
            connections["Bitvavo"] = ConnectionState.CONNECTED
            updated = replace(self.snapshot(), markets=markets, connections=connections, errors=())
        except Exception:  # UI boundary converts details to logs and safe state.
            logger.exception("dashboard_market_refresh_failed")
            previous = self.snapshot()
            connections = dict(previous.connections)
            connections["Bitvavo"] = ConnectionState.ERROR
            markets = tuple(replace(item, state=ConnectionState.ERROR) for item in previous.markets)
            updated = replace(
                previous,
                markets=markets,
                connections=connections,
                errors=("Bitvavo connection unavailable. Retrying automatically.",),
            )
        with self._lock:
            self._snapshot = updated
        return updated

    async def _fetch(self) -> tuple[MarketSummary, ...]:
        async with BitvavoMarketDataAdapter(timeout_seconds=7) as adapter:

            async def one(name: str) -> MarketSummary:
                symbol = MarketSymbol(name)
                state, candles = await asyncio.gather(
                    adapter.get_current_state(symbol),
                    adapter.get_candles(symbol, "1h", limit=72),
                )
                candle_values = tuple(
                    (c.timestamp, c.open, c.high, c.low, c.close, c.volume) for c in candles
                )
                high: Decimal | None
                low: Decimal | None
                volume: Decimal | None
                change: Decimal | None
                if candles:
                    high = max(c.high for c in candles[-24:])
                    low = min(c.low for c in candles[-24:])
                    volume = sum((c.volume for c in candles[-24:]), start=candles[0].volume * 0)
                    first = candles[-24].open if len(candles) >= 24 else candles[0].open
                    change = (state.current_price - first) / first
                else:
                    high = low = volume = change = None
                return MarketSummary(
                    market=name,
                    timestamp=state.timestamp,
                    current_price=state.current_price,
                    change_24h=change,
                    high_24h=high,
                    low_24h=low,
                    volume_24h=volume,
                    bid=state.bid,
                    ask=state.ask,
                    state=ConnectionState.CONNECTED,
                    candles=candle_values,
                )

            return tuple(await asyncio.gather(*(one(name) for name in self._markets)))
