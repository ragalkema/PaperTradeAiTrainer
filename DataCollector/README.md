# DataCollector

Owns acquisition, immutable raw storage, normalization, deterministic deduplication, asset relevance, and versioned online news intelligence. Article scraping remains deliberately excluded. Optional external AI assessment is isolated behind a provider-neutral dataset interface and is never required for collection.

`published_at` describes when a source says content appeared, `received_at` when this system could first observe it, and `processed_at` when derived output became available. Backtests gate availability on receipt/processing time rather than publication time alone.

## News collection

The configurable registry enables ten public structured feeds: CoinDesk, Cointelegraph, Decrypt, The Block, NewsBTC, Blockworks, DL News, Bitcoin.com News, U.Today, and CryptoPotato. Adapters retain feed metadata and summaries, not full article bodies. A changed item becomes a new immutable raw version because its content hash changes. Exact normalized headlines share a deterministic duplicate group. Related articles receive a chronological token-similarity story cluster.

After applying the Alembic migration, run one collection pass with:

```powershell
python -m data_collector news-once
```

Aliases for all dashboard markets are detected by an extensible deterministic registry. Relevance reflects explicit text matches. Online intelligence uses transparent versioned heuristics; it does not claim transformer-level understanding. Market associations record observed returns in bounded post-receipt windows and make no causal claim.

Analyze new or persisted events chronologically, then refresh mature retrospective records:

```powershell
python -m data_collector analyze-news
python -m data_collector update-market-reactions
```

Online records contain per-asset sentiment, importance, event type, novelty, confidence, versions, and explanations. Retrospective impact is research-only and never appears in an online feature snapshot.

## Social intelligence

X API v2 is the first adapter behind provider-neutral social contracts. No account list is silently populated; import the disabled example or your reviewed configuration:

```powershell
python -m data_collector social-accounts import config/social_accounts.example.json
python -m data_collector social-accounts list
python -m data_collector social-accounts enable username
python -m data_collector social-once
python -m data_collector analyze-social
python -m data_collector update-social-reactions
```

Collection requires `X_API_BEARER_TOKEN`. Normal CI uses legal synthetic fixtures and never requires live X access. Engagement observations are append-only and queried as-of the decision time.

## Relevance reference dataset

Export a deduplicated, point-in-time JSONL dataset from persisted news and social intelligence:

```powershell
python -m data_collector build-reference-dataset `
  --total 10000 --influential 2000 --low-value 4000 `
  --output data/reference/market_relevance.jsonl
```

The command never pads a shortfall with duplicates or synthetic records. Its non-zero exit code and JSON report state exactly how many real candidates are missing. Without `--ai`, labels are explicitly marked as weak supervision from the existing versioned scores. Add `--ai` only with `OPENAI_API_KEY`; this uses strict structured output, sends `store=false`, and records the model/version as label provenance. Human review and a chronological holdout remain required before using the dataset for model training.
