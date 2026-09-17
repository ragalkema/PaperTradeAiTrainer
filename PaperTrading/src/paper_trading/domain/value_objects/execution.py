"""Configurable deterministic execution models."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Fee and adverse slippage rates applied to simulated market orders."""

    fee_rate: Decimal = Decimal("0.0025")
    slippage_rate: Decimal = Decimal("0.0005")

    def __post_init__(self) -> None:
        for name, value in (("fee_rate", self.fee_rate), ("slippage_rate", self.slippage_rate)):
            if not value.is_finite() or value < 0 or value >= 1:
                raise ValueError(f"{name} must be finite and between 0 and 1")
