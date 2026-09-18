from datetime import UTC, datetime, timedelta

import pytest
from paper_trading.application.services.recording_policy import RecordingPolicy
from shared.contracts import ActionType


@pytest.mark.unit
def test_snapshot_and_hold_throttling_are_independent() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    policy = RecordingPolicy(
        timedelta(seconds=5), persist_holds=True, hold_interval=timedelta(minutes=1)
    )
    assert policy.should_snapshot(now, None)
    assert not policy.should_snapshot(now, now - timedelta(seconds=4))
    assert policy.should_snapshot(now, now - timedelta(seconds=5))
    assert not policy.should_record_decision(ActionType.HOLD, now, now - timedelta(seconds=30))
    assert policy.should_record_decision(ActionType.HOLD, now, now - timedelta(minutes=1))
    assert policy.should_record_decision(ActionType.BUY, now, now)


@pytest.mark.unit
def test_holds_are_off_by_default() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert not RecordingPolicy().should_record_decision(ActionType.HOLD, now, None)
