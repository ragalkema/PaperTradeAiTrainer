"""Deterministic provider-neutral social normalization and online analysis."""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from data_collector.application.services.asset_detection import DEFAULT_ALIASES, AssetDetector
from data_collector.domain.entities import (
    RawSocialPost,
    SocialAccountCategory,
    SocialEvent,
    SocialEventType,
    SocialIntelligence,
    SocialPostType,
    TrackedSocialAccount,
    VerificationStatus,
)

SOCIAL_SENTIMENT_VERSION = "lexical_social_asset_sentiment_v1"
SOCIAL_RELEVANCE_VERSION = "social_relevance_v1"
SOCIAL_CLASSIFIER_VERSION = "social_event_classifier_v1"
SOCIAL_IMPORTANCE_VERSION = "social_importance_v1"
SOCIAL_NOVELTY_VERSION = "social_chronological_jaccard_v1"
INFLUENCE_VERSION = "estimated_account_influence_v1"
POS = {
    "bullish": 2,
    "stronger": 2,
    "approve": 2,
    "approved": 2,
    "gain": 1,
    "surge": 2,
    "launch": 1,
    "buy": 1,
}
NEG = {
    "bearish": -2,
    "weaker": -2,
    "hack": -3,
    "hacked": -3,
    "exploit": -3,
    "drop": -1,
    "sell": -1,
    "fraud": -2,
}


def normalize_social(
    raw: RawSocialPost,
    account: TrackedSocialAccount,
    processed_at: datetime | None = None,
    tolerance: timedelta = timedelta(minutes=10),
) -> SocialEvent:
    if raw.created_at > raw.received_at + tolerance:
        raise ValueError("created_at exceeds future tolerance")
    detected = AssetDetector().detect(raw.text)
    relevance = {
        asset: (Decimal("0.95") if re.search(rf"\${asset}\b", raw.text, re.I) else score)
        for asset, score in detected.items()
    }
    kind = (
        SocialPostType.REPOST
        if raw.repost_of
        else SocialPostType.QUOTE
        if raw.quote_of
        else SocialPostType.REPLY
        if raw.reply_to
        else SocialPostType.ORIGINAL
    )
    return SocialEvent(
        uuid5(NAMESPACE_URL, f"social:{raw.provider}:{raw.external_post_id}"),
        raw.raw_post_id,
        raw.provider,
        account.account_id,
        raw.external_post_id,
        raw.username,
        raw.text,
        raw.created_at,
        raw.received_at,
        processed_at or datetime.now(UTC),
        raw.language or "und",
        tuple(sorted(relevance)),
        relevance,
        kind,
        raw.reply_to,
        raw.quote_of,
        raw.repost_of,
    )


def account_influence(account: TrackedSocialAccount) -> tuple[Decimal, tuple[str, ...]]:
    followers = Decimal(str(min(1, (account.followers or 0) / 1_000_000)))
    engagement = min(Decimal("1"), (account.typical_engagement or 0) / Decimal("5000"))
    activity = min(Decimal("1"), (account.posts_per_day or 0) / Decimal("20"))
    category = (
        Decimal("0.15")
        if account.category
        in {
            SocialAccountCategory.REGULATOR,
            SocialAccountCategory.INSTITUTION,
            SocialAccountCategory.PROJECT,
            SocialAccountCategory.EXCHANGE,
        }
        else Decimal("0.08")
    )
    score = min(
        Decimal("1"),
        followers * Decimal("0.4")
        + engagement * Decimal("0.3")
        + activity * Decimal("0.15")
        + category,
    )
    return score, (
        f"Follower scale {followers}",
        f"Typical engagement {engagement}",
        f"Activity {activity}",
        f"Category contribution {category}",
    )


