"""Executable financial validation smoke test."""

import pytest

from validation.system.check_paper_trading import paper_trading_violations


@pytest.mark.validation
def test_paper_trading_financial_invariants() -> None:
    assert paper_trading_violations() == []
