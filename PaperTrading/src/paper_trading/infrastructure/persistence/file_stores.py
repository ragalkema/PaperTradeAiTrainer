"""Small append-only local stores for research data."""

import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from shared.contracts import Candle


class AppendOnlyRawMarketStore:
    """Append exact provider payloads to dated JSONL files."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._lock = asyncio.Lock()

    async def append(self, source: str, payload: str) -> None:
        record = json.dumps(
            {"received_at": datetime.now(UTC).isoformat(), "source": source, "payload": payload},
            ensure_ascii=False,
        )
        path = self._directory / f"market-{datetime.now(UTC):%Y-%m-%d}.jsonl"
        async with self._lock:
            await asyncio.to_thread(self._append_line, path, record)

    @staticmethod
    def _append_line(path: Path, line: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")


class JsonlCandleRepository:
    """Append normalized candles once per market/interval/timestamp."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    async def save(self, candles: list[Candle]) -> int:
        async with self._lock:
            return await asyncio.to_thread(self._save, candles)

    def _save(self, candles: list[Candle]) -> int:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        known = self._known_keys()
        new = [candle for candle in candles if self._key(candle) not in known]
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            for candle in new:
                stream.write(json.dumps(asdict(candle), default=self._json_default) + "\n")
        return len(new)

    def _known_keys(self) -> set[tuple[str, str, str]]:
        if not self._path.exists():
            return set()
        keys: set[tuple[str, str, str]] = set()
        for line in self._path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            keys.add((item["market"]["value"], item["interval"], item["timestamp"]))
        return keys

    @staticmethod
    def _key(candle: Candle) -> tuple[str, str, str]:
        return str(candle.market), candle.interval, candle.timestamp.isoformat()

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, (datetime, Decimal)):
            return str(value) if isinstance(value, Decimal) else value.isoformat()
        raise TypeError(f"cannot serialize {type(value).__name__}")


class InMemoryCandleRepository:
    """Deterministic storage adapter for tests and short experiments."""

    def __init__(self) -> None:
        self.candles: dict[tuple[str, str, datetime], Candle] = {}

    async def save(self, candles: list[Candle]) -> int:
        before = len(self.candles)
        for candle in candles:
            self.candles[(str(candle.market), candle.interval, candle.timestamp)] = candle
        return len(self.candles) - before
