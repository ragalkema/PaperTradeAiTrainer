"""Bitvavo-to-shared-to-paper-session compatibility test."""

import asyncio
from decimal import Decimal

import httpx
import pytest
from paper_trading import PaperTradingSession
from paper_trading.infrastructure.bitvavo import BitvavoMarketDataAdapter
from shared.contracts import BotAction, MarketState, MarketSymbol


@pytest.mark.contract
def test_normalized_adapter_state_is_consumed_without_provider_fields() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/ticker/price"):
            return httpx.Response(200, json=[{"market": "BTC-EUR", "price": "100"}])
        return httpx.Response(200, json=[{"market": "BTC-EUR", "bid": "99", "ask": "101"}])

    async def scenario() -> MarketState:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.bitvavo.com/v2"
        )
        state = await BitvavoMarketDataAdapter(client=client).get_current_state(
            MarketSymbol("BTC-EUR")
        )
        await client.aclose()
        return state

    state = asyncio.run(scenario())
    session = PaperTradingSession(Decimal("1000"), Decimal("0"), Decimal("0"))
    session.update_market(state)
    result = session.execute(BotAction.buy(state.market, Decimal("100")))
    assert result.accepted
    assert result.execution_price == state.ask
