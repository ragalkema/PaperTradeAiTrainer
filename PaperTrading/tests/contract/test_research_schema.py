from paper_trading.infrastructure.persistence import Base
from sqlalchemy import Numeric


def test_research_schema_has_expected_tables_and_decimal_money() -> None:
    expected = {
        "paper_sessions",
        "bot_definitions",
        "session_bots",
        "portfolio_snapshots",
        "paper_positions",
        "paper_trades",
        "bot_decisions",
        "experiments",
    }
    assert expected <= set(Base.metadata.tables)
    trade = Base.metadata.tables["paper_trades"]
    for name in ("market_price", "execution_price", "gross_value", "fee", "realized_pnl"):
        column_type = trade.c[name].type
        assert isinstance(column_type, Numeric)
        assert column_type.precision == 38
        assert column_type.scale == 18
