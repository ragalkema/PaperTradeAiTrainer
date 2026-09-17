# AiTrainer

AiTrainer currently provides three intentionally simple baseline bots and a source-neutral runner:

- `RandomBot`: seeded BUY/SELL/HOLD choices.
- `BuyAndHoldBot`: buys once after a successful fill, then holds.
- `MovingAverageBot`: compares short and long simple moving averages.

Each bot implements the same framework-neutral `TradingBot` interface. `MultiBotRunner` broadcasts identical `MarketState` values while every bot owns an independent `PaperSessionPort`. Bots do not know whether data came from Bitvavo, stored candles, or tests.

Run a public historical comparison from the repository root:

```powershell
python scripts/run_experiment.py BTC-EUR 1h --limit 100 --seed 42
```

The output compares return, maximum drawdown, trades, and fees. Experiment metadata includes market, interval, period, execution settings, bot configuration, seed, and Git commit where available. Historical performance does not predict future profitability.

No ML or RL libraries/models are implemented yet.
