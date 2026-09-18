import pytest
from dashboard.application.view_models import ConnectionState
from dashboard.infrastructure.paper_trading import LiveDashboardRepository


@pytest.mark.integration
def test_repository_starts_with_honest_connection_states() -> None:
    snapshot = LiveDashboardRepository(("BTC-EUR",)).snapshot()
    assert snapshot.markets[0].current_price is None
    assert snapshot.connections["Bitvavo"] is ConnectionState.CONNECTING
    assert snapshot.connections["News"] is ConnectionState.DISABLED
