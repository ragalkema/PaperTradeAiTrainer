import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from ai_trainer.application.services.dataset import UnifiedDatasetBuilder
from ai_trainer.domain.entities import DatasetConfiguration
from ai_trainer.infrastructure.datasets.storage import ResearchArtifactStore
from shared.contracts import Candle, MarketSymbol


def _dataset():
    start = datetime(2025, 1, 1, tzinfo=UTC)
    candles = tuple(
        Candle(
            MarketSymbol("BTC-EUR"),
            "1h",
            start + timedelta(hours=i),
            Decimal(100 + i),
            Decimal(102 + i),
            Decimal(99 + i),
            Decimal(101 + i),
            Decimal(10 + i),
        )
        for i in range(24)
    )
    return UnifiedDatasetBuilder().build(
        candles, DatasetConfiguration("BTC-EUR", "1h", start, start + timedelta(hours=24))
    )


def test_dataset_artifacts_preserve_metadata_and_validation(tmp_path: Path) -> None:
    dataset = _dataset()
    store = ResearchArtifactStore(tmp_path / "features", tmp_path / "results")
    folder = store.save_dataset(dataset)
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    validation = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
    assert metadata["fingerprint"] == dataset.metadata.fingerprint
    assert validation["row_count"] == len(dataset.rows)
    assert (folder / "dataset.npz").exists()
