# Operational check and restart test — 2026-09-29

Later update: the two raw items below have been recovered and logon startup installed.
See [the subsequent setup report](windows_research_startup.md). The observations below are the
earlier audit snapshot, not the current backlog.

Checked around 10:45–10:49 Europe/Amsterdam. No model training, orders or paid X calls.

- Public collector and shadow logger were running. All ten news sources reported healthy.
- News events increased from 881 in the earlier build to 920 before the restart and 921 after it.
- BTC/ETH/SOL hourly candles have no gaps from September 18 through the latest completed hour.
  Minute candles are arriving, but a full minute-history gap audit was not performed.
- Six predictions, zero outcomes. All prediction timestamps precede entry; no integrity violations.
  The first labels become eligible at **11:00 UTC / 13:00 local**: entry 09:00 UTC, one-hour target
  at 10:00 UTC, then the stored exit candle must close at 11:00 UTC. Pending is expected, not failure.
- Restarted only the identified public collector and shadow logger, including virtualenv launchers.
  New launcher PIDs: public 35468, shadow 27036; worker PIDs: 35588 and 29540 at inspection time.
  These IDs are a historical snapshot, not permanent process identifiers.
- The restarted shadow cycle reported `inserted=0`, `predictions=6`, no skips. All prediction fields
  retained the same SHA-256 digest before/after restart. All six model files match their frozen
  training-report checksums. No model was changed.
- The collector resumed public API polling; old logs were preserved. New logs are
  `logs/public-collector.restart-20260929.*.log` and `logs/content-shadow.restart-20260929.*.log`.

## Remaining observations

Two raw news items remain in `received` status from September 23. They predate this restart and
have not been replayed or deleted. This is an existing processing backlog, so do not describe
the entire collection pipeline as fully clean. Investigate/replay these separately with original
availability timestamps preserved and a new actual processing timestamp.

Live settlement cannot yet be confirmed for these six predictions: their horizons have not matured.
Controlled tests cover mature settlement, missing data staying pending, duplicate prevention,
restart persistence and premature/late timestamp detection. Recheck after 13:00 local plus a
collector/logger cycle. This restart test does not establish long-term uptime or crash safety at
every possible point in ingestion.

## Inspect again

```powershell
.\.venv\Scripts\python.exe scripts/check_shadow.py
```

This command opens SQLite read-only. It reports per-model counts, pending vs due/unsettled, MAE,
RMSE, timestamp violations and a prediction digest. Optional `--output <new-file.json>` saves an
audit without overwriting earlier evidence. Before/after snapshots are in
`reports/generated/shadow-before-restart-20260929.json` and
`reports/generated/shadow-after-restart-20260929.json`.

The notebook `AiTrainer/notebooks/news_model_review.ipynb` now has a live operational section,
including the most recently updated collector/shadow log. It does not select a winner.
Windows automatic startup is unchanged: these processes still require restarting after reboot.
