"""One-shot command-line entry point for the news collector."""

import argparse
import asyncio
import json
import logging
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from data_collector.application.services.collection import NewsCollectionService
from data_collector.application.services.intelligence_pipeline import NewsIntelligenceService
from data_collector.application.services.news_understanding import (
    ChronologicalNoveltyAnalyzer,
    KeywordEventClassifier,
    LexicalAssetSentimentAnalyzer,
    TransparentImportanceAnalyzer,
)
from data_collector.application.services.normalization import NewsNormalizer
from data_collector.application.services.reference_dataset import (
    DatasetTargets,
    ExistingIntelligenceAssessor,
    ReferenceDatasetBuilder,
)
from data_collector.application.services.retrospective_impact import MarketReactionUpdateService
from data_collector.application.services.social_pipeline import (
    SocialAnalysisService,
    SocialCollectionService,
)
from data_collector.application.services.social_retrospective import SocialReactionUpdateService
from data_collector.domain.entities import SocialAccountCategory, TrackedSocialAccount
from data_collector.infrastructure.ai import OpenAIRelevanceAssessor
from data_collector.infrastructure.configuration import get_data_collector_settings
from data_collector.infrastructure.news import default_source_registry
from data_collector.infrastructure.persistence import (
    SqlAlchemyNewsRepository,
    SqlAlchemySocialRepository,
)
from data_collector.infrastructure.persistence.reference_candidates import (
    SqlAlchemyReferenceCandidateRepository,
)
from data_collector.infrastructure.persistence.session import data_collector_session_factory
from data_collector.infrastructure.rss import RssNewsSourceAdapter
from data_collector.infrastructure.social import XRecentSearchAdapter


async def collect_once() -> int:
    repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    registry = default_source_registry()
    adapters = tuple(RssNewsSourceAdapter(source) for source in registry.enabled())
    try:
        results = await asyncio.gather(
            *(
                NewsCollectionService(repository, NewsNormalizer()).collect(adapter)
                for adapter in adapters
            )
        )
    finally:
        await asyncio.gather(*(adapter.aclose() for adapter in adapters))
    logging.info(
        "news_collection_complete received=%d stored=%d events=%d duplicates=%d quarantined=%d",
        sum(item.fetched for item in results),
        sum(item.stored_raw for item in results),
        sum(item.normalized for item in results),
        sum(item.duplicates for item in results),
        sum(item.quarantined for item in results),
    )
    return 0 if not any(item.failed for item in results) else 1


async def analyze_news(limit: int) -> int:
    repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    service = NewsIntelligenceService(
        repository,
        LexicalAssetSentimentAnalyzer(),
        TransparentImportanceAnalyzer(),
        KeywordEventClassifier(),
        ChronologicalNoveltyAnalyzer(),
    )
    stored = await service.analyze_pending(limit)
    logging.info("news_analysis_complete intelligence_records=%d", stored)
    return 0


async def update_market_reactions(limit: int) -> int:
    repository = SqlAlchemyNewsRepository(data_collector_session_factory)
    events = await repository.recent_news(since=datetime.now(UTC) - timedelta(days=30), limit=limit)
    service = MarketReactionUpdateService(repository)
    stored = sum(
        [await service.update_event(event.news_event_id, datetime.now(UTC)) for event in events]
    )
    logging.info("market_impact_update_complete records=%d", stored)
    return 0


async def social_once() -> int:
    token = get_data_collector_settings().x_api_bearer_token
    if not token:
        logging.error("X_API_BEARER_TOKEN is not configured")
        return 2
    repository = SqlAlchemySocialRepository(data_collector_session_factory)
    adapter = XRecentSearchAdapter(token)
    try:
        stored = await SocialCollectionService(repository).collect(adapter)
    finally:
        await adapter.aclose()
    logging.info("social_collection_complete events=%d", stored)
    return 0


async def analyze_social_command(limit: int) -> int:
    stored = await SocialAnalysisService(
        SqlAlchemySocialRepository(data_collector_session_factory)
    ).analyze_pending(limit)
    logging.info("social_analysis_complete records=%d", stored)
    return 0


