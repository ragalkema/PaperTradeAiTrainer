# Shared contracts

`shared` is intentionally small. It currently owns `MarketState`, `BotAction`, and `TradeResult`, the stable language exchanged by PaperTrading and AiTrainer. Contracts use only the Python standard library so consumers do not inherit web, persistence, or ML dependencies.

Provider clients, persistence, business workflows, models, and generic helpers are forbidden here. Versioned serialization schemas and event envelopes should be added only when a real inter-project transport requires them.
