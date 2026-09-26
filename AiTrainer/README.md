# AiTrainer

AiTrainer currently provides three intentionally simple baseline bots and a source-neutral runner:

- `RandomBot`: seeded BUY/SELL/HOLD choices.
- `BuyAndHoldBot`: buys once after a successful fill, then holds.
- `MovingAverageBot`: compares short and long simple moving averages.

Each bot implements the same framework-neutral `TradingBot` interface. `MultiBotRunner` broadcasts identical `MarketState` values while every bot owns an independent `PaperSessionPort`. Bots do not know whether data came from Bitvavo, stored candles, or tests.

Run a public historical comparison from the repository root:

```powershell
python scripts/run_experiment.py BTC-EUR 1h --limit 100 --seed 42
```

The output compares return, maximum drawdown, trades, and fees. Experiment metadata includes market, interval, period, execution settings, bot configuration, seed, and Git commit where available. Historical performance does not predict future profitability.

## Supervised research

AiTrainer builds point-in-time unified datasets and compares identical canonical timestamps across
Market, Market+News, Market+Social and combined XGBoost regressors. See
`docs/architecture/unified-ml-research.md` for timing, leakage and artifact semantics.

```powershell
python -m ai_trainer compare-feature-groups --market BTC-EUR --interval 1h --target-horizon 1h
```

Use `--synthetic` only to validate pipeline mechanics. Synthetic output is explicitly labelled
`PIPELINE_VALIDATION` and is never a financial research conclusion. No RL or real trading exists.

## Local ML artifacts

For the cost-aware five-horizon bot workflow and critical market/news comparison, see
[`docs/research/bot_prediction_research.md`](../docs/research/bot_prediction_research.md).
Run `python -m ai_trainer research-bot --help` for its local-database command.

Training output is intentionally kept out of Git and can be inspected in these repository-root
directories:

- `data/features/<dataset-id>/dataset.npz`: the exact feature matrix, timestamps and targets.
- `data/features/<dataset-id>/metadata.json`: market, period, feature versions and fingerprint.
- `data/features/<dataset-id>/validation.json`: integrity and leakage-validation results.
- `models/trained/<model-id>.json`: native XGBoost model artifacts, loadable with XGBoost.
- `experiments/results/<comparison-id>.json`: metrics, feature importance and provenance for every
  feature-group comparison.
- `experiments/optuna/`: reserved for local Optuna studies. For persistent tuning, use for example
  `sqlite:///experiments/optuna/studies.db`; database files are ignored by Git.

Install the complete research environment, including XGBoost and Optuna, with:

```powershell
python -m pip install -e ".[dev,ml]"
```

Optuna is available as a dependency for a future tuning command; normal comparison runs remain
deterministic and do not start an Optuna study implicitly.
