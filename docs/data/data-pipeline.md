# Data pipeline

```text
external source → immutable raw → normalized → features → training/backtesting
```

Raw data must never be overwritten. Corrections and late arrivals create new records or versions. Derived outputs retain source identifiers, input checksums, schema/feature version, transformation code version, and run ID. Git stores no market dumps, large datasets, database dumps, or generated model artifacts.
