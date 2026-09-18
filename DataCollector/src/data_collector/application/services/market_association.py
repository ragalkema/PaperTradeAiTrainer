"""Observed post-event market movement; this service makes no causal claim."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from data_collector.domain.entities import MarketAssociation, NewsEvent


@dataclass(frozen=True, slots=True)
class CandleObservation:
    market: str
    timestamp: datetime
    close: Decimal
    volume: Decimal


class MarketAssociationService:
    def associate(
        self,
        event: NewsEvent,
        candles: tuple[CandleObservation, ...],
        windows: tuple[int, ...] = (5, 15, 30, 60, 240, 1440),
    ) -> tuple[MarketAssociation, ...]:
        """Compare bounded observations using received_at as the availability boundary."""
        associations: list[MarketAssociation] = []
        by_market = {item.market for item in candles}
        for market in sorted(by_market):
            ordered = sorted(
                (item for item in candles if item.market == market), key=lambda item: item.timestamp
            )
            before = [item for item in ordered if item.timestamp <= event.received_at]
            if not before:
                continue
            baseline = before[-1]
            for window in windows:
                target_time = event.received_at + timedelta(minutes=window)
                after = next((item for item in ordered if item.timestamp >= target_time), None)
                if after is None or baseline.close <= 0:
                    continue
                identifier = uuid5(
                    NAMESPACE_URL,
                    f"news-market:{event.news_event_id}:{market}:{window}",
                )
                associations.append(
                    MarketAssociation(
                        identifier,
                        event.news_event_id,
                        market,
                        window,
                        baseline.close,
                        after.close,
                        (after.close - baseline.close) / baseline.close,
                        after.timestamp,
                        baseline.volume,
                        after.volume,
                    )
                )
        return tuple(associations)
