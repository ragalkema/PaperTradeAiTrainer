# Roadmap

1. Implement a public, read-only Bitvavo `MarketDataService` and persist normalized observations.
2. Add immutable raw capture, normalization, and point-in-time validation.
3. Implement the basic long-only paper ledger, market orders, fees, and deterministic fills.
4. Build the bot runtime and baseline strategies under identical event streams.
5. Add reproducible backtests and experiment metrics.
6. Add the monitoring API and dashboard views.
7. Add news/social collection and versioned NLP features.
8. Evaluate ML/RL dependencies only when a concrete experiment requires them.

Likely future research dependencies include NumPy, pandas or Polars, scikit-learn, XGBoost, PyTorch, Gymnasium, Stable-Baselines3, Optuna, and Transformers. They are intentionally absent today.
