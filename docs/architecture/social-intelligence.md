# Social intelligence architecture

```text
X API v2 -> XRecentSearchAdapter -> RawSocialPost -> SocialEvent
       -> versioned online SocialIntelligence -> SocialFeatureSnapshot -> future AiTrainer

SocialEvent -> future market observations -> SocialMarketReaction
            -> SocialMarketImpact -> Dashboard research only
```

X is infrastructure. Domain contracts use provider-neutral “social post/event” language so another provider can be added without changing future AiTrainer inputs.

## Selected X API capabilities

The adapter uses the current X API v2 application-bearer endpoint `GET https://api.x.com/2/tweets/search/recent`. It combines tracked accounts with `from:` operators, requests up to 100 results, follows `meta.next_token`, expands authors, and requests `created_at`, language, references, edit history, and public metrics. X also documents user lookup/timeline and filtered-stream capabilities, but availability, retention, rate limits, and pricing depend on the developer plan. HTTP 429 reads `x-rate-limit-reset` or `Retry-After` and exposes the retry time rather than hammering the API. See the [official recent-search/pagination documentation](https://docs.x.com/xdks/python/pagination) and [official field reference](https://docs.x.com/x-api/posts/english-language-firehose-stream).

No scraping or API-access evasion is implemented. Operators must review their current X agreement for storage, deletion, redistribution, and compliance obligations. Raw versions are retained separately when content or metrics change; downstream exports should avoid redistributing post text unless permitted.

## Point-in-time rules

`created_at` is provider time, `received_at` is first local observation, and `processed_at` is normalized availability. Online queries require receipt and processing at or before the decision time. Engagement is append-only: queries select the newest snapshot whose `observed_at <= decision_time`.

## Online algorithms

- Relevance `social_relevance_v1`: explicit cashtags score 0.95; bounded BTC/ETH/SOL aliases use the existing deterministic relevance detector.
- Sentiment `lexical_social_asset_sentiment_v1`: transparent asset-specific lexical context, not a truth or transformer model.
- Influence `estimated_account_influence_v1`: capped follower scale 40%, typical engagement 30%, activity 15%, and configured category contribution up to 15%. Influence is not trust.
- Importance `social_importance_v1`: relevance 30%, influence 20%, novelty 17%, category severity, and a base factor. No future price data.
- Novelty `social_chronological_jaccard_v1`: social-to-social token similarity using only earlier receipts; repost novelty is discounted.

`online_social_features_v1` includes post counts (15m/1h/6h), unique accounts, mean sentiment, relevance/importance/influence-weighted sentiment, maximum relevance/importance/novelty, high-influence count, breaking count, optional activity z-score, and point-in-time engagement velocity. Insufficient history produces `NULL` activity z-score.

Retrospective `social_market_impact_v1` combines online relevance, importance, novelty, influence, and mature abnormal return/volume. It is temporal association, not causality, and cannot enter the online query port.
