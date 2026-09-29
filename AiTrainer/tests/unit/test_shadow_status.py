import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from ai_trainer.infrastructure.models.content_shadow import ShadowJournal
from ai_trainer.infrastructure.models.shadow_status import journal_status


def test_status_distinguishes_pending_overdue_and_settled_without_mutating(tmp_path):
    path = tmp_path / "shadow.db"
    ShadowJournal(path)
    decision = datetime(2026, 1, 1, tzinfo=UTC)
    entry = decision + timedelta(hours=1)
    with sqlite3.connect(path) as db:
        for model in ("one", "two"):
            db.execute(
                "INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?)",
                (
                    model,
                    "ETH-EUR",
                    entry.isoformat(),
                    decision.isoformat(),
                    decision.isoformat(),
                    1,
                    0.02,
                    "{}",
                ),
            )
    before = journal_status(path, decision)
    assert all(m["pending_not_due"] == 1 for m in before["models"])
    assert before["violations"] == []
    due = entry + timedelta(hours=2)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO outcomes VALUES (?,?,?,?,?)",
            ("one", "ETH-EUR", entry.isoformat(), due.isoformat(), 0.01),
        )
    after = journal_status(path, due)
    assert after["models"][0]["mae"] == pytest.approx(0.01)
    assert after["models"][0]["rmse"] == pytest.approx(0.01)
    assert after["models"][1]["due_unsettled"] == 1
    assert after["prediction_digest"] == before["prediction_digest"]
    assert after["integrity"] == "ok"
    with sqlite3.connect(path) as db:
        db.execute("UPDATE predictions SET recorded_at=? WHERE model_id='two'", (due.isoformat(),))
        db.execute("UPDATE outcomes SET evaluated_at=?", (decision.isoformat(),))
    invalid = journal_status(path, due)
    assert set(invalid["violations"]) == {"prediction_not_forward", "premature_outcome"}


def test_missing_journal_is_not_created_by_status(tmp_path):
    path = tmp_path / "absent.db"
    with pytest.raises(sqlite3.OperationalError):
        journal_status(path, datetime.now(UTC))
    assert not path.exists()
