from datetime import UTC, datetime, timedelta

from data_operations.application.reactions import mature_pending_windows


def test_only_elapsed_reaction_windows_mature() -> None:
    event = datetime(2026, 1, 1, tzinfo=UTC)
    assert mature_pending_windows(event, event + timedelta(minutes=31), (5,)) == (15, 30)
    assert 60 not in mature_pending_windows(event, event + timedelta(minutes=31), ())
