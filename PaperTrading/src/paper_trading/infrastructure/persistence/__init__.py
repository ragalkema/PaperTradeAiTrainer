"""Asynchronous persistence adapter foundation."""

from sqlalchemy.orm import DeclarativeBase

from paper_trading.infrastructure.persistence.file_stores import (
    AppendOnlyRawMarketStore,
    InMemoryCandleRepository,
    JsonlCandleRepository,
)


class Base(DeclarativeBase):
    """Declarative base for PaperTrading-owned tables."""


from paper_trading.infrastructure.persistence.models import (  # noqa: E402
    BotDecisionModel,
    BotDefinitionModel,
    ExperimentModel,
    PaperSessionModel,
    PaperTradeModel,
    PortfolioSnapshotModel,
    PositionModel,
    SessionBotModel,
)
from paper_trading.infrastructure.persistence.research_repository import (  # noqa: E402
    SqlAlchemyResearchRepository,
)

__all__ = [
    "AppendOnlyRawMarketStore",
    "Base",
    "BotDecisionModel",
    "BotDefinitionModel",
    "ExperimentModel",
    "InMemoryCandleRepository",
    "JsonlCandleRepository",
    "PaperSessionModel",
    "PaperTradeModel",
    "PortfolioSnapshotModel",
    "PositionModel",
    "SessionBotModel",
    "SqlAlchemyResearchRepository",
]
