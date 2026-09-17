"""Tests for paper-exchange and experiment contracts."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.bots.models import ActionType
from app.experiments.models import ExperimentSpec
from app.paper_exchange.models import OrderRequest, PaperOrder, PaperOrderStatus


def test_paper_order_records_only_virtual_order_data() -> None:
    request = OrderRequest(symbol="BTC-EUR", side=ActionType.BUY, quantity=Decimal("0.1"))
    order = PaperOrder(
        order_id=uuid4(),
        request=request,
        status=PaperOrderStatus.PENDING,
        created_at=datetime.now(UTC),
    )

    assert order.request.symbol == "BTC-EUR"
    assert order.status is PaperOrderStatus.PENDING


def test_order_request_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        OrderRequest(symbol="BTC-EUR", side=ActionType.SELL, quantity=Decimal("0"))


def test_experiment_spec_preserves_reproducibility_metadata() -> None:
    start = datetime.now(UTC)
    spec = ExperimentSpec(
        experiment_id=uuid4(),
        bot_id="baseline",
        bot_version="1",
        strategy="buy-and-hold",
        starting_balance=Decimal("10000"),
        start_time=start,
        end_time=start + timedelta(days=1),
        market="BTC-EUR",
        configuration={"interval": "1m"},
        random_seed=42,
        feature_version="v1",
        code_version="abc123",
    )

    assert spec.random_seed == 42
    assert spec.configuration == {"interval": "1m"}
