"""Load a validation-selected research artifact once for repeated bot inference."""

import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from ai_trainer.domain.entities import DatasetRow
from ai_trainer.training.supervised.bot_research import Costs


class PaperSignalPredictor:
    """A signal provider, not an order executor; one instance per market/bot."""

    def __init__(self, report_path: Path) -> None:
        from xgboost import XGBRegressor

        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.market: str = report["market"]
        self.costs = Costs(**report["costs"])
        self.candidate = next(
            (c for c in report["candidates"] if c["id"] == report["selected_candidate"]), None
        )
        self.model: Any = None
        if self.candidate:
            path = report_path.parent / Path(self.candidate["model_path"]).name
            if hashlib.sha256(path.read_bytes()).hexdigest() != self.candidate["model_sha256"]:
                raise ValueError("model checksum mismatch")
            self.model = XGBRegressor()
            self.model.load_model(path)

    def predict(
        self, row: DatasetRow, now: datetime, *, position_open: bool = False
    ) -> dict[str, Any]:
        if not self.candidate:
            return {"action": "HOLD", "reason": "no_validation_candidate"}
        if position_open:
            return {"action": "HOLD", "reason": "position_already_open"}
        if not row.timestamp <= now < row.timestamp + timedelta(hours=1):
            return {"action": "HOLD", "reason": "stale_or_future_features"}
        names = self.candidate["features"]
        if any(
            (value := row.features.get(n)) is None
            or not math.isfinite(value)
            or n not in row.feature_observed_at
            or row.feature_observed_at[n] > row.timestamp
            for n in names
        ):
            return {"action": "HOLD", "reason": "missing_or_unavailable_features"}
        gross = float(self.model.predict(np.asarray([[row.features[n] for n in names]]))[0])
        net = self.costs.net(gross)
        return {
            "action": "BUY" if net > self.candidate["minimum_net_edge"] else "HOLD",
            "market": self.market,
            "model_id": self.candidate["id"],
            "predicted_gross_return": gross,
            "estimated_net_return": net,
            "horizon_hours": self.candidate["horizon_hours"],
            "position_fraction": 0.1,
        }
