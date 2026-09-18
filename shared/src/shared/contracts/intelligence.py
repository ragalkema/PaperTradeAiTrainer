"""Cross-project envelope for future point-in-time feature engineering."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ResearchFeatureSnapshot:
    market: str
    timestamp: datetime
    market_features: dict[str, Decimal | int | None]
    news_features: dict[str, Decimal | int | None]
    social_features: dict[str, Decimal | int | None]
    feature_versions: dict[str, str]
