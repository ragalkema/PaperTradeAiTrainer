"""X API v2 recent-search adapter; X-specific fields stop at this boundary."""

import hashlib
import json
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from uuid import NAMESPACE_URL, uuid5

import httpx

from data_collector.domain.entities import RawSocialPost, TrackedSocialAccount


class XRateLimitedError(RuntimeError):
    def __init__(self, retry_at: datetime | None) -> None:
        super().__init__("X API rate limited")
        self.retry_at = retry_at


class XRecentSearchAdapter:
    endpoint = "https://api.x.com/2/tweets/search/recent"

    def __init__(self, bearer_token: str, client: httpx.AsyncClient | None = None) -> None:
        if not bearer_token:
            raise ValueError("X_API_BEARER_TOKEN is required")
        self._client = client or httpx.AsyncClient(
            timeout=20, headers={"Authorization": f"Bearer {bearer_token}"}
        )
        self._owns = client is None

    async def aclose(self) -> None:
        if self._owns:
            await self._client.aclose()

    async def fetch_recent_posts(
        self,
        accounts: tuple[TrackedSocialAccount, ...],
        *,
        start_time: datetime | None = None,
        pagination_token: str | None = None,
    ) -> tuple[tuple[RawSocialPost, ...], str | None]:
        usernames = [item.username.lstrip("@") for item in accounts if item.enabled]
        if not usernames:
            return (), None
        params = {
            "query": "(" + " OR ".join(f"from:{name}" for name in usernames[:25]) + ")",
            "max_results": "100",
            "tweet.fields": (
                "id,text,author_id,created_at,lang,referenced_tweets,"
                "public_metrics,edit_history_tweet_ids"
            ),
            "expansions": "author_id",
            "user.fields": "id,username,name,public_metrics,verified,verified_type",
        }
        if start_time:
            params["start_time"] = start_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if pagination_token:
            params["next_token"] = pagination_token
        response = await self._client.get(self.endpoint, params=params)
        if response.status_code == 429:
            reset = response.headers.get("x-rate-limit-reset")
            retry = (
                datetime.fromtimestamp(int(reset), UTC)
                if reset
                else _retry_after(response.headers.get("retry-after"))
            )
            raise XRateLimitedError(retry)
        response.raise_for_status()
        return parse_x_response(response.json(), datetime.now(UTC))


def parse_x_response(
    payload: dict[str, object], received_at: datetime
) -> tuple[tuple[RawSocialPost, ...], str | None]:
    includes = payload.get("includes", {})
    users = (
        {str(item["id"]): item for item in includes.get("users", [])}
        if isinstance(includes, dict)
        else {}
    )
    output = []
    data = payload.get("data", [])
    posts = data if isinstance(data, list) else []
    for post in posts:
        if not isinstance(post, dict):
            continue
        author = str(post.get("author_id", ""))
        user = users.get(author, {})
        references = {
            str(item.get("type")): str(item.get("id")) for item in post.get("referenced_tweets", [])
        }
        preserved = dict(post)
        digest = hashlib.sha256(json.dumps(preserved, sort_keys=True).encode()).hexdigest()
        external = str(post["id"])
        output.append(
            RawSocialPost(
                uuid5(NAMESPACE_URL, f"raw-social:x:{external}:{digest}"),
                "x",
                external,
                author,
                str(user.get("username", author)),
                str(post.get("text", "")),
                datetime.fromisoformat(str(post["created_at"]).replace("Z", "+00:00")),
                received_at,
                digest,
                str(post.get("lang")) if post.get("lang") else None,
                references.get("replied_to"),
                references.get("quoted"),
                references.get("retweeted"),
                post.get("public_metrics")
                if isinstance(post.get("public_metrics"), dict)
                else None,
                {"edit_history_post_ids": post.get("edit_history_tweet_ids", [])},
            )
        )
    meta = payload.get("meta", {})
    token = str(meta["next_token"]) if isinstance(meta, dict) and meta.get("next_token") else None
    return tuple(output), token


def _retry_after(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        from datetime import timedelta

        return datetime.now(UTC) + timedelta(seconds=int(value))
    except ValueError:
        try:
            return parsedate_to_datetime(value).astimezone(UTC)
        except ValueError:
            return None
