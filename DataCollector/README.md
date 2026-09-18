# DataCollector

Owns acquisition, immutable raw storage, normalization, deterministic deduplication, asset relevance, and versioned online news intelligence. Social media, article scraping, and external LLM calls remain deliberately excluded.

`published_at` describes when a source says content appeared, `received_at` when this system could first observe it, and `processed_at` when derived output became available. Backtests gate availability on receipt/processing time rather than publication time alone.

## News collection

The configurable registry enables four public structured feeds: CoinDesk, Cointelegraph, Decrypt, and The Block. Adapters retain feed metadata and summaries, not full article bodies. A changed item becomes a new immutable raw version because its content hash changes. Exact normalized headlines share a deterministic duplicate group. Related articles receive a chronological token-similarity story cluster.

After applying the Alembic migration, run one collection pass with:

```powershell
python -m data_collector news-once
```

BTC, ETH, and SOL aliases are detected by an extensible deterministic registry. Relevance reflects explicit text matches. Online intelligence uses transparent versioned heuristics; it does not claim transformer-level understanding. Market associations record observed returns in bounded post-receipt windows and make no causal claim.

Analyze new or persisted events chronologically, then refresh mature retrospective records:

```powershell
python -m data_collector analyze-news
python -m data_collector update-market-reactions
```

Online records contain per-asset sentiment, importance, event type, novelty, confidence, versions, and explanations. Retrospective impact is research-only and never appears in an online feature snapshot.
