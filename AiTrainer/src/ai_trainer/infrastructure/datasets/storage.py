"""Local ignored artifact persistence with human-readable provenance."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from ai_trainer.domain.entities import ResearchModelResult, UnifiedDataset


class ResearchArtifactStore:
    def __init__(
        self, root: Path = Path("data/features"), results: Path = Path("experiments/results")
    ) -> None:
        self._root, self._results = root, results

    def save_dataset(self, dataset: UnifiedDataset) -> Path:
        folder = self._root / dataset.metadata.dataset_id
        folder.mkdir(parents=True, exist_ok=True)
        names = sorted({name for row in dataset.rows for name in row.features})
        np.savez_compressed(
            folder / "dataset.npz",
            timestamps=np.asarray([x.timestamp.isoformat() for x in dataset.rows]),
            feature_names=np.asarray(names),
            features=np.asarray(
                [
                    [np.nan if row.features.get(n) is None else row.features[n] for n in names]
                    for row in dataset.rows
                ],
                dtype=float,
            ),
            targets=np.asarray([np.nan if x.target is None else x.target for x in dataset.rows]),
        )
        (folder / "metadata.json").write_text(
            json.dumps(_json(asdict(dataset.metadata)), indent=2, sort_keys=True), encoding="utf-8"
        )
        (folder / "validation.json").write_text(
            json.dumps(
                _json(asdict(dataset.validation)) if dataset.validation else {},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return folder

    def save_comparison(
        self,
        comparison_id: str,
        name: str,
        dataset: UnifiedDataset,
        models: tuple[ResearchModelResult, ...],
    ) -> Path:
        self._results.mkdir(parents=True, exist_ok=True)
        path = self._results / f"{comparison_id}.json"
        payload = {
            "comparison_id": comparison_id,
            "name": name,
            "dataset": _json(asdict(dataset.metadata)),
            "validation": _json(asdict(dataset.validation)) if dataset.validation else None,
            "models": [_json(asdict(x)) for x in models],
            "test_period": {"start": models[0].timestamps[0], "end": models[0].timestamps[-1]}
            if models and models[0].timestamps
            else None,
        }
        path.write_text(json.dumps(_json(payload), indent=2, sort_keys=True), encoding="utf-8")
        return path


def _json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(x) for x in value]
    return value
