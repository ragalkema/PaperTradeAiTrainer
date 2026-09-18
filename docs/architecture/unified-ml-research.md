# Unified supervised ML research

One row at timestamp **T** represents only information available by **T**. Provider candle
timestamps are candle-open times; a row is emitted at `open + interval`, after OHLCV is complete.

`UnifiedDatasetBuilder` owns market feature engineering, composition, targets and provenance.
DataCollector retains ownership of versioned News and Social snapshots. Research loads each
snapshot range in one bounded query and joins it to the canonical candle-close index in memory.
News snapshots enforce `received_at <= T` and `processed_at <= T`; Social additionally selects
engagement observed at or before T. Retrospective impact/reaction types are not accepted by the
builder.

## Features and missingness

`market_features_v1` contains returns over 1/3/6/12 periods, log return, volume and volume change,
rolling volume mean/z-score, normalized high-low range, 6/12-period EMA and distance, 14-period
RSI/ATR, 6/12 MACD with a 5-period signal, and 12-period return volatility. Warm-up values are
missing. A missing intelligence snapshot remains missing; a persisted snapshot with count zero is
genuine zero activity. XGBoost consumes missing values natively.

Four views—Market, Market+News, Market+Social and all features—slice the same canonical rows.
Targets are attached only after feature construction:

`future_return(T,h) = close(T+h) / close(T) - 1`

The initial configuration uses `h=1h`. Target names never enter the feature matrix.

## Validation and splits

Dataset validation reports rows, range, duplicate/missing timestamps, per-feature missingness,
non-finite values, target distribution and intelligence coverage. `DatasetLeakageValidator`
rejects unordered rows, feature observations after T, target/impact/reaction feature names,
non-future targets and overlapping or insufficiently purged splits.

Train/validation/test are chronological. Rows whose target time crosses the configured gap are
removed before the next split. The default purge equals the target horizon. Expanding-window
walk-forward splits use the same rule. Test data is never used for early stopping, tuning or paper
policy threshold selection.

## Models, metrics and artifacts

`RegressionModelPort` isolates orchestration from `XGBRegressor`. The conservative v1 parameters
are recorded with seed 42 and validation-only early stopping. Zero-return and previous-return
baselines share test timestamps. Metrics are MAE, RMSE, R², Pearson, Spearman and directional
accuracy; undefined constant/insufficient correlations remain null.

Ignored `data/features/<dataset-id>/` folders contain compressed arrays plus metadata and a
validation report. Ignored `models/trained/` artifacts are referenced by path and SHA-256.
`experiments/results/` contains comparison metadata and every out-of-sample timestamp,
prediction and actual. The Dashboard reads these summaries without training on its UI thread.

Reproducibility records source candle identity, feature/target versions, configuration, analyzer
versions, code commit, seed, split dates and model parameters. CPU/library differences can still
cause small floating-point variation. Feature gain is model importance, not causality.

The optional paper policy is separate from prediction. Its symmetric threshold is selected only
on validation observations and includes configured friction. It is research-only and cannot place
real orders.
