from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from paper_trading.domain.entities import BotDecisionRecord, DecisionContextRecord
from shared.contracts import ActionType, MarketSymbol


@pytest.mark.unit
def test_decision_rejects_lookahead_context() -> None:
    decision_time = datetime(2026, 1, 1, tzinfo=UTC)
    context = DecisionContextRecord(
        decision_time + timedelta(seconds=1),
        Decimal("100"),
        Decimal("99"),
        Decimal("101"),
        Decimal("2"),
        Decimal("10000"),
        Decimal("10000"),
        Decimal("0"),
    )
    with pytest.raises(ValueError, match="future"):
        BotDecisionRecord(
            uuid4(),
            uuid4(),
            uuid4(),
            decision_time,
            MarketSymbol("BTC-EUR"),
            ActionType.HOLD,
            Decimal("0"),
            context,
        )
