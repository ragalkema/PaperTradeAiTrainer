# Leakage prevention

At simulation time T, a bot receives only data available at or before T. Backtests advance an explicit clock and use point-in-time joins. Rolling features are backward-looking; transformations and normalization statistics are fitted only on training windows.

Train, validation, and test splits are chronological when random splitting would leak temporal information. Revised news cannot appear before its receipt/processing time. Validation must detect train/test overlap, duplicate or unordered timestamps, future features, full-dataset normalization, late data, and incompatible dataset/feature versions.

Experiments record dataset, feature and model versions; chronological windows; configuration; hyperparameters; random seed; and Git commit.

## News intelligence separation

Online news queries require both `received_at <= decision_time` and normalized event `processed_at <= decision_time`. Versioned intelligence may be reproduced later during a chronological backfill, so its database insertion time is provenance rather than a reason to hide source information that was already available. Novelty compares only with events received earlier. `NewsFeatureService` depends exclusively on `OnlineIntelligenceQueryPort`; its snapshot contains no reaction, impact, return, future-volume, or future-volatility fields.

Retrospective impact is a separate research path. It may use observations after receipt and is exposed through `RetrospectiveResearchPort`, never the AiTrainer-facing online port. Its score indicates temporal association, not causality.
