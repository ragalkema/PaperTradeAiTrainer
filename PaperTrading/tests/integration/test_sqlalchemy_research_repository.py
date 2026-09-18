import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from paper_trading import PaperTradingSession
from paper_trading.application.services.experiment_persistence import (
    BotRegistration,
    ExperimentPersistenceService,
    ExperimentRegistration,
)
from paper_trading.infrastructure.persistence import Base, SqlAlchemyResearchRepository
from shared.contracts import BotAction, MarketState, MarketSymbol
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.integration
def test_repository_round_trip_queries_and_performance() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        repository = SqlAlchemyResearchRepository(sessions)
        service = ExperimentPersistenceService(repository)
        start = datetime(2026, 1, 1, tzinfo=UTC)
        run = await service.start(
            ExperimentRegistration(
                "Round trip",
                "Repository integration",
                (MarketSymbol("BTC-EUR"),),
                start,
                start + timedelta(hours=1),
                Decimal("10000"),
                Decimal("0"),
                Decimal("0"),
                7,
                (BotRegistration("BuyBot", "baseline", "1"),),
            )
        )
        paper = PaperTradingSession(Decimal("10000"), Decimal("0"), Decimal("0"))
        state = MarketState(
            MarketSymbol("BTC-EUR"), start, Decimal("100"), Decimal("100"), Decimal("100")
        )
        paper.update_market(state)
        action = BotAction.buy(state.market, Decimal("1000"))
        result = paper.execute(action)
        run.recorder.on_step("BuyBot", state, action, result, paper.portfolio())
        await service.complete(run)

        experiment = await repository.experiment(run.experiment_id)
        participants = await repository.session_bots(run.session_id)
        assert experiment and experiment.name == "Round trip"
        assert len(participants) == 1
        participant = participants[0]
        assert (await repository.current_portfolio(participant.session_bot_id)) is not None
        assert len(await repository.recent_trades(run.session_id)) == 1
        assert len(await repository.decisions(participant.session_bot_id)) == 1
        assert len(await repository.open_positions(participant.session_bot_id)) == 1
        performance = await repository.performance(participant.session_bot_id)
        assert performance and performance.trade_count == 1
        await engine.dispose()

    asyncio.run(scenario())
