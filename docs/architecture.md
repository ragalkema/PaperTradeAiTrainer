# Architecture

The platform starts as a modular monolith. Module boundaries are explicit, but deployment and operations remain simple until scale proves a need to split services.

```text
Data Collection
      ↓
Immutable Raw Storage
      ↓
Normalization and Feature Engineering
      ↓
Bot Runtime
      ↓
Paper Exchange
      ↓
Experiment Tracking
      ↓
FastAPI
      ↓
Frontend
```

## Safety-critical flow

```text
Bitvavo public data → MarketDataService → normalized MarketState
                                               ↓
                                              Bot
                                               ↓
                                           BotAction
                                               ↓
                                        PaperExchange
```

Bots consume normalized observations and emit intents. They never receive a Bitvavo client, credentials, or transport object. The paper exchange owns virtual execution and depends only on normalized market data and its own virtual ledger. There is no real-order gateway or order endpoint.

## Module responsibilities

- `market`: external market-data adapters and normalization; no order execution.
- `data`: raw/normalized schemas and lineage.
- `features`: deterministic point-in-time transformations.
- `bots`: strategy-neutral bot interface and bot-owned state.
- `paper_exchange`: virtual orders, fills, fees, positions, and portfolios.
- `experiments`: reproducible configurations, runs, and performance results.
- `news` and `social`: future text collectors isolated from market execution.
- `database`: persistence configuration and models.
- `api`: HTTP presentation over application services.

Future WebSocket collectors can run asynchronously and publish normalized events through in-process queues initially. Redis may later support cache, queues, pub/sub, and live state. PostgreSQL is the system of record for structured metadata; large immutable datasets and model artifacts should move to S3-compatible storage with URIs and checksums stored in PostgreSQL.
