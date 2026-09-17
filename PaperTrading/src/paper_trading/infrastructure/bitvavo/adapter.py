"""Public-only Bitvavo REST and WebSocket market-data adapter."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from shared.contracts import Candle, MarketState, MarketSymbol
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from paper_trading.application.ports import RawMarketDataStore

logger = logging.getLogger(__name__)


class MarketDataError(RuntimeError):
    """Provider transport or schema error exposed without Bitvavo response coupling."""


class BitvavoMarketDataAdapter:
    """Normalize Bitvavo public data; this adapter has no authenticated/order methods."""

    REST_URL = "https://api.bitvavo.com/v2"
    WEBSOCKET_URL = "wss://ws.bitvavo.com/v2"
    SUPPORTED_INTERVALS = frozenset(
        {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "1W", "1M"}
    )

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        raw_store: RawMarketDataStore | None = None,
        timeout_seconds: float = 10.0,
        max_reconnect_attempts: int = 5,
        base_backoff_seconds: float = 1.0,
    ) -> None:
        self._client = client or httpx.AsyncClient(base_url=self.REST_URL, timeout=timeout_seconds)
        self._owns_client = client is None
        self._raw_store = raw_store
        self._timeout_seconds = timeout_seconds
        self._max_reconnect_attempts = max_reconnect_attempts
        self._base_backoff_seconds = base_backoff_seconds

    async def __aenter__(self) -> "BitvavoMarketDataAdapter":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_current_state(self, market: MarketSymbol) -> MarketState:
        price_data, book_data = await asyncio.gather(
            self._get("/ticker/price", {"market": str(market)}),
            self._get("/ticker/book", {"market": str(market)}),
        )
        price = self._single_object(price_data, "ticker price")
        book = self._single_object(book_data, "ticker book")
        self._require_market(price, market)
        self._require_market(book, market)
        return MarketState(
            market,
            datetime.now(UTC),
            self._decimal(price, "price"),
            self._decimal(book, "bid"),
            self._decimal(book, "ask"),
        )

    async def get_market_info(self, market: MarketSymbol) -> Mapping[str, Any]:
        payload = await self._get("/markets", {"market": str(market)})
        item = self._single_object(payload, "market information")
        self._require_market(item, market)
        return item

    async def get_candles(
        self,
        market: MarketSymbol,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1440,
    ) -> Sequence[Candle]:
        if interval not in self.SUPPORTED_INTERVALS:
            raise ValueError(f"unsupported candle interval: {interval}")
        if not 1 <= limit <= 1440:
            raise ValueError("candle limit must be between 1 and 1440")
        params: dict[str, str | int] = {"interval": interval, "limit": limit}
        if start is not None:
            params["start"] = self._milliseconds(start)
        if end is not None:
            params["end"] = self._milliseconds(end)
        payload = await self._get(f"/{market}/candles", params)
        if not isinstance(payload, list):
            raise MarketDataError("invalid candle response: expected a list")
        candles = [self._parse_candle(row, market, interval) for row in payload]
        return sorted(candles, key=lambda candle: candle.timestamp)

    async def _get(self, path: str, params: Mapping[str, str | int]) -> Any:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            raw = response.text
            await self._preserve_raw("bitvavo_rest", raw)
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise MarketDataError(f"temporary Bitvavo network error: {type(exc).__name__}") from exc
        except httpx.HTTPStatusError as exc:
            raise MarketDataError(f"Bitvavo returned HTTP {exc.response.status_code}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise MarketDataError("Bitvavo returned invalid JSON") from exc

    async def stream_states(self, markets: Sequence[MarketSymbol]) -> AsyncIterator[MarketState]:
        if not markets:
            raise ValueError("at least one market is required")
        attempt = 0
        subscription = {
            "action": "subscribe",
            "channels": [{"name": "ticker", "markets": [str(market) for market in markets]}],
        }
        while True:
            try:
                logger.info("bitvavo_market_connection_opening")
                async with connect(
                    self.WEBSOCKET_URL, open_timeout=self._timeout_seconds
                ) as socket:
                    await socket.send(json.dumps(subscription))
                    logger.info("bitvavo_market_connection_open")
                    while True:
                        async with asyncio.timeout(self._timeout_seconds * 6):
                            raw = await socket.recv()
                        if not isinstance(raw, str):
                            logger.warning("bitvavo_binary_message_ignored")
                            continue
                        await self._preserve_raw("bitvavo_websocket", raw)
                        state = self.parse_ticker_message(raw)
                        if state is not None:
                            attempt = 0
                            yield state
            except asyncio.CancelledError:
                logger.info("bitvavo_market_connection_shutdown")
                raise
            except (TimeoutError, ConnectionClosed, OSError, WebSocketException) as exc:
                attempt += 1
                if attempt > self._max_reconnect_attempts:
                    raise MarketDataError("Bitvavo WebSocket reconnect limit exceeded") from exc
                delay = min(self._base_backoff_seconds * (2 ** (attempt - 1)), 30.0)
                logger.warning(
                    "bitvavo_market_connection_retry attempt=%s delay=%s", attempt, delay
                )
                await asyncio.sleep(delay)

    @staticmethod
    def parse_ticker_message(raw: str) -> MarketState | None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("bitvavo_invalid_json_ignored")
            return None
        if not isinstance(payload, dict):
            logger.warning("bitvavo_invalid_message_ignored")
            return None
        event = payload.get("event")
        if event in {"subscribed", "pong"}:
            return None
        if event != "ticker":
            logger.debug("bitvavo_unknown_message_ignored event=%s", event)
            return None
        try:
            return MarketState(
                MarketSymbol(str(payload["market"])),
                datetime.now(UTC),
                Decimal(str(payload["lastPrice"])),
                Decimal(str(payload["bestBid"])),
                Decimal(str(payload["bestAsk"])),
            )
        except (KeyError, InvalidOperation, ValueError) as exc:
            logger.warning("bitvavo_invalid_ticker_ignored error=%s", type(exc).__name__)
            return None

    async def _preserve_raw(self, source: str, payload: str) -> None:
        if self._raw_store is not None:
            await self._raw_store.append(source, payload)

    @staticmethod
    def _single_object(payload: Any, label: str) -> Mapping[str, Any]:
        if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
            return payload[0]
        if isinstance(payload, dict):
            return payload
        raise MarketDataError(f"invalid {label} response")

    @staticmethod
    def _require_market(payload: Mapping[str, Any], market: MarketSymbol) -> None:
        if payload.get("market") != str(market):
            raise MarketDataError("Bitvavo response market did not match request")

    @staticmethod
    def _decimal(payload: Mapping[str, Any], field: str) -> Decimal:
        try:
            value = Decimal(str(payload[field]))
        except (KeyError, InvalidOperation) as exc:
            raise MarketDataError(f"invalid or missing numeric field: {field}") from exc
        if not value.is_finite() or value <= 0:
            raise MarketDataError(f"invalid or missing numeric field: {field}")
        return value

    @staticmethod
    def _milliseconds(value: datetime) -> int:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("candle range timestamps must be timezone-aware")
        return int(value.timestamp() * 1000)

    @staticmethod
    def _parse_candle(row: Any, market: MarketSymbol, interval: str) -> Candle:
        if not isinstance(row, list) or len(row) != 6:
            raise MarketDataError("invalid candle row")
        try:
            timestamp = datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC)
            values = [Decimal(str(value)) for value in row[1:]]
            return Candle(market, interval, timestamp, *values)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise MarketDataError("invalid candle row") from exc
