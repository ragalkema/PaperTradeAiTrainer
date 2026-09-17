"""Virtual order states."""

from enum import StrEnum


class PaperOrderStatus(StrEnum):
    """Lifecycle states for virtual orders only."""

    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
