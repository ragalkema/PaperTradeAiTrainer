"""Transparent, deterministic online news understanding strategies (heuristic v1)."""

import re
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from data_collector.application.services.asset_detection import DEFAULT_ALIASES
from data_collector.domain.entities import (
    AssetSentiment,
    Classification,
    ImportanceResult,
    NewsEvent,
    NewsEventType,
    NoveltyResult,
)

SENTIMENT_VERSION = "lexical_asset_sentiment_v1"
CLASSIFIER_VERSION = "keyword_event_classifier_v1"
IMPORTANCE_VERSION = "transparent_importance_v1"
NOVELTY_VERSION = "chronological_jaccard_v1"

POSITIVE = {
    "approve": 2,
    "approved": 2,
    "approval": 2,
    "gain": 1,
    "gains": 1,
    "surge": 2,
    "adoption": 2,
    "launch": 1,
    "upgrade": 1,
    "record": 1,
    "secure": 1,
    "bullish": 2,
}
NEGATIVE = {
    "hack": -3,
    "hacked": -3,
    "exploit": -3,
    "breach": -3,
    "fraud": -2,
    "ban": -2,
    "lawsuit": -2,
    "liquidation": -2,
    "fall": -1,
    "falls": -1,
    "drop": -1,
    "outflow": -1,
    "bearish": -2,
}

CATEGORY_TERMS: dict[NewsEventType, tuple[str, ...]] = {
    NewsEventType.REGULATION: ("regulation", "regulator", "sec ", "cftc", "government"),
    NewsEventType.ETF: (" etf", "exchange traded fund"),
    NewsEventType.MACRO: ("central bank", "interest rate", "inflation", "federal reserve", "ecb"),
    NewsEventType.SECURITY: ("hack", "exploit", "breach", "stolen", "vulnerability"),
    NewsEventType.EXCHANGE: ("exchange", "binance", "coinbase", "kraken", "bitvavo"),
    NewsEventType.ADOPTION: ("adoption", "accepts bitcoin", "payment integration"),
    NewsEventType.PROTOCOL: ("protocol", "upgrade", "hard fork", "mainnet"),
    NewsEventType.LEGAL: ("lawsuit", "court", "judge", "legal ruling"),
    NewsEventType.STABLECOIN: ("stablecoin", "usdt", "usdc", "depeg"),
    NewsEventType.INSTITUTIONAL: ("institutional", "blackrock", "fidelity", "asset manager"),
    NewsEventType.MARKET_STRUCTURE: ("liquidation", "market maker", "order book"),
    NewsEventType.COMPANY: ("company", "earnings", "acquisition", "corporate"),
    NewsEventType.GENERAL_MARKET: ("market", "price", "rally", "selloff"),
}

SEVERITY = {
    NewsEventType.SECURITY: Decimal("0.35"),
    NewsEventType.REGULATION: Decimal("0.30"),
    NewsEventType.ETF: Decimal("0.30"),
    NewsEventType.MACRO: Decimal("0.28"),
    NewsEventType.LEGAL: Decimal("0.24"),
    NewsEventType.EXCHANGE: Decimal("0.22"),
    NewsEventType.STABLECOIN: Decimal("0.25"),
    NewsEventType.INSTITUTIONAL: Decimal("0.22"),
    NewsEventType.PROTOCOL: Decimal("0.18"),
    NewsEventType.ADOPTION: Decimal("0.18"),
    NewsEventType.MARKET_STRUCTURE: Decimal("0.18"),
    NewsEventType.COMPANY: Decimal("0.12"),
    NewsEventType.GENERAL_MARKET: Decimal("0.05"),
    NewsEventType.OTHER: Decimal("0"),
}


def _words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


