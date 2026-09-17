"""Offline integration tests for the public-only Bitvavo adapter."""

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter, MarketDataError
from shared.contracts import MarketSymbol

MARKET = MarketSymbol("BTC-EUR")


def client_for(handler: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, base_url="https://api.bitvavo.com/v2")


@pytest.mark.integration
def test_current_state_normalizes_public_ticker_and_book() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ticker/price"):
            return httpx.Response(200, json=[{"market": "BTC-EUR", "price": "100000"}])
        return httpx.Response(
            200,
            json=[{"market": "BTC-EUR", "bid": "99990", "ask": "100010"}],
        )

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(handler))
        adapter = BitvavoMarketDataAdapter(client=client)
        state = await adapter.get_current_state(MARKET)
        assert state.current_price == Decimal("100000")
        assert state.bid == Decimal("99990")
        assert state.ask == Decimal("100010")
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.integration
def test_candles_are_normalized_and_sorted_chronologically() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                [2000, "101", "103", "100", "102", "2"],
                [1000, "100", "102", "99", "101", "1"],
            ],
        )

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(handler))
        adapter = BitvavoMarketDataAdapter(client=client)
        candles = await adapter.get_candles(MARKET, "1m")
        assert [candle.timestamp.timestamp() for candle in candles] == [1.0, 2.0]
        assert candles[0].close == Decimal("101")
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        [{"market": "BTC-EUR"}],
        [{"market": "BTC-EUR", "price": "not-a-number"}],
    ],
)
def test_invalid_ticker_fields_are_rejected(payload: object) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ticker/price"):
            return httpx.Response(200, json=payload)
        return httpx.Response(200, json=[{"market": "BTC-EUR", "bid": "99", "ask": "101"}])

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(handler))
        adapter = BitvavoMarketDataAdapter(client=client)
        with pytest.raises(MarketDataError, match="numeric field"):
            await adapter.get_current_state(MARKET)
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.integration
def test_timeout_is_translated_to_market_data_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(handler))
        adapter = BitvavoMarketDataAdapter(client=client)
        with pytest.raises(MarketDataError, match="network error"):
            await adapter.get_current_state(MARKET)
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.integration
def test_connection_error_is_translated_to_market_data_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(handler))
        adapter = BitvavoMarketDataAdapter(client=client)
        with pytest.raises(MarketDataError, match="network error"):
            await adapter.get_current_state(MARKET)
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.integration
def test_invalid_candle_is_rejected() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[[1000, "100", "90", "99", "101", "1"]])

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(handler))
        adapter = BitvavoMarketDataAdapter(client=client)
        with pytest.raises(MarketDataError, match="invalid candle"):
            await adapter.get_candles(MARKET, "1m")
        await client.aclose()

    asyncio.run(scenario())


@pytest.mark.integration
def test_websocket_ticker_parser_handles_valid_malformed_and_unknown_messages() -> None:
    valid = json.dumps(
        {
            "event": "ticker",
            "market": "BTC-EUR",
            "bestBid": "99",
            "bestAsk": "101",
            "lastPrice": "100",
        }
    )
    state = BitvavoMarketDataAdapter.parse_ticker_message(valid)
    assert state is not None and state.market == MARKET
    assert state.timestamp.tzinfo is not None
    assert BitvavoMarketDataAdapter.parse_ticker_message("{") is None
    assert BitvavoMarketDataAdapter.parse_ticker_message('{"event":"subscribed"}') is None
    assert BitvavoMarketDataAdapter.parse_ticker_message('{"event":"other"}') is None


@pytest.mark.integration
def test_websocket_reconnects_after_temporary_connection_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    class FakeSocket:
        async def send(self, _: str) -> None:
            return None

        async def recv(self) -> str:
            return json.dumps(
                {
                    "event": "ticker",
                    "market": "BTC-EUR",
                    "bestBid": "99",
                    "bestAsk": "101",
                    "lastPrice": "100",
                }
            )

    class FakeConnection:
        async def __aenter__(self) -> FakeSocket:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise OSError("temporary disconnect")
            return FakeSocket()

        async def __aexit__(self, *_: object) -> None:
            return None

    def fake_connect(*_: object, **__: object) -> FakeConnection:
        return FakeConnection()

    monkeypatch.setattr("paper_trading.infrastructure.bitvavo.adapter.connect", fake_connect)

    async def scenario() -> None:
        client = client_for(httpx.MockTransport(lambda _: httpx.Response(200, json=[])))
        adapter = BitvavoMarketDataAdapter(
            client=client, base_backoff_seconds=0, max_reconnect_attempts=2
        )
        stream = adapter.stream_states([MARKET])
        state = await anext(stream)
        await stream.aclose()
        await client.aclose()
        assert state.market == MARKET

    asyncio.run(scenario())
    assert attempts == 2


@pytest.mark.integration
def test_candle_range_requires_aware_timestamps() -> None:
    async def scenario() -> None:
        client = client_for(httpx.MockTransport(lambda _: httpx.Response(200, json=[])))
        adapter = BitvavoMarketDataAdapter(client=client)
        with pytest.raises(ValueError, match="timezone-aware"):
            await adapter.get_candles(MARKET, "1m", start=datetime.now())
        assert await adapter.get_candles(MARKET, "1m", start=datetime.now(UTC)) == []
        await client.aclose()

    asyncio.run(scenario())
