# Local data

Raw data must never be overwritten by processed data.

The local pipeline is `raw` → `normalized` → `features` → training/backtesting. Contents are ignored by Git; only structure documentation is tracked. Large datasets belong in local or object storage with checksums, versions, and provenance recorded in experiment metadata.
