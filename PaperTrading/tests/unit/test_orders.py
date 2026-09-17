"""Paper-order invariant tests."""

from decimal import Decimal

import pytest
from paper_trading.domain.entities import OrderRequest
from shared.contracts import ActionType


@pytest.mark.unit
def test_order_request_is_virtual_and_positive() -> None:
    request = OrderRequest("BTC-EUR", ActionType.BUY, Decimal("0.01"))
    assert request.quantity == Decimal("0.01")
    with pytest.raises(ValueError, match="positive"):
        OrderRequest("BTC-EUR", ActionType.BUY, Decimal("0"))
    with pytest.raises(ValueError, match="not an executable"):
        OrderRequest("BTC-EUR", ActionType.HOLD, Decimal("1"))
