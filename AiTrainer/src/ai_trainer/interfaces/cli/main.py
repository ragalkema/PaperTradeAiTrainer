"""One-command supervised research workflow."""

import argparse
import asyncio
import json
import random
import subprocess
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from data_collector.domain.entities import NewsFeatureSnapshot, SocialFeatureSnapshot
from data_operations.domain.entities import ResearchReadinessReport
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
    compare.add_argument("--allow-unready", action="store_true", help="override readiness warning")
    readiness = commands.add_parser("dataset-readiness")
    readiness.add_argument("--market", choices=("BTC-EUR", "ETH-EUR", "SOL-EUR"), default="BTC-EUR")
    readiness.add_argument("--interval", default="1h")
    readiness.add_argument("--start", required=True)
    readiness.add_argument("--end", required=True)
    research = commands.add_parser("research-bot", help="Cost-aware five-horizon local research")
    research.add_argument("--market", choices=("BTC-EUR", "ETH-EUR", "SOL-EUR"), default="BTC-EUR")
    research.add_argument("--start", required=True)
    research.add_argument("--end", required=True)
    research.add_argument("--validation-start", required=True)
    research.add_argument("--test-start", required=True)
    research.add_argument("--fee-per-side", type=float, default=0.0025)
    research.add_argument("--spread-slippage-per-side", type=float, default=0.001)
    research.add_argument("--output", type=Path)
    research.add_argument(
        "--optuna-trials",
        type=int,
        default=0,
        help="0 disables tuning; otherwise 1-100 trials per model",
    )
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
    readiness_report: ResearchReadinessReport | None = None
    if not args.synthetic:
        readiness_report = await _readiness_report(args.market, args.interval, start, end)
        combined = next(
            x for x in readiness_report.groups if x.feature_group == "market_news_social"
        )
        if not combined.ready and not args.allow_unready:
            print("WARNING: combined dataset is not research ready: " + ", ".join(combined.reasons))
            print("Use --allow-unready only for research/debug purposes.")
            return 3
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
    if readiness_report is not None:
        await _freeze_manifest(dataset, readiness_report, commit)
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
    if args.command == "research-bot":
        return asyncio.run(_research_bot(args))
    if args.command == "compare-feature-groups":
        return asyncio.run(_compare(args))
    if args.command == "dataset-readiness":
        return asyncio.run(_print_readiness(args))
    return 2


async def _research_bot(args: argparse.Namespace) -> int:
    from data_collector.infrastructure.persistence import SqlAlchemyNewsRepository
    from data_collector.infrastructure.persistence.session import data_collector_session_factory
    from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
    from data_operations.infrastructure.session import operations_session_factory

    from ai_trainer.application.services.news_alignment import align_news
    from ai_trainer.domain.entities import FeatureConfiguration
    from ai_trainer.training.supervised.bot_research import Costs, run_research

    def utc(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    start, end = utc(args.start), utc(args.end)
    validation, test = utc(args.validation_start), utc(args.test_start)
    if not start < validation < test < end:
        raise ValueError("require start < validation-start < test-start < end")
    if end > datetime.now(UTC):
        raise ValueError("end cannot be in the future")
    repository = SqlAlchemyOperationsRepository(operations_session_factory)
    candles = await repository.candles(args.market, "1h", start, end)
    snapshots = await SqlAlchemyNewsRepository(data_collector_session_factory).feature_snapshots(
        args.market, start - timedelta(minutes=10), end
    )
    safe_snapshots = align_news(
        snapshots, [c.timestamp + timedelta(hours=1) for c in candles], args.market
    )
    dataset = UnifiedDatasetBuilder().build(
        candles,
        DatasetConfiguration(
            args.market, "1h", start, end, feature_configuration=FeatureConfiguration.MARKET_NEWS
        ),
        news=safe_snapshots,
    )
    output = args.output or Path("experiments/results") / f"bot-{args.market}-{uuid4()}"
    report = run_research(
        dataset,
        validation,
        test,
        output,
        Costs(args.fee_per_side, args.spread_slippage_per_side),
        candles=candles,
        optuna_trials=args.optuna_trials,
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "selected_candidate": report["selected_candidate"],
                "bot_action": report["bot_action"],
                "news_comparison": report["news_comparison"],
                "aligned_news_decisions": len(safe_snapshots),
            },
            indent=2,
        )
    )
    return 0


async def _readiness_report(
    market: str, interval: str, start: datetime, end: datetime
) -> ResearchReadinessReport:
    from data_operations.application.readiness import ReadinessQueryService
    from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
    from data_operations.infrastructure.session import operations_session_factory

    return await ReadinessQueryService(
        SqlAlchemyOperationsRepository(operations_session_factory)
    ).report(market, interval, start, end)


async def _print_readiness(args: argparse.Namespace) -> int:
    report = await _readiness_report(
        args.market,
        args.interval,
        datetime.fromisoformat(args.start),
        datetime.fromisoformat(args.end),
    )
    print(
        json.dumps(
            {
                "market": report.market,
                "interval": report.interval,
                "policy": report.policy_version,
                "market_coverage": report.market_coverage,
                "news_uptime": report.news_operational_coverage,
                "social_uptime": report.social_operational_coverage,
                "groups": [
                    {"name": x.feature_group, "ready": x.ready, "reasons": x.reasons}
                    for x in report.groups
                ],
            },
            indent=2,
        )
    )
    return 0


async def _freeze_manifest(
    dataset: object, readiness: ResearchReadinessReport, git_commit: str | None
) -> None:
    from data_operations.domain.entities import DatasetManifest
    from data_operations.infrastructure.repository import SqlAlchemyOperationsRepository
    from data_operations.infrastructure.session import operations_session_factory

    from ai_trainer.domain.entities import UnifiedDataset

    if not isinstance(dataset, UnifiedDataset):
        raise TypeError("expected UnifiedDataset")
    identity = sha256(
        f"{dataset.metadata.fingerprint}:{readiness.policy_version}".encode()
    ).hexdigest()
    await SqlAlchemyOperationsRepository(operations_session_factory).save_manifest(
        DatasetManifest(
            identity,
            dataset.metadata.market,
            dataset.metadata.interval,
            dataset.metadata.start_time,
            dataset.metadata.end_time,
            len(dataset.rows),
            {
                "market": dataset.metadata.market_feature_version,
                "news": dataset.metadata.news_feature_version,
                "social": dataset.metadata.social_feature_version,
                "target": dataset.metadata.target_version,
            },
            dataset.metadata.analyzer_versions,
            {
                "market": readiness.market_coverage,
                "news": readiness.news_operational_coverage,
                "social": readiness.social_operational_coverage,
            },
            dataset.metadata.fingerprint,
            readiness.policy_version,
            datetime.now(UTC),
            git_commit,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
