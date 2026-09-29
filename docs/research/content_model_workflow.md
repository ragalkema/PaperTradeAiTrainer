# Market versus market + text, and forward observation

## Refresh public data

Run `python -m data_operations run-public --once` for public RSS and current candles. A failing
source remains explicitly unhealthy; successful content is retained and analyzed. No X or paid
AI calls are made. A failed source blocks six-hour aggregate coverage, not use of other available
event texts. Use `run-public` without `--once` for ongoing collection; it must remain running.
It is not installed as a Windows startup service. A sleeping computer does not collect news.

Repair missing hourly data for BTC-EUR, ETH-EUR and SOL-EUR using
`python -m data_operations repair-market-gaps --market ETH-EUR --interval 1h --start
2026-09-18T00:00:00Z --end <last-completed-UTC-hour>`. Then run
`python -m ai_trainer build-event-reactions --start 2025-01-01` for refreshed per-message labels.

## Train and compare

```powershell
.\.venv\Scripts\python.exe -m ai_trainer compare-content --market ETH-EUR --start 2026-09-18
```

Repeat for BTC-EUR and SOL-EUR. This reads local data only. No Optuna is run: three fixed Ridge
regularization strengths (0.1, 1, 10) suffice for this small-data baseline. Existing `research-bot`
Optuna functionality is unchanged. Each run gets a new `experiments/results/content-<market>-<uuid>`
directory with `report.json`, plain JSON linear models and test prediction JSONL files.

Both variants use exactly the same event-bearing hourly decisions. Messages available in the
preceding hour are aggregated, identical text is deduplicated, and technical features require
24 consecutive completed hourly candles. This is **conditional on content arrivals**, not a
backtest of every hour. X text joins automatically when local X events exist; no X history is
invented. News titles/summaries need not contain full article text.

The market baseline uses normalized numeric features and Ridge. The text variant additionally
uses train-only TF-IDF unigrams/bigrams (maximum 5,000). Scaling, vocabulary and IDF are fit on
training only. No retrospective relevance or engagement is used. JSON model artifacts contain
everything needed for inference, without pickle loading or paid language-model calls.

Default splits use the first 60% / next 20% / final 20% of unique decision times. Override with
both `--validation-start` and `--test-start`. Per-horizon purging removes targets not known before
the next partition. Story IDs/text hashes cannot cross into later partitions. Regularization is
selected on validation MSE, never test outcomes. Training needs at least three train observations
and one validation/test observation **only to exercise the pipeline**, not to claim reliability.
Reports are deliberately marked `EXPLORATORY_ONLY` even if a small test happens to look good.

Seven horizons are attempted: 1h, 2h, 6h, 12h, 24h, 7d, 30d. Unmatured/gapped targets are excluded.
Each report gives partition sizes, RMSE versus zero-return prediction, direction accuracy,
net return, trades and conservative intrabar drawdown. Execution enters at the next hourly
opening, holds the horizon, charges 0.25% fee + 0.10% spread/slippage per side, allocates 10%,
and permits one long position. Additional net-edge threshold is fixed at zero (not test-tuned).
Cash, always-long on matching decisions, and contiguous-window buy-and-hold are baselines.
No shorting, lending, staking, market depth or partial fills are represented.

These hourly comparison labels use the hourly decision after message availability and can have
a later entry than the per-message export. This is intentional aggregation, not identical labels.
Successful code tests and favorable historical metrics do not demonstrate live profitability.

## Inspect the notebook

Open `AiTrainer/notebooks/news_model_review.ipynb` in VS Code with a Python/Jupyter kernel.
Install the optional kernel with `python -m pip install -e ".[notebooks]"` and select `.venv`.
It selects the newest ETH run by default. Change `REPORT` for another run, or `HORIZON` for another
holding period. It shows test metrics, source texts, predicted/observed returns and the forward
journal. It uses the standard library plus IPython; no paid calls, retraining or chart dependencies.

## Frozen forward logging, no orders

```powershell
.\.venv\Scripts\python.exe -m ai_trainer shadow-content `
  --models experiments/results/content-ETH-EUR-<id>/market_1h.json `
           experiments/results/content-ETH-EUR-<id>/market_text_1h.json --watch
```

Replace paths with your generated models. Omit `--watch` for one cycle. Run the public collector
alongside it. Every five minutes, this command reads newly available content and completed
candles, records frozen predictions and settles matured outcomes. No fitting, model promotion,
orders or paper capital mutations occur. If there is no fresh content or complete market context,
it skips instead of fabricating an observation. Forward decisions are wall-clock arrivals rather
than retrospective whole-hour buckets; entry is still the strictly next hourly opening.

`experiments/results/content-shadow.db` is a separate SQLite research journal, not a replacement
for PostgreSQL. Unique model hash/market/entry identities prevent duplicates across restarts.
Predictions are never updated by this code; realized outcomes live in another table. Late writes
at/after entry and predictions backdated before model freezing are rejected. Outputs remain
pending when candles are missing. Never edit a frozen artifact to disguise its provenance.

Let the process accumulate observations prospectively. Review per-model errors and outcomes;
do not select a winner on repeatedly inspected 2026 tests and call that independent validation.
Collect substantially more dates/regimes and keep a new future holdout before any trading use.

The running collector writes `logs/public-collector.stdout.log` and
`logs/public-collector.stderr.log`; forward logging writes `logs/content-shadow.stdout.log` and
`logs/content-shadow.stderr.log`. To inspect these specific processes in PowerShell:

```powershell
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object { $_.CommandLine -match 'data_operations run-public|ai_trainer shadow-content' } |
  Select-Object ProcessId, CommandLine
```

The later Windows setup now supervises both processes and starts them at user logon.
Use the stop marker described in [Windows startup](windows_research_startup.md) to stop them;
stopping a worker alone triggers automatic restart. There may be a virtualenv launcher and worker.

## First local run: 2026-09-29

- Repaired 67 hourly candles for each of BTC, ETH and SOL. A subsequent database check found
  zero missing hourly candles from September 18 through the latest closed hour.
- Collected 150 new normalized news events. CryptoPotato initially returned malformed XML;
  on the next public cycle its stored health recovered. No paid X calls were made.
- Reaction export `event-reactions-126efb8e-814a-4563-ac33-8bc12116e1d2` contains 881 source news
  events, of which 306 map to these markets (364 market/message rows). Each short horizon has
  308 mature samples, 7d has 43, and 30d has none. There are still no X events.
- Matched comparison windows: BTC 19, ETH 8, SOL 8. Trained 26 market/text artifacts across
  eligible horizons; 7d/30d lack sufficient purged partitions. All reports are exploratory.
- Latest one-hour text models make zero test trades after the fixed cost gate. Text marginally
  improves BTC prediction RMSE but worsens ETH/SOL here; the sample is far too small for conclusions.
- Started a public-only collector and a forward logger for six frozen one-hour models
  (market and market+text for each coin). Six genuine forward predictions were recorded;
  the repeat cycle inserted no duplicates. Realized outcomes are pending, not assumed wins.

Runs: `content-ETH-EUR-24cbdf4a-a4ec-40f0-9e65-77176a2f6dd1`,
`content-BTC-EUR-a43ac9ae-a58d-417f-9ae1-2d12bf99e706`,
`content-SOL-EUR-477d6aa5-c72a-446e-bf6f-d19d88b11252`, all under `experiments/results`.
