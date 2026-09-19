"""Market gap detection never interpolates prices."""

from datetime import datetime, timedelta

from data_operations.domain.entities import MarketGapReport, MissingRange

INTERVALS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


class MarketGapDetector:
    def detect(
        self,
        market: str,
        interval: str,
        start: datetime,
        end: datetime,
        present: tuple[datetime, ...],
    ) -> MarketGapReport:
        step = INTERVALS.get(interval)
        if step is None or end <= start:
            raise ValueError("unsupported interval or invalid period")
        expected = []
        cursor = start
        while cursor < end:
            expected.append(cursor)
            cursor += step
        available = set(present)
        missing = tuple(x for x in expected if x not in available)
        ranges: list[MissingRange] = []
        for value in missing:
            if not ranges or value != ranges[-1].end + step:
                ranges.append(MissingRange(value, value, 1))
            else:
                prior = ranges[-1]
                ranges[-1] = MissingRange(prior.start, value, prior.observations + 1)
        return MarketGapReport(
            market,
            interval,
            start,
            end,
            len(expected),
            len(expected) - len(missing),
            missing,
            tuple(ranges),
        )
