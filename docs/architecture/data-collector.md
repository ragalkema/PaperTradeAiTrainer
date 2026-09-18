# DataCollector architecture

## Online intelligence

`NewsEvent -> versioned per-asset NewsIntelligence -> NewsFeatureSnapshot -> future AiTrainer`

The first implementation is transparent and local: lexical asset-specific sentiment (`lexical_asset_sentiment_v1`), keyword classification (`keyword_event_classifier_v1`), deterministic importance (`transparent_importance_v1`), and chronological token-similarity novelty (`chronological_jaccard_v1`). Strategy ports allow later NLP or transformer implementations without changing ingestion.

Feature snapshots use 15-minute, 1-hour, and 6-hour receipt-time windows. Weighted sentiment is `sum(sentiment * relevance * importance) / sum(relevance * importance)`; a zero denominator produces `NULL`.

## Retrospective research

`NewsEvent -> future market observations -> RetrospectiveImpact -> Dashboard research`

`heuristic_v1` combines relevance, online importance, novelty, absolute observed return, and available volume response. Pending windows are explicit and omitted from response calculations. A high score means temporal association, never causality. This query port is separate from online features.

DataCollector owns external textual acquisition, immutable raw capture, normalization, and future lightweight NLP preprocessing. Provider code belongs in infrastructure adapters for official news APIs, RSS, social APIs, or—only where appropriate and permitted—scrapers. Application use cases coordinate ports; domain entities describe source-neutral content.

It emits normalized data through shared schemas or future messaging/API adapters. It does not import AiTrainer, PaperTrading internals, or model code.
