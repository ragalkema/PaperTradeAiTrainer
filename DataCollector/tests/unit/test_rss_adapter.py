from datetime import UTC, datetime

import pytest
from data_collector.infrastructure.rss.adapter import parse_feed


@pytest.mark.unit
def test_parses_rss_metadata_only() -> None:
    payload = b"""<rss><channel><item><title>Bitcoin update</title>
    <link>https://example.test/a</link><guid>1</guid>
    <description>Short summary</description><pubDate>Fri, 18 Sep 2026 10:00:00 GMT</pubDate>
    </item></channel></rss>"""
    received = datetime(2026, 9, 18, 10, 1, tzinfo=UTC)
    item = parse_feed("example", payload, received)[0]
    assert item.title == "Bitcoin update"
    assert item.summary == "Short summary"
    assert item.published_at < item.received_at
    assert item.raw_metadata == {"categories": ()}


@pytest.mark.unit
def test_parses_atom_feed() -> None:
    payload = b"""<feed xmlns='http://www.w3.org/2005/Atom'><entry><title>ETH update</title>
    <id>urn:1</id><link href='https://example.test/e'/><updated>2026-09-18T10:00:00Z</updated>
    <summary>Summary</summary></entry></feed>"""
    items = parse_feed("example", payload, datetime(2026, 9, 18, 10, 1, tzinfo=UTC))
    assert items[0].external_id == "urn:1"
    assert items[0].url == "https://example.test/e"
