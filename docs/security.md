# Security

## Financial safety boundary

This repository is paper trading only. It has no real-order endpoint, exchange execution adapter, or production trading credential path. Bots receive normalized market state—not Bitvavo clients or secrets—and the paper exchange creates only virtual orders. Public market data and paper trading must operate without Bitvavo credentials.

Any future real-trading capability would require a separate module, explicit threat model and review, distinct credentials and deployment, restrictive permissions, kill switches, audit logging, and a deliberate architectural decision. It must never be introduced as a small extension to `PaperExchange`.

## Secret handling

Commit only `.env.example`, never `.env`. Never log API keys, tokens, database credentials, private keys, authorization headers, or complete configuration objects. Use GitHub environment/repository secrets in CI and a secret manager outside local development. If a secret is committed, revoke it first, then remove it from history using a coordinated procedure.

Use market-data-only credentials if a provider eventually requires authentication. Never place withdrawal-enabled or real-order-enabled credentials in this application.

## Repository controls

CodeQL scans Python and TypeScript. Dependabot proposes grouped weekly dependency updates and monthly Actions updates. Enable GitHub secret scanning and push protection in repository settings, plus private-vulnerability reporting where available. Review workflow permission changes and pin third-party actions to trusted releases or commit SHAs when the threat model requires it.

Structured logging should use event names such as `market_data_received`, `bot_decision`, `paper_order_created`, `paper_order_filled`, `news_received`, `feature_generated`, `experiment_started`, and `experiment_finished`, but only when useful and without sensitive payloads.
