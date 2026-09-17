# Paper-trading MVP

## Public data flow

```text
Bitvavo public REST/WebSocket
        ↓ exact payload appended
raw local storage
        ↓ adapter validation/normalization
MarketState / Candle
        ↓
PaperTradingSession
        ↓
DeterministicPaperExchange
        ↓
PortfolioSnapshot / TradeResult / PerformanceMetrics
```

The adapter translates provider fields at the infrastructure boundary. Domain and application code never parse Bitvavo payloads or make network requests. REST errors become `MarketDataError`; WebSocket reconnects use capped exponential backoff and stop after a configurable number of consecutive failures.

## Safety and accounting

Actions are intents, not provider orders. BUY carries a quote-currency budget; SELL carries base quantity. Fees are included in cost basis, realized P&L is net of buy/sell fees, and valuation uses the latest normalized current price. Every execution checks non-negative balances, fee totals, quote-value conservation, and asset conservation with a 1e-24 Decimal representation tolerance.

## Offline tests

Normal tests use deterministic states and HTTP/WebSocket mocks. They never require internet or credentials. Live public commands are manual development operations.
