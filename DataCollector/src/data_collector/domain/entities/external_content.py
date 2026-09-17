"""Minimal source-neutral external content entity."""

from dataclasses import dataclass

from data_collector.domain.enums import SourceType
from data_collector.domain.value_objects import EventTimes


@dataclass(frozen=True, slots=True)
class ExternalContent:
    """Raw textual observation before provider-specific normalization."""

    source_id: str
    source_type: SourceType
    content: str
    times: EventTimes

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.content.strip():
            raise ValueError("content must not be empty")
