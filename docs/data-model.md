# Data model and time-series safety

The data pipeline is append-oriented:

```text
External source → immutable raw capture → normalization → features → model input
```

Raw data is never overwritten by processed data. Each derived dataset should retain source identifiers, schema/feature version, transformation code version, run ID, and a pointer or checksum for its raw inputs. Reprocessing creates a new version.

## Planned data families

- Market: candles, trades, order-book snapshots, and tickers.
- Text: news articles and social posts.
- Derived: sentiment, technical indicators, and market features.
- Execution: bot decisions, virtual orders/trades, and portfolio snapshots.
- Research: experiment specifications, metrics, and artifact references.

Only schemas needed by current behavior should become database tables. PostgreSQL will hold structured metadata and queryable records. Bulk history belongs in versioned Parquet/object storage, never Git.

## Point-in-time correctness

Every observation has an event timestamp and, where relevant, an ingestion timestamp. External text should retain `published_at`, `received_at`, and `processed_at`. Corrections and late arrivals must be appended, not silently backdated.

Backtests advance an explicit simulation clock. A bot may receive only records whose availability timestamp is at or before that clock. Features must use backward-looking windows, point-in-time joins, and a cutoff passed explicitly into data access. Dataset splits are chronological; normalization statistics are fitted only on training windows. Tests should cover boundary timestamps, late data, missing data, and look-ahead rejection.

For reproducibility, persist source versions/checksums, time zone (UTC), universe, sampling rules, feature version, and the exact cutoff policy.
