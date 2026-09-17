# Roadmap

Develop in this order:

Completed foundation milestones:

- Shared market/trading contracts.
- Read-only Bitvavo public market-data adapter.
- Append-only raw capture and idempotent normalized candle storage.
- Deterministic spot PaperExchange with simulation invariants.
- Random, buy-and-hold, and moving-average baseline bots.
- Initial historical multi-bot comparison and basic metrics.

Next milestones:

1. Develop DataCollector news ingestion, source validation, immutable raw storage, and normalized `NewsEvent` contracts.
2. Expand historical dataset management and experiment result persistence.
3. Add richer order-book/depth-driven slippage models.
4. Add DataCollector news adapters, preferring official APIs/RSS.
5. Add versioned NLP/news features.
6. Add permitted official social/X collection.
7. Add classical and neural ML bots.
8. Add a reinforcement-learning environment.
9. Add PPO/SAC agents.
10. Run live multi-bot paper-trading experiments.

Likely future research dependencies include NumPy, pandas or Polars, scikit-learn, XGBoost, PyTorch, Gymnasium, Stable-Baselines3, Optuna, and Transformers. Install them only for a concrete milestone.
