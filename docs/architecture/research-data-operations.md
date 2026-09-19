# Research data operations and readiness

Data Operations coordinates Market, News, Social, online analysis, retrospective maturity, and
health. It does not own trading, sentiment, ML logic, or Dashboard business rules.

The chain remains `RAW -> NORMALIZED -> ONLINE INTELLIGENCE -> FEATURES`. Health metadata sits
alongside this chain and is not a model feature. Repairs never modify immutable raw records.

## Coverage semantics

Market coverage compares expected timestamps with persisted candles. News/Social coverage measures
collector operational time, not events per hour. Healthy plus zero events is observed zero activity;
offline/unknown means activity is unknown. Historical limitations explicitly record periods that
RSS or configured official Social access cannot recover.

## Readiness policy v1

Defaults are configurable engineering requirements, not universal scientific thresholds:

- minimum period 30 days;
- market availability 99.5%;
- no unresolved gap of three hours or more;
- selected intelligence collectors operational 98%;
- 500 canonical rows;
- at most 10% unusable feature rows.

Market-only, Market+News, Market+Social, and Combined are assessed separately. A longest-period
finder merges contiguous eligible intervals but never starts training. A real experiment manifest
freezes period, rows, versions, coverage, fingerprint, policy, generation time, and Git commit.

## Recovery and maturity

Backfill checkpoints resume after the last stored candle; overlapping writes are idempotent. Market
gaps can be repaired from public candles. RSS/Social downtime stays unknown unless official access
supports recovery. Graceful shutdown writes OFFLINE health observations.

Retrospective +5m/+15m/+30m/+1h/+4h/+24h reactions are created only when mature and market candles
exist. They remain research-only and can never enter online ML features.

## Everyday workflow and retention

Run `docker compose up -d postgres`, `python -m alembic upgrade head`,
`.\scripts\run-data-operations.ps1`, and `.\scripts\run-dashboard.ps1`. The explicit
`.\scripts\run-all.ps1` convenience wrapper performs the same startup; it does not modify Windows
startup settings. Collection and training remain separate: inspect `dataset-readiness`, then launch
a real comparison only when its requested feature group is ready.

Research records are not deleted automatically. Raw provider data is retained only where provider
terms allow it. Use `.\scripts\backup-postgres.ps1`; restore its custom-format dump with
`pg_restore --clean --if-exists --no-owner -d papertrading <dump-file>` against a stopped local
collector stack.
