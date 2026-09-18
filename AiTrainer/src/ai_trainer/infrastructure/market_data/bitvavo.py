"""Read-only historical candle source for the AiTrainer composition root."""

from datetime import UTC, datetime
from decimal import Decimal

import httpx
from shared.contracts import Candle, MarketSymbol


class HistoricalBitvavoAdapter:
    URL = "https://api.bitvavo.com/v2"

    async def get_candles(
        self, market: str, interval: str, start: datetime, end: datetime, limit: int
    ) -> tuple[Candle, ...]:
        async with httpx.AsyncClient(base_url=self.URL, timeout=20) as client:
            response = await client.get(
                f"/{market}/candles",
                params={
                    "interval": interval,
                    "start": int(start.timestamp() * 1000),
                    "end": int(end.timestamp() * 1000),
                    "limit": limit,
                },
            )
            response.raise_for_status()
            payload = response.json()
        symbol = MarketSymbol(market)
        values = (
            Candle(
                symbol,
                interval,
                datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC),
                *(Decimal(str(x)) for x in row[1:]),
            )
            for row in payload
        )
        return tuple(sorted(values, key=lambda x: x.timestamp))
