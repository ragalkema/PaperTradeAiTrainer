"""One-command supervised research workflow."""

import argparse
import asyncio
import json
import random
import subprocess
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from data_collector.domain.entities import NewsFeatureSnapshot, SocialFeatureSnapshot
from shared.contracts import Candle, MarketSymbol

from ai_trainer.application.services.dataset import (
    DatasetLeakageValidator,
    UnifiedDatasetBuilder,
    chronological_split,
)
from ai_trainer.domain.entities import DatasetConfiguration
from ai_trainer.infrastructure.datasets.storage import ResearchArtifactStore
from ai_trainer.infrastructure.market_data import HistoricalBitvavoAdapter
from ai_trainer.infrastructure.models import XGBoostRegressorAdapter
from ai_trainer.training.supervised.comparison import FeatureGroupComparison


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-trainer", description="Point-in-time ML research (paper only)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare-feature-groups")
    compare.add_argument("--market", choices=("BTC-EUR", "ETH-EUR", "SOL-EUR"), default="BTC-EUR")
    compare.add_argument("--interval", default="1h")
    compare.add_argument("--target-horizon", default="1h")
    compare.add_argument("--limit", type=int, default=1440)
    compare.add_argument("--seed", type=int, default=42)
    compare.add_argument("--start")
    compare.add_argument("--end")
    compare.add_argument("--synthetic", action="store_true", help="validate mechanics only")
    return parser


def _duration(value: str) -> timedelta:
    units = {"m": 60, "h": 3600, "d": 86400}
    try:
        return timedelta(seconds=int(value[:-1]) * units[value[-1]])
    except (KeyError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"invalid duration: {value}") from exc


async def _compare(args: argparse.Namespace) -> int:
    end = datetime.fromisoformat(args.end) if args.end else datetime.now(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    start = datetime.fromisoformat(args.start) if args.start else end - timedelta(hours=args.limit)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    candles = (
        _synthetic_candles(args.market, args.interval, start, args.limit, args.seed)
        if args.synthetic
        else await HistoricalBitvavoAdapter().get_candles(
            args.market, args.interval, start, end, min(args.limit, 1440)
        )
    )
    configuration = DatasetConfiguration(
        args.market,
        args.interval,
        start,
        end,
        _duration(args.target_horizon),
        random_seed=args.seed,
    )
    commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        ).stdout.strip()
        or None
    )
    news, social = ((), ()) if args.synthetic else await _load_intelligence(args.market, start, end)
    dataset = UnifiedDatasetBuilder().build(
        candles,
        configuration,
        news={item.feature_time: item for item in news},
        social={item.feature_time: item for item in social},
        git_commit=commit,
    )
    DatasetLeakageValidator().validate(dataset)
    store = ResearchArtifactStore()
    location = store.save_dataset(dataset)
    split = chronological_split(dataset.rows, purge=configuration.target_horizon)
    comparison = FeatureGroupComparison(
        lambda: XGBoostRegressorAdapter({"random_state": args.seed}), Path("models/trained")
    )
    models = comparison.run(dataset, split)
    comparison_id = str(uuid4())
    result = store.save_comparison(
        comparison_id, "XGBoost feature group comparison v1", dataset, models
    )
    print(
        json.dumps(
            {
                "result_kind": "PIPELINE_VALIDATION" if args.synthetic else "REAL_RESEARCH",
                "dataset_id": dataset.metadata.dataset_id,
                "rows": len(dataset.rows),
                "dataset_path": str(location),
                "comparison_path": str(result),
                "models": {
                    x.name: {
                        "features": x.feature_configuration.value,
                        "rmse": x.metrics.rmse,
                        "mae": x.metrics.mae,
                        "pearson": x.metrics.pearson,
                        "directional_accuracy": x.metrics.directional_accuracy,
                    }
                    for x in models
                },
            },
            indent=2,
        )
    )
    return 0


async def _load_intelligence(
    market: str, start: datetime, end: datetime
) -> tuple[tuple[NewsFeatureSnapshot, ...], tuple[SocialFeatureSnapshot, ...]]:
    """One bounded query per source; unavailable storage means explicit missing coverage."""
    try:
        from data_collector.infrastructure.persistence import (
            SqlAlchemyNewsRepository,
            SqlAlchemySocialRepository,
        )
        from data_collector.infrastructure.persistence.session import data_collector_session_factory

        news_repository = SqlAlchemyNewsRepository(data_collector_session_factory)
        social_repository = SqlAlchemySocialRepository(data_collector_session_factory)
        return await asyncio.gather(
            news_repository.feature_snapshots(market, start, end),
            social_repository.social_feature_snapshots(market, start, end),
        )
    except Exception:
        return (), ()


def _synthetic_candles(
    market: str, interval: str, start: datetime, count: int, seed: int
) -> tuple[Candle, ...]:
    if interval != "1h":
        raise ValueError("synthetic CLI validation currently supports interval 1h")
    generator = random.Random(seed)
    price = Decimal("30000")
    output = []
    for index in range(max(count, 120)):
        opening = price
        price *= Decimal(str(1 + 0.002 * (generator.random() - 0.45)))
        high = max(opening, price) * Decimal("1.001")
        low = min(opening, price) * Decimal("0.999")
        output.append(
            Candle(
                MarketSymbol(market),
                interval,
                start + timedelta(hours=index),
                opening,
                high,
                low,
                price,
                Decimal(100 + index % 12),
            )
        )
    return tuple(output)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "compare-feature-groups":
        return asyncio.run(_compare(args))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
