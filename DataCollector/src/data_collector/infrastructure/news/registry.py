"""Configurable registry of intentionally small, structured public news sources."""

from data_collector.domain.entities import NewsSource, NewsSourceKind

DEFAULT_SOURCES = (
    NewsSource(
        "coindesk",
        "CoinDesk",
        NewsSourceKind.RSS,
        True,
        100,
        300,
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ),
    NewsSource(
        "cointelegraph",
        "Cointelegraph",
        NewsSourceKind.RSS,
        True,
        90,
        300,
        "https://cointelegraph.com/rss",
    ),
    NewsSource("decrypt", "Decrypt", NewsSourceKind.RSS, True, 80, 300, "https://decrypt.co/feed"),
    NewsSource(
        "theblock",
        "The Block",
        NewsSourceKind.RSS,
        True,
        70,
        300,
        "https://www.theblock.co/rss.xml",
    ),
    NewsSource(
        "newsbtc", "NewsBTC", NewsSourceKind.RSS, True, 65, 300, "https://www.newsbtc.com/feed/"
    ),
    NewsSource(
        "blockworks", "Blockworks", NewsSourceKind.RSS, True, 65, 300, "https://blockworks.com/feed"
    ),
    NewsSource(
        "dlnews",
        "DL News",
        NewsSourceKind.RSS,
        True,
        65,
        300,
        "https://www.dlnews.com/arc/outboundfeeds/rss/",
    ),
    NewsSource(
        "bitcoincom",
        "Bitcoin.com News",
        NewsSourceKind.RSS,
        True,
        55,
        300,
        "https://news.bitcoin.com/feed/",
    ),
    NewsSource("utoday", "U.Today", NewsSourceKind.RSS, True, 50, 300, "https://u.today/rss.php"),
    NewsSource(
        "cryptopotato",
        "CryptoPotato",
        NewsSourceKind.RSS,
        True,
        50,
        300,
        "https://cryptopotato.com/feed/",
    ),
)


class NewsSourceRegistry:
    def __init__(self, sources: tuple[NewsSource, ...] = DEFAULT_SOURCES) -> None:
        identifiers = [item.source_id for item in sources]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("news source IDs must be unique")
        self._sources = sources

    def enabled(self) -> tuple[NewsSource, ...]:
        return tuple(
            sorted(
                (item for item in self._sources if item.enabled),
                key=lambda item: (-item.priority, item.source_id),
            )
        )

    def get(self, source_id: str) -> NewsSource:
        try:
            return next(item for item in self._sources if item.source_id == source_id)
        except StopIteration as exc:
            raise KeyError(source_id) from exc
