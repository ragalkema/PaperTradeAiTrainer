# Architecture overview

PaperTradeAiTrainer is a modular monorepo with four Python package boundaries:

```text
DataCollector ──normalized text events──┐
                                       ├── shared contracts ── AiTrainer
public market data ── PaperTrading ─────┘
```

Each project uses pragmatic Clean Architecture: interfaces and infrastructure depend inward on application and domain; application declares ports; domain stays framework-free. Projects do not import one another's internal modules. Communication uses shared contracts now and may later use application ports, APIs, or events without requiring distributed infrastructure.

Dependency rules:

1. DataCollector does not know how AI models work.
2. PaperTrading does not know whether a bot uses rules, XGBoost, PyTorch, PPO, or SAC.
3. AiTrainer never communicates directly with Bitvavo.
4. `shared` contains contracts, not business logic or utilities.
5. External frameworks remain at the edges.
6. Domain logic is testable without internet, databases, provider APIs, or GPUs.
7. AI agents cannot execute real trades.
8. Raw historical data is immutable.
