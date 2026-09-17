"""Validate core paper-account conservation using a deterministic round trip."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from paper_trading import PaperTradingSession
from shared.contracts import BotAction, MarketState, MarketSymbol


def paper_trading_violations() -> list[str]:
    """Return violations of externally observable paper-account invariants."""
    market = MarketSymbol("BTC-EUR")
    start = datetime(2026, 1, 1, tzinfo=UTC)
    session = PaperTradingSession(Decimal("10000"), Decimal("0.0025"), Decimal("0.0005"))
    session.update_market(
        MarketState(
            market,
            start,
            Decimal("100000"),
            Decimal("99990"),
            Decimal("100010"),
        )
    )
    buy = session.execute(BotAction.buy(market, Decimal("1000")))
    session.update_market(
        MarketState(
            market,
            start + timedelta(minutes=1),
            Decimal("105000"),
            Decimal("104990"),
            Decimal("105010"),
        )
    )
    sell = session.execute(BotAction.sell(market, buy.quantity))
    portfolio = session.portfolio()
    violations: list[str] = []
    if not buy.accepted or not sell.accepted:
        violations.append("deterministic BUY/SELL scenario was rejected")
    if portfolio.cash < 0 or any(value < 0 for value in portfolio.asset_balances.values()):
        violations.append("portfolio contains a negative balance")
    if portfolio.fees_paid != buy.fee + sell.fee:
        violations.append("fees were not deducted consistently")
    if len(session.history) != 2:
        violations.append("trade history did not record both executions")
    return violations


if __name__ == "__main__":
    found = paper_trading_violations()
    if found:
        raise SystemExit("\n".join(found))
    print("PaperTrading financial invariants passed.")
