# DataCollector

Owns acquisition and normalization of news, social, RSS, API, and—only when appropriate—scraped textual data. No integrations are implemented yet. Raw captures remain immutable and normalized outputs are separate, versioned artifacts.

`published_at` describes when a source says content appeared, `received_at` when this system could first observe it, and `processed_at` when derived output became available. Backtests generally gate availability on receipt/processing time rather than publication time alone.
