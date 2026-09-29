"""Read-only operational audit of frozen forward predictions."""

import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any


def journal_status(path: Path, now: datetime) -> dict[str, Any]:
    if now.tzinfo is None:
        raise ValueError("timezone-aware audit time required")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        predictions = [
            dict(row)
            for row in db.execute("SELECT * FROM predictions ORDER BY model_id,market,entry_at")
        ]
        outcomes = {
            tuple(row[k] for k in ("model_id", "market", "entry_at")): dict(row)
            for row in db.execute("SELECT * FROM outcomes")
        }
    models: dict[tuple[str, str], Any] = defaultdict(list)
    violations = []
    identities = set()
    for row in predictions:
        identity = tuple(row[k] for k in ("model_id", "market", "entry_at"))
        if identity in identities:
            violations.append("duplicate_prediction")
        identities.add(identity)
        decision, recorded, entry = (
            datetime.fromisoformat(row[k]) for k in ("decision_at", "recorded_at", "entry_at")
        )
        due = entry + timedelta(hours=row["horizon"] + 1)
        if not decision <= recorded < entry:
            violations.append("prediction_not_forward")
        outcome = outcomes.get(identity)
        if outcome and datetime.fromisoformat(outcome["evaluated_at"]) < due:
            violations.append("premature_outcome")
        models[(row["model_id"], row["market"])].append((row, due, outcome))
    violations.extend("orphan_outcome" for key in outcomes if key not in identities)
    result = []
    for (model, market), items in sorted(models.items()):
        errors = [r["prediction"] - o["actual"] for r, _, o in items if o]
        pending = [due for _, due, o in items if not o]
        result.append(
            {
                "model_id": model,
                "market": market,
                "predictions": len(items),
                "matured": len(errors),
                "pending_not_due": sum(due > now for due in pending),
                "due_unsettled": sum(due <= now for due in pending),
                "next_label_available_at": min(pending).isoformat() if pending else None,
                "mae": sum(abs(e) for e in errors) / len(errors) if errors else None,
                "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)) if errors else None,
                "last_prediction_at": max(r["recorded_at"] for r, _, _ in items),
            }
        )
    return {
        "audited_at": now.isoformat(),
        "integrity": integrity,
        "predictions": len(predictions),
        "outcomes": len(outcomes),
        "prediction_digest": sha256(json.dumps(predictions, sort_keys=True).encode()).hexdigest(),
        "violations": violations,
        "models": result,
        "note": "Due/unsettled requires checking collector lag and missing candles; not a loss.",
    }
