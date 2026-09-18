"""Canonicalization, fingerprinting, timestamp protection, and normalization."""

import hashlib
import html
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

from data_collector.application.services.asset_detection import AssetDetector
from data_collector.domain.entities import NewsEvent, RawNewsItem, RawNewsStatus

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


class NewsNormalizer:
    def __init__(
        self,
        detector: AssetDetector | None = None,
        future_tolerance: timedelta = timedelta(minutes=10),
    ) -> None:
        self._detector = detector or AssetDetector()
        self._future_tolerance = future_tolerance

    def normalize(
        self,
        raw: RawNewsItem,
        source_name: str,
        processed_at: datetime | None = None,
    ) -> NewsEvent:
        processed = processed_at or datetime.now(UTC)
        if raw.published_at > raw.received_at + self._future_tolerance:
            raise FutureTimestampError("published_at exceeds configured future tolerance")
        title = clean_text(raw.title)
        summary = clean_text(raw.summary) if raw.summary else None
        url = canonical_url(raw.url)
        relevance = self._detector.detect(title, summary)
        fingerprint = duplicate_fingerprint(raw.source_id, raw.external_id, title, url)
        return NewsEvent(
            uuid5(NAMESPACE_URL, f"news-event:{raw.raw_item_id}"),
            raw.raw_item_id,
            raw.source_id,
            source_name,
            title,
            url,
            raw.published_at.astimezone(UTC),
            raw.received_at.astimezone(UTC),
            processed.astimezone(UTC),
            tuple(sorted(relevance)),
            relevance,
            detect_language(title, summary),
            summary,
            clean_text(raw.author) if raw.author else None,
            duplicate_group_id=uuid5(NAMESPACE_URL, f"news-duplicate:{fingerprint}"),
        )

    def quarantine(self, raw: RawNewsItem, reason: str) -> RawNewsItem:
        return replace(raw, status=RawNewsStatus.QUARANTINED, quarantine_reason=reason)


class FutureTimestampError(ValueError):
    pass


def canonical_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_PARAMETERS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), "")
    )


def clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html.unescape(value))
    return re.sub(r"\s+", " ", without_tags).strip()


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean_text(value).casefold()).strip()


def duplicate_fingerprint(source_id: str, external_id: str | None, title: str, url: str) -> str:
    # Phase 1 groups articles with the same punctuation/case-normalized headline even when
    # separate providers use different IDs and URLs. Semantic story clustering remains future work.
    del source_id, external_id, url
    payload = normalized_title(title)
    return hashlib.sha256(payload.encode()).hexdigest()


def detect_language(title: str, summary: str | None) -> str:
    text = f"{title} {summary or ''}"
    ascii_letters = sum(character.isascii() and character.isalpha() for character in text)
    letters = sum(character.isalpha() for character in text)
    return (
        "en" if not letters or Decimal(ascii_letters) / Decimal(letters) > Decimal("0.8") else "und"
    )
