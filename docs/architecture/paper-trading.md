# PaperTrading architecture

PaperTrading owns public market-data normalization and virtual execution concepts. The only permitted exchange flow is:

```text
Bitvavo public market data → MarketDataPort adapter → MarketState
                                                   ↓
                                             PaperTrading
                                                   ↓
                                           virtual execution
```

There is no real-order port and no deposit, withdrawal, or live execution adapter. Bots receive shared observations and submit shared intents through the bot gateway; they never receive Bitvavo clients or credentials. Future simulation validation must detect impossible balances, prices, quantities, timestamps, portfolio states, and agent attempts to exploit simulator behavior.
