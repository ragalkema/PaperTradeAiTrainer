"""Generic RSS/Atom adapter using only structured feed metadata."""

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Literal, overload
from uuid import NAMESPACE_URL, uuid5

import httpx

from data_collector.domain.entities import NewsSource, RawNewsItem


class RssNewsSourceAdapter:
    def __init__(
        self,
        source: NewsSource,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15,
    ) -> None:
        self._source = source
        self._client = client or httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "PaperTradeAiTrainer/0.3 research RSS reader"},
        )
        self._owns_client = client is None

    @property
    def source(self) -> NewsSource:
        return self._source

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_latest(self, received_at: datetime | None = None) -> tuple[RawNewsItem, ...]:
        observed = received_at or datetime.now(UTC)
        response = await self._client.get(self._source.feed_url)
        response.raise_for_status()
        return parse_feed(self._source.source_id, response.content, observed)


def parse_feed(source_id: str, payload: bytes, received_at: datetime) -> tuple[RawNewsItem, ...]:
    if received_at.tzinfo is None:
        raise ValueError("received_at must be timezone-aware")
    root = ET.fromstring(payload)
    items = root.findall(".//item")
    if items:
        return tuple(_rss_item(source_id, item, received_at) for item in items)
    entries = root.findall("{*}entry")
    return tuple(_atom_entry(source_id, entry, received_at) for entry in entries)


def _rss_item(source_id: str, item: ET.Element, received_at: datetime) -> RawNewsItem:
    title = _text(item, "title")
    link = _text(item, "link")
    guid = _text(item, "guid", required=False) or link
    published = _timestamp(
        _text(item, "pubDate", required=False) or _text(item, "{*}published", required=False),
        received_at,
    )
    summary = _text(item, "description", required=False)
    author = _text(item, "{*}creator", required=False) or _text(item, "author", required=False)
    categories = tuple(
        text for node in item.findall("category") if (text := (node.text or "").strip())
    )
    return _raw(source_id, guid, title, summary, link, author, published, received_at, categories)


def _atom_entry(source_id: str, entry: ET.Element, received_at: datetime) -> RawNewsItem:
    title = _text(entry, "{*}title")
    link_node = entry.find("{*}link")
    link = link_node.attrib.get("href", "") if link_node is not None else ""
    external_id = _text(entry, "{*}id", required=False) or link
    published = _timestamp(
        _text(entry, "{*}published", required=False) or _text(entry, "{*}updated", required=False),
        received_at,
    )
    summary = _text(entry, "{*}summary", required=False)
    author = _text(entry, "{*}author/{*}name", required=False)
    return _raw(source_id, external_id, title, summary, link, author, published, received_at, ())


def _raw(
    source_id: str,
    external_id: str,
    title: str,
    summary: str | None,
    url: str,
    author: str | None,
    published_at: datetime,
    received_at: datetime,
    categories: tuple[str, ...],
) -> RawNewsItem:
    preserved = {
        "external_id": external_id,
        "title": title,
        "summary": summary,
        "url": url,
        "author": author,
        "published_at": published_at.isoformat(),
        "categories": categories,
    }
    content_hash = hashlib.sha256(
        json.dumps(preserved, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    raw_id = uuid5(NAMESPACE_URL, f"raw-news:{source_id}:{content_hash}")
    return RawNewsItem(
        raw_id,
        source_id,
        title,
        url,
        published_at,
        received_at.astimezone(UTC),
        content_hash,
        external_id,
        summary,
        author,
        {"categories": categories},
    )


def _timestamp(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback.astimezone(UTC)
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@overload
def _text(parent: ET.Element, path: str, required: Literal[True] = True) -> str: ...


@overload
def _text(parent: ET.Element, path: str, required: Literal[False]) -> str | None: ...


def _text(parent: ET.Element, path: str, required: bool = True) -> str | None:
    node = parent.find(path)
    value = "" if node is None else "".join(node.itertext()).strip()
    if required and not value:
        raise ValueError(f"RSS item missing {path}")
    return value or None
