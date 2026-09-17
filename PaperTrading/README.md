# PaperTrading

PaperTrading is a deterministic, spot-only virtual exchange backed by normalized public market data. It never sends orders, uses authentication headers, deposits, withdraws, borrows, or handles real funds.

## Current functionality

- Public Bitvavo ticker price, best bid/ask, market information, candles, and ticker stream.
- Append-only raw JSONL capture and idempotent normalized candle storage.
- Independent virtual EUR accounts and crypto balances.
- BUY by quote-currency budget, SELL by base-asset quantity, and HOLD.
- Configurable fees and adverse percentage slippage using `Decimal`.
- Virtual trade history, fee-inclusive cost basis, realized/unrealized P&L, valuation, win rate, and drawdown.
- Financial conservation checks after every attempted execution.

The public adapter follows Bitvavo's documented `/ticker/price`, `/ticker/book`, `/markets`, `/{market}/candles`, and ticker WebSocket APIs. It has no API key argument and no order method.

## Commands

From the repository root with the virtual environment active:

```powershell
# Retrieve a public price (no API key)
python -m paper_trading price BTC-EUR

# Fetch and persist normalized candles without duplicating overlaps
python -m paper_trading candles BTC-EUR 1h --limit 100

# Start the interactive paper-only CLI
python -m paper_trading trade
```

Interactive commands are `price BTC-EUR`, `buy BTC-EUR 100`, `sell BTC-EUR 0.001`, `portfolio`, `history`, and `quit`. BUY values are EUR budgets; SELL values are asset quantities.

Raw events are appended under `data/raw/market/`. Normalized candles go to `data/normalized/market/candles.jsonl`. Both locations are ignored by Git.

## Execution model

BUY executes at `ask × (1 + slippage)` and deducts requested value plus fee. SELL executes at `bid × (1 - slippage)` and credits proceeds minus fee. There are no partial fills, depth effects, limit orders, leverage, or shorts yet.
