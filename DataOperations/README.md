# Research Data Operations

Start PostgreSQL, migrate, and run the failure-isolated collector stack:

```powershell
docker compose up -d postgres
python -m alembic upgrade head
.\scripts\run-data-operations.ps1
```

Market, News, Social, intelligence, reactions, and health use independent configured schedules.
Ctrl+C cancels workers, closes clients, and records shutdown. One failing source does not stop the
others.

Restartable, idempotent market maintenance:

```powershell
python -m data_operations backfill-market --market BTC-EUR --interval 1h --start 2025-01-01 --end 2026-09-01
python -m data_operations repair-market-gaps --market BTC-EUR --interval 1h --start 2025-01-01 --end 2026-09-01
```

Repairs request only missing ranges and never interpolate OHLCV. RSS/X history is collected only
where legitimate provider access supports it. Earlier unavailable periods are stored as coverage
limitations, never treated as zero events.

```powershell
python -m ai_trainer dataset-readiness --market BTC-EUR --interval 1h --start 2026-01-01 --end 2026-09-01
```

Real comparisons stop when combined readiness fails unless `--allow-unready` is explicit.
Collection never retrains models.

Use `.\scripts\backup-postgres.ps1` for a development `pg_dump`. Restore using `pg_restore` with
the local development database. Backups are ignored by Git. No research data is automatically
deleted; provider-specific retention obligations remain isolated in provider infrastructure.
