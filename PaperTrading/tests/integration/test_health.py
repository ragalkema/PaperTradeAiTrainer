"""PaperTrading API integration test."""

import pytest
from fastapi.testclient import TestClient
from paper_trading.interfaces.api import app


@pytest.mark.integration
def test_health_identifies_paper_mode() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "trading_mode": "paper"}
