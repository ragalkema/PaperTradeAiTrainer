# AiTrainer architecture

AiTrainer owns bot abstractions, training, backtesting, evaluation, comparison, and experiment reproducibility. The `TradingBot` port is independent of ML libraries. Rule-based, XGBoost, neural, PPO, SAC, news, and hybrid bots can implement the same interface.

Adapters may communicate with PaperTrading through shared contracts and public application/API boundaries. AiTrainer cannot import PaperTrading infrastructure or Bitvavo code.

The initial `RandomBot`, `BuyAndHoldBot`, and `MovingAverageBot` validate this boundary. A `MultiBotRunner` gives every bot identical states and an independent session. The historical experiment runner produces reproducible basic metrics without claiming predictive performance.
