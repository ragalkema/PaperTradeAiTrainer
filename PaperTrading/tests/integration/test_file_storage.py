"""Append-only raw and idempotent normalized storage tests."""

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from paper_trading.infrastructure.persistence import AppendOnlyRawMarketStore, JsonlCandleRepository
from shared.contracts import Candle, MarketSymbol


@pytest.mark.integration
def test_raw_store_appends_without_overwriting(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = AppendOnlyRawMarketStore(tmp_path)
        await store.append("test", '{"price":"1"}')
        await store.append("test", '{"price":"2"}')

    asyncio.run(scenario())
    lines = next(tmp_path.glob("*.jsonl")).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["payload"] for line in lines] == [
        '{"price":"1"}',
        '{"price":"2"}',
    ]


@pytest.mark.integration
def test_candle_store_deduplicates_overlapping_imports(tmp_path: Path) -> None:
    candle = Candle(
        MarketSymbol("BTC-EUR"),
        "1m",
        datetime(2026, 1, 1, tzinfo=UTC),
        Decimal("100"),
        Decimal("101"),
        Decimal("99"),
        Decimal("100"),
        Decimal("1"),
    )

    async def scenario() -> None:
        repository = JsonlCandleRepository(tmp_path / "candles.jsonl")
        assert await repository.save([candle]) == 1
        assert await repository.save([candle]) == 0

    asyncio.run(scenario())
    assert len((tmp_path / "candles.jsonl").read_text(encoding="utf-8").splitlines()) == 1
