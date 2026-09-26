# Cost-aware bot research

Run from the repository root with the existing local PostgreSQL database:

```powershell
python -m ai_trainer research-bot --market BTC-EUR --start 2025-01-01 --end 2026-09-26T10:00:00Z --validation-start 2025-10-01 --test-start 2026-01-01
```

Repeat for ETH-EUR or SOL-EUR. This reads local candles and news snapshots; it makes no provider
or paid AI calls. Each run creates a new `experiments/results/bot-<market>-<uuid>/` directory.
It contains five native XGBoost JSON models (ten with adequate news coverage), test predictions
in NPZ files, and `report.json` with costs, feature order, checksums and all candidate metrics.
These artifacts are local and Git-ignored. Earlier workflows still use `models/trained/`.

## Target and selection

Predict exact endpoint returns at 1, 2, 6, 12 and 24 hours. These are estimated returns, not
calibrated probabilities or guaranteed profits. Using returns preserves small movements that
would disappear inside a broad 0–2% class. Intraperiod barrier targets are deferred until the
execution simulator can reliably resolve entry, stop and take-profit ordering.

Use the same decision timestamps for all horizons and both feature groups. Require 24 consecutive
warmup hours and complete future hourly targets; exclude windows crossing candle gaps. Feature
calculation uses an incremental EMA/MACD recurrence verified against the original implementation.
Targets are excluded from model inputs. News snapshots generated after a decision are excluded.
The dataset fingerprint includes actual feature values, not only candles.

Partitions are chronological: training, a separate early-stopping block (last 20% before the
validation boundary), policy validation, and test. A maximum-horizon purge prevents label overlap
at boundaries. The example reserves October–December 2025 for policy selection and 2026 for
testing. Repeated development using these test results makes 2026 exploratory; future paper data
is still necessary for independent confirmation.

Thresholds are a predeclared grid of additional net edge: 0%, 0.25%, 0.5%, 1%. Candidates need at
least ten validation trades, positive net return minus closed-trade drawdown, and positive return
with doubled spread/slippage. Horizon and feature-group selection use validation only. Cash/HOLD
is selected if no candidate qualifies. Test metrics never select the model.

Default cost assumptions are **0.25% fee and 0.10% spread/slippage per side**, configurable with
`--fee-per-side` and `--spread-slippage-per-side`. They are research assumptions, not an assertion
about a specific account tariff. Both entry and exit are charged. Allocate 10% of current equity
to one spot long at a time; wait until its horizon completes before another entry. Reports include
cash and always-long-with-the-same-holding-period baselines. The latter is not buy-and-hold.

This evaluation measures closed-trade drawdown, not intratrade mark-to-market losses. Execution
uses candle endpoints and estimated friction. It does not simulate partial fills, order-book
depth, margin, liquidation, staking or lending. Do not interpret it as an executable P&L guarantee.

## Critical news comparison

News coverage must be at least 95% in each partition, based on available snapshots including
valid zero-news counts. Otherwise the report explicitly skips news; all-null columns cannot win
an ablation comparison. Market and market+news models share observations, splits and parameters.
This is an initial coverage check, not a replacement for source uptime, archive provenance and
human label audits. No social/X data is used in this workflow.

## Bot inference

`PaperSignalPredictor` in `AiTrainer/src/ai_trainer/infrastructure/models/paper_signal.py` loads
the selected model once, verifies its checksum and preserves training feature order. Pass a
completed, point-in-time-safe `DatasetRow`, current UTC time, and whether a position is open.
It returns HOLD when no candidate qualified, a position is already open, inputs are missing,
features are stale/future, or required observation times are unavailable. Otherwise the signal
contains estimated gross/net return, horizon and allocation. The caller must enforce market
identity, consume each hourly decision once, and schedule the exit. This is a reusable signal
provider; it is not automatically attached to the existing live ticker bots or an order executor.

Optuna remains installed but is not used by this fixed-parameter benchmark. Tuning must use only
training/validation partitions and must not select parameters on the reported test outcomes.

## Local first run

On the stored 2025–2026 candles, all three markets selected HOLD. Five horizons per market were
trained. None passed the validation gates; news was skipped for insufficient snapshot history.
This establishes a reproducible benchmark and does not establish a profitable strategy.
