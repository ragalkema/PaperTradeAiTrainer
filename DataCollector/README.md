# DataCollector

Owns acquisition, immutable raw storage, normalization, deterministic deduplication, and asset relevance for external intelligence. Phase 1 implements structured RSS news only; social media, article scraping, sentiment models, and LLM enrichment are deliberately excluded.

`published_at` describes when a source says content appeared, `received_at` when this system could first observe it, and `processed_at` when derived output became available. Backtests gate availability on receipt/processing time rather than publication time alone.

## News collection

The configurable registry enables four public structured feeds: CoinDesk, Cointelegraph, Decrypt, and The Block. Adapters retain feed metadata and summaries, not full article bodies. A changed item becomes a new immutable raw version because its content hash changes. Exact normalized headlines share a deterministic duplicate group; semantic story clustering is intentionally deferred.

After applying the Alembic migration, run one collection pass with:

```powershell
python -m data_collector news-once
```

BTC, ETH, and SOL aliases are detected by an extensible deterministic registry. Relevance reflects explicit text matches. Sentiment and importance remain `NULL` until a real, validated scoring model is introduced. Market associations record observed returns in bounded post-receipt windows and make no causal claim.
