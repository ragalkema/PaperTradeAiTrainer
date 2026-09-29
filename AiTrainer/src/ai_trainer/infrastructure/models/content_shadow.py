"""Append-only forward predictions and separately matured outcomes; never orders."""

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from shared.contracts import Candle

from ai_trainer.application.services.event_reactions import ReactionPrices, next_open
from ai_trainer.training.supervised.content_comparison import predict


class ShadowJournal:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS predictions (
                model_id TEXT, market TEXT, entry_at TEXT, decision_at TEXT,
                recorded_at TEXT, horizon INTEGER, prediction REAL, inputs TEXT,
                PRIMARY KEY(model_id, market, entry_at))""")
            db.execute("""CREATE TABLE IF NOT EXISTS outcomes (
                model_id TEXT, market TEXT, entry_at TEXT, evaluated_at TEXT, actual REAL,
                PRIMARY KEY(model_id, market, entry_at))""")

    def record(self, model_path: Path, observation: dict[str, Any], now: datetime) -> bool:
        payload = model_path.read_bytes()
        model = json.loads(payload)
        decision = datetime.fromisoformat(observation["decision_at"])
        entry = next_open(decision)
        if (
            model.get("schema") != "linear_content_v1"
            or model["market"] != observation["market"]
            or datetime.fromisoformat(model["frozen_at"]) > decision
            or not decision <= now < entry
        ):
            raise ValueError(
                "only newly generated, forward predictions with a frozen model allowed"
            )
        prediction = predict(model, [observation])[0]
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO predictions VALUES (?,?,?,?,?,?,?,?)",
                (
                    sha256(payload).hexdigest(),
                    model["market"],
                    entry.isoformat(),
                    decision.isoformat(),
                    now.isoformat(),
                    model["horizon_hours"],
                    prediction,
                    json.dumps(observation, sort_keys=True, allow_nan=False),
                ),
            )
            return cursor.rowcount == 1

    def settle(self, candles: Sequence[Candle], now: datetime) -> int:
        prices = ReactionPrices(candles, now)
        count = 0
        with sqlite3.connect(self.path) as db:
            pending = db.execute("""SELECT p.model_id, p.market,
                p.entry_at, p.decision_at, p.horizon
                FROM predictions p LEFT JOIN outcomes o USING(model_id,market,entry_at)
                WHERE o.model_id IS NULL""").fetchall()
            for model, market, entry, decision, horizon in pending:
                label = prices.measure(market, datetime.fromisoformat(decision), horizon)
                if label["status"] == "ready":
                    cursor = db.execute(
                        "INSERT OR IGNORE INTO outcomes VALUES (?,?,?,?,?)",
                        (model, market, entry, now.isoformat(), label["return_fraction"]),
                    )
                    count += cursor.rowcount
        return count

    def summary(self) -> dict[str, Any]:
        with sqlite3.connect(self.path) as db:
            predictions = db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            errors = db.execute("""SELECT prediction, actual FROM predictions
                JOIN outcomes USING(model_id,market,entry_at)""").fetchall()
        return {
            "predictions": predictions,
            "matured": len(errors),
            "mae": sum(abs(p - a) for p, a in errors) / len(errors) if errors else None,
        }
