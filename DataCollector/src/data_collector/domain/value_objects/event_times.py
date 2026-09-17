"""Availability timestamps for external textual content."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EventTimes:
    """Publication, receipt, and processing times used for point-in-time safety."""

    published_at: datetime
    received_at: datetime
    processed_at: datetime | None = None

    def __post_init__(self) -> None:
        timestamps = (self.published_at, self.received_at, self.processed_at)
        if any(value is not None and value.tzinfo is None for value in timestamps):
            raise ValueError("event timestamps must be timezone-aware")
        if self.received_at < self.published_at:
            raise ValueError("received_at must not precede published_at")
        if self.processed_at is not None and self.processed_at < self.received_at:
            raise ValueError("processed_at must not precede received_at")
