# Roadmap

Develop in this order:

1. Complete shared market contracts as concrete use cases require them.
2. Implement a read-only Bitvavo public `MarketDataPort` adapter.
3. Persist immutable raw and normalized market data.
4. Implement the PaperExchange core.
5. Add deterministic simulation/invariant tests.
6. Add simple baseline bots.
7. Build historical backtesting and experiment comparison.
8. Add DataCollector news adapters, preferring official APIs/RSS.
9. Add versioned NLP/news features.
10. Add permitted official social/X collection.
11. Add classical and neural ML bots.
12. Add a reinforcement-learning environment.
13. Add PPO/SAC agents.
14. Run live multi-bot paper-trading experiments.

Likely future research dependencies include NumPy, pandas or Polars, scikit-learn, XGBoost, PyTorch, Gymnasium, Stable-Baselines3, Optuna, and Transformers. Install them only for a concrete milestone.