def analyze_social(
    event: SocialEvent,
    account: TrackedSocialAccount,
    prior: tuple[SocialEvent, ...],
    processed_at: datetime | None = None,
) -> tuple[SocialIntelligence, ...]:
    text = event.text.casefold()
    words = re.findall(r"[a-z0-9]+", text)
    influence, influence_explanation = account_influence(account)
    mapping = (
        (SocialEventType.RUMOR, ("rumor", "unconfirmed", "reportedly")),
        (SocialEventType.SECURITY, ("hack", "exploit", "breach")),
        (SocialEventType.ETF, (" etf",)),
        (SocialEventType.REGULATION, ("regulation", " sec ", "regulator")),
        (SocialEventType.PRICE_PREDICTION, ("target", "prediction", "will hit")),
        (SocialEventType.ANNOUNCEMENT, ("announce", "launch", "official")),
        (SocialEventType.MARKET_OPINION, ("bullish", "bearish", "stronger", "weaker")),
    )
    matched = next(
        ((kind, terms) for kind, terms in mapping if any(term in f" {text} " for term in terms)),
        None,
    )
    event_type = matched[0] if matched else SocialEventType.OTHER
    event_conf = Decimal("0.75") if matched else Decimal("0.35")
    current = set(words)
    similarities = []
    for old in prior:
        if old.received_at < event.received_at:
            other = set(re.findall(r"[a-z0-9]+", old.text.casefold()))
            similarities.append(
                Decimal(len(current & other)) / Decimal(len(current | other))
                if current | other
                else Decimal("0")
            )
    similarity = max(similarities, default=Decimal("0"))
    novelty = (
        Decimal("0.2")
        if event.post_type is SocialPostType.REPOST
        else max(Decimal("0.1"), Decimal("1") - similarity)
    )
    official = account.category in {
        SocialAccountCategory.REGULATOR,
        SocialAccountCategory.COMPANY,
        SocialAccountCategory.PROJECT,
        SocialAccountCategory.EXCHANGE,
    }
    verification = (
        VerificationStatus.OFFICIAL_SOURCE
        if official
        else VerificationStatus.CLAIM
        if event_type is SocialEventType.RUMOR
        else VerificationStatus.UNKNOWN
    )
    output = []
    when = processed_at or datetime.now(UTC)
    for asset in event.mentioned_assets:
        aliases = DEFAULT_ALIASES.get(asset, (asset.casefold(),))
        raw_score = sum(POS.get(word, NEG.get(word, 0)) for word in words)
        for alias in aliases:
            if re.search(rf"{re.escape(alias)}\s+(?:looks\s+)?stronger\s+than", text):
                raw_score += 2
            if re.search(rf"stronger\s+than\s+{re.escape(alias)}", text):
                raw_score -= 2
        sentiment = max(Decimal("-1"), min(Decimal("1"), Decimal(raw_score) / 4))
        confidence = min(
            Decimal("0.9"),
            Decimal("0.4") + Decimal(sum(w in POS or w in NEG for w in words)) * Decimal("0.1"),
        )
        category_weight = (
            Decimal("0.25")
            if event_type
            in {
                SocialEventType.SECURITY,
                SocialEventType.REGULATION,
                SocialEventType.ETF,
                SocialEventType.ANNOUNCEMENT,
            }
            else Decimal("0.08")
        )
        importance = min(
            Decimal("1"),
            Decimal("0.08")
            + event.asset_relevance[asset] * Decimal("0.3")
            + influence * Decimal("0.2")
            + novelty * Decimal("0.17")
            + category_weight,
        )
        identifier = uuid5(
            NAMESPACE_URL,
            f"social-intelligence:{event.social_event_id}:{asset}:{SOCIAL_SENTIMENT_VERSION}",
        )
        output.append(
            SocialIntelligence(
                identifier,
                event.social_event_id,
                asset,
                event.asset_relevance[asset],
                sentiment,
                confidence,
                importance,
                event_type,
                event_conf,
                novelty,
                influence,
                verification,
                SOCIAL_SENTIMENT_VERSION,
                SOCIAL_RELEVANCE_VERSION,
                SOCIAL_IMPORTANCE_VERSION,
                SOCIAL_CLASSIFIER_VERSION,
                SOCIAL_NOVELTY_VERSION,
                INFLUENCE_VERSION,
                when,
                {
                    "influence": influence_explanation,
                    "importance": (
                        f"Relevance {event.asset_relevance[asset]}",
                        f"Influence {influence}",
                        f"Novelty {novelty}",
                        f"Category {category_weight}",
                    ),
                },
            )
        )
    return tuple(output)
