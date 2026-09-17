# PaperTrading architecture

PaperTrading owns public market-data normalization and virtual execution concepts. The only permitted exchange flow is:

```text
Bitvavo public market data → MarketDataPort adapter → MarketState
                                                   ↓
                                             PaperTrading
                                                   ↓
                                           virtual execution
```

There is no real-order port and no deposit, withdrawal, or live execution adapter. Bots receive shared observations and submit shared intents through the bot gateway; they never receive Bitvavo clients or credentials.

The current deterministic engine supports virtual spot market BUY/SELL/HOLD, bid/ask spread, configurable fee and adverse percentage slippage, cost basis, P&L, history, valuation, and initial metrics. It checks impossible balances, prices, quantities, timestamps, fee accounting, and money/asset conservation after execution.
