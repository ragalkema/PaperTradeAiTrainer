# Automatic public research startup (Windows)

Installed on 2026-09-29 for the current Windows user. The models remain frozen and no orders,
paid X calls or model retraining are enabled.

## What starts

Task Scheduler task **PaperTradeAiTrainer-PublicResearch** starts at this user's **logon** after
a restart. It does not run before login, or while the computer is asleep. It runs with ordinary
user privileges; no password is stored. Task Scheduler restarts a failed supervisor after one
minute. The supervisor checks its two workers every ten seconds and restarts exited workers,
with a thirty-second retry limit to avoid rapid loops.

`scripts/watch_public_research.ps1` starts Docker Desktop hidden if absent, and starts only the
existing `paper-trade-ai-postgres-1` database container. It never recreates/deletes database volumes.
Database availability still depends on Docker Desktop being able to start on this computer.
The worker commands are strictly `data_operations run-public` and `ai_trainer shadow-content`:
public RSS/candles, and order-free frozen predictions. No auto-X command is used.

The six pinned model paths/checksums are in the local Git-ignored
`experiments/results/research-runtime.json`. A checksum mismatch prevents startup. The named
mutex prevents two supervisors in the same user session; do not additionally start manual workers.
This monitors **process exit**, not all possible hangs or source outages. Check health and logs too.

## Inspect

```powershell
Get-ScheduledTask -TaskName PaperTradeAiTrainer-PublicResearch
Get-Content logs/public-research-supervisor.json
.\.venv\Scripts\python.exe scripts/check_shadow.py
```

Worker stdout/stderr are in `logs/public-collector.managed-*.log` and
`logs/content-shadow.managed-*.log`, with a new file each restart. Heartbeat JSON includes current
PIDs and start counts. These logs need periodic disk-space review; automatic retention is not set.

## Stop or resume

For a graceful stop, create the stop marker:

```powershell
New-Item -ItemType File -Path experiments/results/public-research.stop -Force
```

Within a polling interval the supervisor terminates only its owned worker trees and exits.
The marker prevents collection on subsequent logins. To disable the scheduled task too:

```powershell
Disable-ScheduledTask -TaskName PaperTradeAiTrainer-PublicResearch
```

To resume, remove only that marker, enable the task, then start it:

```powershell
Remove-Item -LiteralPath C:\PaperTradeAiTrainer\experiments\results\public-research.stop
Enable-ScheduledTask -TaskName PaperTradeAiTrainer-PublicResearch
Start-ScheduledTask -TaskName PaperTradeAiTrainer-PublicResearch
```

Do not stop only a worker if you intend to stop collection: the supervisor will restart it.
Install/reinstall with `powershell -NoProfile -ExecutionPolicy Bypass -File
scripts/install_public_research_startup.ps1`. If task registration is unavailable, the installer
uses a per-user Startup shortcut instead; that fallback restarts workers, not a crashed supervisor.
This computer successfully used Task Scheduler, not the fallback.

## Recovery and live-outcome audit

Two interrupted raw news items from September 23 were normalized on September 29 at
09:32:49 UTC. Their original publication/receipt times were preserved, and `processed_at` is the
actual recovery time. A second recovery returned no work. The public collector now automatically
recovers `received` items older than ten minutes before each news cycle, atomically with status
updates. This also handles an existing event whose raw-status update was interrupted, without
changing the existing event time. Duplicates/quarantined timestamps are handled separately.

Manual preview: `python scripts/recover_news.py`; apply: add `--apply`. Do not backdate a replay.

Both worker process trees were deliberately stopped during the setup test and automatically
restarted by the supervisor. Frozen models and journal entries were preserved; the restarted
shadow logger reported zero duplicate inserts. This is not a real Windows reboot test.

At the morning check, twelve forward predictions existed, none overdue. The first six labels
become eligible at 13:00 Europe/Amsterdam (11:00 UTC), including the conservative exit-candle
closure rule. Actual settlement was therefore not yet verifiable. A one-shot task
**PaperTradeAiTrainer-FirstMaturityAudit-20260929** is scheduled at 13:15 local to write
`reports/generated/shadow-first-maturity-20260929.json`. It checks results; it does not invent
missing outcomes or send a notification. If logged out/asleep, execution may occur later at an
eligible logged-in time. Review `due_unsettled`, violations and model errors in that report.
