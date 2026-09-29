# News and X reaction datasets

Build local, per-content price labels without provider calls or database schema changes:

```powershell
.\.venv\Scripts\python.exe -m ai_trainer build-event-reactions --start 2025-01-01
```

Default markets: BTC-EUR, ETH-EUR, SOL-EUR. Override with `--markets ETH-EUR BTC-EUR`.
Only the assets identified in each processed event are included; unmapped articles are not
silently assigned to every coin. News uses stored title/summary, X uses stored post text.
Raw unprocessed/quarantined records are not exported. No synthetic posts are added.

`--start` / `--end` filter publication times (`start <= time < end`). `--as-of` limits outcome
observations and content availability; both optional end values default to now. Dates without
a timezone mean UTC. A repeat run creates a new immutable directory under
`experiments/results/event-reactions-<uuid>/`. `--output` must name a directory that does not yet
exist. Generated text/data stays local and Git-ignored under the default output root.

## Files

- `events.jsonl`: every matched event/market, metadata, safe input fields and both sets of labels.
- `training_1h.jsonl`, `training_2h.jsonl`, `training_6h.jsonl`, `training_12h.jsonl`,
  `training_24h.jsonl`, `training_7d.jsonl`, `training_30d.jsonl`: mature, complete training samples.
- `manifest.json`: schema version, cutoff, markets, counts, class balance, distinct price windows,
  SHA-256 output checksums, split settings and limitations.

One story mentioning two coins creates two rows. Several stories may share a price window:
sample counts are **not counts of independent observations**. Group similar stories and shared
windows during evaluation; use chronological blocks, not random row splits.

## Time and label definitions

The training anchor is `max(published_at, received_at, processed_at)`. Its reference price is the
opening of the **strictly next hourly candle**. The endpoint is the opening 1, 2, 6, 12, 24,
168 or 720 hours later. This is hourly resolution, not the exact quote at publication time.
The exit candle must itself have closed by the cutoff before its stored opening is accepted.
Every hourly candle from entry through exit must exist. No interpolation or forward filling.

Each horizon contains:

- `return_fraction`: endpoint/reference - 1; 0.02 means +2%.
- `maximum_return_fraction` / `minimum_return_fraction`: highest/lowest movement within the
  holding period, including the exit open but excluding price action after it.
- `direction`: up, down, flat.
- `magnitude_band`: [0,2), [2,5), [5,10), [10,15), [15,20), [20,infinity) percent.
  Exactly 2% enters the 2-5% band; the largest band is **20%+**, not <20%.
- `entry_at`, `target_at`, `label_available_at`, `status`.

`pending` means the complete horizon has not yet matured. `missing_candles` means it has
matured but local prices are incomplete. Neither is a zero/flat label or a negative example.
Rerun after collection/backfill to mature these labels. This is not a scheduled background job.

`publication_reactions_not_features` separately describes price action from the next opening
after publication. An old article collected today can have a mature publication reaction and
a pending training target. That descriptive reaction is never copied into the training input.

These are **associations, not evidence that a particular post caused a move**. Especially at
7/30 days, many other events intervene. Returns are gross labels, not executable net profits;
fees, spread, latency and position sizing belong in subsequent strategy evaluation.

## Training safely

Read only `features` as model input: `text`, `source`, `source_type`, `asset`. Use the selected
`target.return_fraction` for regression or `target.class` for classification. Fit text
vectorizers/encoders and any normalization using training data only. No engagement totals,
retrospective impact scores, target prices or publication reactions belong in X.

The existing `research-bot` candle-based trainer does not automatically consume this new
event-text schema; this command builds datasets, not new trained models. A text model/adapter
is a separate step. The event content and asset mapping are assumed to have existed at the
stored processed time; edited content history is not available. These exports do not claim
to recreate historical candle ingestion times, only retrospective outcomes.

For chronological partitions, supply **both** `--validation-start` and `--test-start`.
Partition assignment uses content availability, not publication. Labels whose availability
reaches the next boundary are purged per horizon (up to 30 days plus hourly alignment/closure).
Repeated story clusters or identical normalized text in later partitions are excluded there.
Check `target.split` when loading the training files: train, validation and test remain in one
file per horizon. `events.jsonl` retains excluded rows for auditing. Without these flags,
partitions are unassigned; the downstream trainer must split and purge explicitly.

Do not create artificial 2025 training data by backdating recently received articles.
Seven- and thirty-day training files will legitimately be empty until enough observed history
exists. X support does not imply X data is already present or that paid collection was started.
