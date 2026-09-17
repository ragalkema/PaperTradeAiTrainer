"""Asynchronous persistence adapter foundation."""

from sqlalchemy.orm import DeclarativeBase

from paper_trading.infrastructure.persistence.file_stores import (
    AppendOnlyRawMarketStore,
    InMemoryCandleRepository,
    JsonlCandleRepository,
)


class Base(DeclarativeBase):
    """Base for future PaperTrading persistence models."""


__all__ = [
    "AppendOnlyRawMarketStore",
    "Base",
    "InMemoryCandleRepository",
    "JsonlCandleRepository",
]
