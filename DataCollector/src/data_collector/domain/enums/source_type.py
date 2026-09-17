"""External content source categories."""

from enum import StrEnum


class SourceType(StrEnum):
    """Supported conceptual sources; no collector is implemented yet."""

    NEWS = "news"
    SOCIAL = "social"
    RSS = "rss"
    API = "api"
