# Leakage prevention

At simulation time T, a bot receives only data available at or before T. Backtests advance an explicit clock and use point-in-time joins. Rolling features are backward-looking; transformations and normalization statistics are fitted only on training windows.

Train, validation, and test splits are chronological when random splitting would leak temporal information. Revised news cannot appear before its receipt/processing time. Validation must detect train/test overlap, duplicate or unordered timestamps, future features, full-dataset normalization, late data, and incompatible dataset/feature versions.

Experiments record dataset, feature and model versions; chronological windows; configuration; hyperparameters; random seed; and Git commit.