class LexicalAssetSentimentAnalyzer:
    """Small transparent baseline; not a transformer or claim of deep language understanding."""

    def analyze(self, event: NewsEvent, processed_at: datetime) -> tuple[AssetSentiment, ...]:
        text = f"{event.title}. {event.summary or ''}"
        sentences = re.split(r"(?<=[.!?;])\s+|\b(?:while|whereas|but)\b", text, flags=re.I)
        results = []
        for asset in event.mentioned_assets:
            aliases = DEFAULT_ALIASES.get(asset, (asset.casefold(),))
            local = [
                part
                for part in sentences
                if any(re.search(rf"\b{re.escape(alias)}\b", part, re.I) for alias in aliases)
            ]
            context = " ".join(local) or text
            words = _words(context)
            raw = sum(POSITIVE.get(word, NEGATIVE.get(word, 0)) for word in words)
            for alias in aliases:
                if re.search(
                    rf"(?:rotate|rotation|flow)\w*\s+out\s+of\s+{re.escape(alias)}\b", context, re.I
                ):
                    raw -= 3
                if re.search(
                    rf"(?:rotate|rotation|flow)\w*\s+(?:in|into)\s+{re.escape(alias)}\b",
                    context,
                    re.I,
                ):
                    raw += 3
            score = max(Decimal("-1"), min(Decimal("1"), Decimal(raw) / Decimal("4")))
            evidence = sum(word in POSITIVE or word in NEGATIVE for word in words)
            confidence = min(Decimal("0.9"), Decimal("0.35") + Decimal(evidence) * Decimal("0.12"))
            results.append(
                AssetSentiment(asset, score, confidence, "lexical", SENTIMENT_VERSION, processed_at)
            )
        return tuple(results)


class KeywordEventClassifier:
    def classify(self, event: NewsEvent) -> Classification:
        text = f" {event.title} {event.summary or ''} ".casefold()
        matches = [
            (kind, sum(term in text for term in terms)) for kind, terms in CATEGORY_TERMS.items()
        ]
        ranked = sorted(
            (item for item in matches if item[1]), key=lambda item: (-item[1], item[0].value)
        )
        if not ranked:
            return Classification(
                NewsEventType.OTHER,
                Decimal("0.3"),
                (),
                "keyword",
                CLASSIFIER_VERSION,
                ("No taxonomy term matched",),
            )
        primary, count = ranked[0]
        confidence = min(Decimal("0.95"), Decimal("0.55") + Decimal(count - 1) * Decimal("0.12"))
        return Classification(
            primary,
            confidence,
            tuple(item[0] for item in ranked[1:4]),
            "keyword",
            CLASSIFIER_VERSION,
            (f"Matched {count} {primary.value} term(s)",),
        )


class TransparentImportanceAnalyzer:
    def analyze(self, event: NewsEvent, classification: Classification) -> ImportanceResult:
        relevance = max(event.asset_relevance.values(), default=Decimal("0"))
        category = SEVERITY[classification.event_type]
        headline = (
            Decimal("0.15")
            if any(asset in event.title.upper() for asset in event.mentioned_assets)
            else Decimal("0")
        )
        breadth = min(Decimal("0.12"), Decimal(len(event.mentioned_assets)) * Decimal("0.04"))
        relevance_factor = relevance * Decimal("0.28")
        score = min(
            Decimal("1"), Decimal("0.08") + category + headline + breadth + relevance_factor
        )
        explanation = (
            "Base +0.08",
            f"{classification.event_type.value} category +{category}",
            f"Headline asset +{headline}",
            f"Asset breadth +{breadth}",
            f"Relevance contribution +{relevance_factor}",
        )
        return ImportanceResult(
            score, Decimal("0.75"), "transparent_heuristic", IMPORTANCE_VERSION, explanation
        )


class ChronologicalNoveltyAnalyzer:
    threshold = Decimal("0.42")

    def analyze(self, event: NewsEvent, prior_events: tuple[NewsEvent, ...]) -> NoveltyResult:
        current = set(_words(f"{event.title} {event.summary or ''}"))
        best_score = Decimal("0")
        best: NewsEvent | None = None
        for prior in prior_events:
            if prior.received_at >= event.received_at:
                continue
            other = set(_words(f"{prior.title} {prior.summary or ''}"))
            union = current | other
            similarity = (
                Decimal(len(current & other)) / Decimal(len(union)) if union else Decimal("0")
            )
            if similarity > best_score:
                best_score, best = similarity, prior
        if best is not None and best_score >= self.threshold:
            cluster = best.story_cluster_id or uuid5(NAMESPACE_URL, f"story:{best.news_event_id}")
            novelty = max(Decimal("0.1"), Decimal("1") - best_score)
            reason = f"Prior story similarity {best_score:.3f}"
        else:
            cluster = uuid5(NAMESPACE_URL, f"story:{event.news_event_id}")
            novelty, reason = Decimal("1"), "No sufficiently similar prior story"
        return NoveltyResult(
            novelty, Decimal("0.8"), cluster, "token_jaccard", NOVELTY_VERSION, (reason,)
        )
