"""Configurable append policies prevent unbounded high-frequency persistence."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from shared.contracts import ActionType


@dataclass(frozen=True, slots=True)
class RecordingPolicy:
    snapshot_interval: timedelta = timedelta(seconds=5)
    persist_holds: bool = False
    hold_interval: timedelta = timedelta(minutes=1)

    def should_snapshot(self, timestamp: datetime, previous: datetime | None) -> bool:
        return previous is None or timestamp - previous >= self.snapshot_interval

    def should_record_decision(
        self, action: ActionType, timestamp: datetime, previous_hold: datetime | None
    ) -> bool:
        if action is not ActionType.HOLD:
            return True
        return self.persist_holds and (
            previous_hold is None or timestamp - previous_hold >= self.hold_interval
        )
