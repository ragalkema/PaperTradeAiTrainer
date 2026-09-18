from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from data_collector.domain.entities import SocialAccountCategory, TrackedSocialAccount
from data_collector.infrastructure.social import (
    XRateLimitedError,
    XRecentSearchAdapter,
    parse_x_response,
)


@pytest.mark.unit
def test_x_fixture_parses_pagination_metrics_and_reference_types() -> None:
    payload = {
        "data": [
            {
                "id": "10",
                "author_id": "1",
                "text": "$BTC looks strong",
                "created_at": "2026-09-18T12:00:00Z",
                "lang": "en",
                "referenced_tweets": [{"type": "quoted", "id": "9"}],
                "public_metrics": {"like_count": 12},
            }
        ],
        "includes": {"users": [{"id": "1", "username": "alice", "name": "Alice"}]},
        "meta": {"next_token": "next"},
    }
    posts, token = parse_x_response(payload, datetime(2026, 9, 18, 12, 1, tzinfo=UTC))
    assert token == "next" and posts[0].username == "alice"
    assert posts[0].quote_of == "9" and posts[0].public_metrics == {"like_count": 12}


@pytest.mark.unit
def test_x_fixture_tolerates_missing_metrics_and_empty_deleted_results() -> None:
    post = {"id": "11", "author_id": "1", "text": "ETH", "created_at": "2026-09-18T12:00:00Z"}
    posts, _ = parse_x_response({"data": [post]}, datetime(2026, 9, 18, 12, 1, tzinfo=UTC))
    assert posts[0].public_metrics is None
    assert parse_x_response({"errors": [{"title": "Not Found"}]}, datetime.now(UTC))[0] == ()


@pytest.mark.unit
def test_x_adapter_surfaces_rate_limit_retry_time() -> None:
    async def run() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"retry-after": "60"})
        )
        client = httpx.AsyncClient(transport=transport)
        adapter = XRecentSearchAdapter("token", client)
        now = datetime.now(UTC)
        account = TrackedSocialAccount(
            uuid4(), "x", "1", "alice", None, True, SocialAccountCategory.OTHER, 1, now, now
        )
        with pytest.raises(XRateLimitedError) as captured:
            await adapter.fetch_recent_posts((account,))
        assert captured.value.retry_at and captured.value.retry_at > now
        await client.aclose()

    import asyncio

    asyncio.run(run())
