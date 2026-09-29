"""Auditable per-content labels, not causal attribution or model input features."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Any

from shared.contracts import Candle
from shared.contracts.market import require_aware

HORIZONS = {"1h": 1, "2h": 2, "6h": 6, "12h": 12, "24h": 24, "7d": 168, "30d": 720}
HOUR = timedelta(hours=1)
VERSION = "content_reactions_v1"


@dataclass(frozen=True)
class ContentEvent:
    event_id: str
    source_type: str
    source: str
    text: str
    published_at: datetime
    received_at: datetime
    processed_at: datetime
    assets: tuple[str, ...]
    story_id: str | None = None

    def __post_init__(self) -> None:
        for time in (self.published_at, self.received_at, self.processed_at):
            require_aware(time)
        if self.source_type not in {"news", "x"}:
            raise ValueError("expected news or x content")

    @property
    def available_at(self) -> datetime:
        return max(self.published_at, self.received_at, self.processed_at)

    @property
    def content_hash(self) -> str:
        return sha256(" ".join(self.text.casefold().split()).encode()).hexdigest()


def next_open(time: datetime) -> datetime:
    """Strictly later hourly opening, including for exact-hour arrivals."""
    require_aware(time)
    return time.astimezone(UTC).replace(minute=0, second=0, microsecond=0) + HOUR


def movement(value: Decimal) -> dict[str, str]:
    magnitude = abs(value) * 100
    band = next(
        (
            name
            for bound, name in (
                (2, "0-2%"),
                (5, "2-5%"),
                (10, "5-10%"),
                (15, "10-15%"),
                (20, "15-20%"),
            )
            if magnitude < bound
        ),
        "20%+",
    )
    direction = "up" if value > 0 else "down" if value < 0 else "flat"
    return {"direction": direction, "magnitude_band": band, "class": f"{direction}:{band}"}


class ReactionPrices:
    def __init__(self, candles: Sequence[Candle], cutoff: datetime) -> None:
        require_aware(cutoff)
        self.cutoff = cutoff
        self.index: dict[tuple[str, datetime], Candle] = {}
        for candle in candles:
            if candle.interval != "1h":
                raise ValueError("reaction dataset requires hourly candles")
            if candle.timestamp != candle.timestamp.replace(minute=0, second=0, microsecond=0):
                raise ValueError("candles must align to whole UTC hours")
            key = (str(candle.market), candle.timestamp)
            if key in self.index:
                raise ValueError("duplicate candle identity")
            # Historical stores may contain a partial last candle. Never use it.
            if candle.timestamp + HOUR <= cutoff:
                self.index[key] = candle

    def measure(self, market: str, anchor: datetime, hours: int) -> dict[str, Any]:
        entry = next_open(anchor)
        end = entry + timedelta(hours=hours)
        known_at = end + HOUR  # exit open is only used once its stored bar is closed
        result: dict[str, Any] = {
            "entry_at": entry.isoformat(),
            "target_at": end.isoformat(),
            "label_available_at": known_at.isoformat(),
            "horizon_hours": hours,
        }
        if known_at > self.cutoff:
            return {**result, "status": "pending"}
        bars = [self.index.get((market, entry + i * HOUR)) for i in range(hours + 1)]
        if any(bar is None for bar in bars):
            return {**result, "status": "missing_candles"}
        complete = [bar for bar in bars if bar is not None]
        price = complete[0].open
        change = complete[-1].open / price - 1
        # Include the exit opening, but not price action after that exit.
        maximum = max([bar.high for bar in complete[:-1]] + [complete[-1].open]) / price - 1
        minimum = min([bar.low for bar in complete[:-1]] + [complete[-1].open]) / price - 1
        return {
            **result,
            "status": "ready",
            "entry_price": float(price),
            "exit_price": float(complete[-1].open),
            "return_fraction": float(change),
            "maximum_return_fraction": float(maximum),
            "minimum_return_fraction": float(minimum),
            **movement(change),
        }


def build_reaction_rows(
    events: Sequence[ContentEvent],
    candles: Sequence[Candle],
    markets: Sequence[str],
    cutoff: datetime,
) -> list[dict[str, Any]]:
    prices = ReactionPrices(candles, cutoff)
    seen: set[tuple[str, str, str]] = set()
    rows = []
    for event in sorted(events, key=lambda e: (e.available_at, e.source_type, e.event_id)):
        if event.available_at > cutoff:
            continue
        for market in sorted(set(markets)):
            if market.split("-")[0] not in event.assets:
                continue
            identity = (event.source_type, event.event_id, market)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append(
                {
                    "sample_id": ":".join(identity),
                    "metadata": {
                        "event_id": event.event_id,
                        "market": market,
                        "published_at": event.published_at.isoformat(),
                        "received_at": event.received_at.isoformat(),
                        "processed_at": event.processed_at.isoformat(),
                        "available_at": event.available_at.isoformat(),
                        "content_hash": event.content_hash,
                        "story_group": event.story_id or event.content_hash,
                        "availability_delay_seconds": (
                            event.available_at - event.published_at
                        ).total_seconds(),
                    },
                    # No hindsight intelligence, reactions, final engagement or future prices in X.
                    "features": {
                        "text": event.text,
                        "source": event.source,
                        "source_type": event.source_type,
                        "asset": market.split("-")[0],
                    },
                    "targets": {
                        name: prices.measure(market, event.available_at, hours)
                        for name, hours in HORIZONS.items()
                    },
                    "publication_reactions_not_features": {
                        name: prices.measure(market, event.published_at, hours)
                        for name, hours in HORIZONS.items()
                    },
                }
            )
    return rows


def assign_splits(
    rows: list[dict[str, Any]],
    validation_start: datetime,
    test_start: datetime,
) -> None:
    """Purge labels crossing boundaries and whole stories repeated in later partitions."""
    require_aware(validation_start)
    require_aware(test_start)
    if validation_start >= test_start:
        raise ValueError("validation-start must precede test-start")
    seen_groups: dict[str, str] = {}
    for row in sorted(
        rows, key=lambda row: datetime.fromisoformat(row["metadata"]["available_at"])
    ):
        time = datetime.fromisoformat(row["metadata"]["available_at"])
        split = (
            "train" if time < validation_start else "validation" if time < test_start else "test"
        )
        boundary = (
            validation_start if split == "train" else test_start if split == "validation" else None
        )
        metadata = row["metadata"]
        groups = (metadata["story_group"], metadata["content_hash"])
        repeat = any(group in seen_groups and seen_groups[group] != split for group in groups)
        for group in groups:
            seen_groups.setdefault(group, split)
        for label in row["targets"].values():
            label["split"] = split
            if repeat:
                label["split"] = "excluded_repeated_story"
            elif boundary and datetime.fromisoformat(label["label_available_at"]) >= boundary:
                label["split"] = "purged_boundary"


def trainable_samples(rows: Sequence[Mapping[str, Any]], horizon: str) -> list[dict[str, Any]]:
    if horizon not in HORIZONS:
        raise ValueError("unknown horizon")
    return [
        {
            "sample_id": row["sample_id"],
            "metadata": row["metadata"],
            "features": row["features"],
            "target": row["targets"][horizon],
        }
        for row in rows
        if row["targets"][horizon]["status"] == "ready"
        and row["targets"][horizon].get("split")
        not in {"purged_boundary", "excluded_repeated_story"}
    ]
