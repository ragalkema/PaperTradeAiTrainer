# Dashboard

The primary PaperTradeAiTrainer interface is a native Python 3.12+/PySide6 Qt Widgets
application. It is an observer/controller at the repository edge; it does not own trade
execution, experiment calculations, collection, or model logic.

## Current functionality

- Dark navigation shell with an always-visible **PAPER MODE** indicator.
- Honest `N/A`, disabled, and waiting states throughout.
- Non-blocking public Bitvavo price, bid/ask, 24-hour candle summary, and recent chart for
  BTC-EUR, ETH-EUR, and SOL-EUR.
- Page foundations for bots, experiments, news, social, trades, data health, training, system,
  and settings; unsupported operations are visibly disabled.
- Deterministic Top 5 intelligence ranking. Scores are consumed, never invented, and described
  as estimates/associations.

When PostgreSQL is migrated and contains research runs, Dashboard now queries real active-session
bots, aggregate virtual capital/P&L, positions, trades, decisions, equity history, performance,
and experiment metadata. News, social events, training runs, and detailed database telemetry
remain unavailable. Demo values are never used.

## Run and test

```powershell
python -m pip install -e ".[dashboard]"
.\scripts\run-dashboard.ps1
$env:QT_QPA_PLATFORM = "offscreen"
pytest Dashboard/tests --no-cov
```

## Windows build

```powershell
.\scripts\build-dashboard.ps1
```

The reliable ONEDIR output is `dist\PaperTradeAiTrainer\PaperTradeAiTrainer.exe`; distribute
the entire directory. Optional `-OneFile` outputs `dist\PaperTradeAiTrainer.exe` but launches
more slowly. Both are windowed builds. CI verifies and uploads ONEDIR without publishing it.
