"""Future immutable raw and normalized storage adapters."""

from data_collector.infrastructure.persistence.models import (
    DataCollectorBase,
    NewsEventModel,
    NewsMarketAssociationModel,
    NewsSourceModel,
    RawNewsItemModel,
)
from data_collector.infrastructure.persistence.repository import SqlAlchemyNewsRepository

__all__ = [
    "DataCollectorBase",
    "NewsEventModel",
    "NewsMarketAssociationModel",
    "NewsSourceModel",
    "RawNewsItemModel",
    "SqlAlchemyNewsRepository",
]
