"""Small validated financial value objects shared across boundaries."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True, order=True)
class AssetSymbol:
    """Upper-case asset identifier such as BTC or EUR."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("asset symbol must be non-empty and alphanumeric")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class MarketSymbol:
    """Base/quote market identifier such as BTC-EUR."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        parts = normalized.split("-")
        if len(parts) != 2:
            raise ValueError("market symbol must use BASE-QUOTE format")
        AssetSymbol(parts[0])
        AssetSymbol(parts[1])
        object.__setattr__(self, "value", normalized)

    @property
    def base(self) -> AssetSymbol:
        return AssetSymbol(self.value.split("-", maxsplit=1)[0])

    @property
    def quote(self) -> AssetSymbol:
        return AssetSymbol(self.value.split("-", maxsplit=1)[1])

    def __str__(self) -> str:
        return self.value


def require_positive(value: Decimal, name: str) -> Decimal:
    """Reject non-finite or non-positive financial values."""
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


Money = Decimal
Quantity = Decimal
Price = Decimal