async def update_social_reactions(limit: int) -> int:
    repository = SqlAlchemySocialRepository(data_collector_session_factory)
    events = await repository.recent_social(datetime.now(UTC) - timedelta(days=30), limit)
    service = SocialReactionUpdateService(repository)
    stored = sum([await service.update_event(x.social_event_id, datetime.now(UTC)) for x in events])
    logging.info("social_impact_update_complete records=%d", stored)
    return 0


async def social_accounts(action: str, value: str | None) -> int:
    repository = SqlAlchemySocialRepository(data_collector_session_factory)
    if action == "list":
        for account in await repository.tracked_accounts(False):
            print(
                f"{account.username}\t{account.category.value}\t"
                f"{'enabled' if account.enabled else 'disabled'}"
            )
        return 0
    if action in {"enable", "disable"}:
        if not value:
            raise ValueError("username is required")
        await repository.set_account_enabled(value, action == "enable")
        return 0
    if not value:
        raise ValueError("JSON path is required")
    now = datetime.now(UTC)
    for item in json.loads(Path(value).read_text(encoding="utf-8")):
        username = str(item["username"])
        await repository.add_account(
            TrackedSocialAccount(
                uuid5(
                    NAMESPACE_URL,
                    f"social-account:{item.get('provider', 'x')}:{username.casefold()}",
                ),
                str(item.get("provider", "x")),
                None,
                username,
                str(item.get("display_name")) if item.get("display_name") else None,
                bool(item.get("enabled", False)),
                SocialAccountCategory(str(item.get("category", "other"))),
                int(item.get("priority", 0)),
                now,
                now,
            )
        )
    return 0


async def build_reference_dataset(
    output: Path,
    total: int,
    influential: int,
    low_value: int,
    use_ai: bool,
) -> int:
    candidates = await SqlAlchemyReferenceCandidateRepository(
        data_collector_session_factory
    ).candidates(max(total * 2, 20_000))
    assessor: ExistingIntelligenceAssessor | OpenAIRelevanceAssessor
    ai: OpenAIRelevanceAssessor | None = None
    if use_ai:
        settings = get_data_collector_settings()
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("--ai requires OPENAI_API_KEY")
        ai = OpenAIRelevanceAssessor(api_key, settings.openai_relevance_model)
        assessor = ai
    else:
        assessor = ExistingIntelligenceAssessor()
    try:
        rows, report = await ReferenceDatasetBuilder().build(
            candidates, assessor, DatasetTargets(total, influential, low_value)
        )
    finally:
        if ai:
            await ai.aclose()
    ReferenceDatasetBuilder.write_jsonl(rows, output)
    print(json.dumps({**asdict(report), "output": str(output)}, sort_keys=True))
    return 0 if report.shortfall == 0 else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="PaperTradeAiTrainer data collection")
    parser.add_argument(
        "command",
        choices=(
            "news-once",
            "analyze-news",
            "update-market-reactions",
            "social-once",
            "analyze-social",
            "update-social-reactions",
            "social-accounts",
            "build-reference-dataset",
        ),
    )
    parser.add_argument("action", nargs="?", choices=("list", "import", "enable", "disable"))
    parser.add_argument("value", nargs="?")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--output", type=Path, default=Path("data/reference/market_relevance.jsonl")
    )
    parser.add_argument("--total", type=int, default=10_000)
    parser.add_argument("--influential", type=int, default=2_000)
    parser.add_argument("--low-value", type=int, default=4_000)
    parser.add_argument("--ai", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "news-once":
        return asyncio.run(collect_once())
    if args.command == "analyze-news":
        return asyncio.run(analyze_news(args.limit))
    if args.command == "update-market-reactions":
        return asyncio.run(update_market_reactions(args.limit))
    if args.command == "social-once":
        return asyncio.run(social_once())
    if args.command == "analyze-social":
        return asyncio.run(analyze_social_command(args.limit))
    if args.command == "update-social-reactions":
        return asyncio.run(update_social_reactions(args.limit))
    if args.command == "build-reference-dataset":
        return asyncio.run(
            build_reference_dataset(
                args.output, args.total, args.influential, args.low_value, args.ai
            )
        )
    return asyncio.run(social_accounts(args.action or "list", args.value))
