from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from paper_trading import PaperTradingSession
from paper_trading.application.services.recording_policy import RecordingPolicy
from paper_trading.application.services.research_recorder import ResearchRunRecorder
from shared.contracts import BotAction, MarketState, MarketSymbol


@pytest.mark.integration
def test_recorder_captures_exact_decision_trade_snapshot_and_position() -> None:
    session_id, bot_id = uuid4(), uuid4()
    recorder = ResearchRunRecorder(
        session_id, {"BuyBot": bot_id}, RecordingPolicy(timedelta(seconds=1))
    )
    paper = PaperTradingSession(Decimal("10000"), Decimal("0"), Decimal("0"))
    state = MarketState(
        MarketSymbol("BTC-EUR"),
        datetime(2026, 1, 1, tzinfo=UTC),
        Decimal("100"),
        Decimal("99"),
        Decimal("101"),
    )
    paper.update_market(state)
    action = BotAction.buy(state.market, Decimal("1000"))
    result = paper.execute(action)
    recorder.on_step("BuyBot", state, action, result, paper.portfolio())
    assert len(recorder.trades) == len(recorder.decisions) == len(recorder.snapshots) == 1
    assert len(recorder.positions) == 1
    assert recorder.decisions[0].context.market_timestamp == state.timestamp
    assert recorder.decisions[0].executed_trade_id == recorder.trades[0].trade_id
    assert recorder.positions[0].average_entry_price == Decimal("101")
    assert recorder.positions[0].session_bot_id == bot_id
