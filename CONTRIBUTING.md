# Contributing

Use `feature/<short-description>` branches from `dev`. Keep changes focused, add meaningful tests, and open a pull request into `dev`. Releases move from `dev` to `main` through a reviewed pull request.

Before opening a pull request, run the backend Ruff, mypy, and pytest checks plus the frontend lint, typecheck, test, and build commands documented in the root README. Never commit secrets, raw datasets, model binaries, logs, or database dumps.

This is a paper-trading-only project. Contributions that introduce real-order execution or expose trading credentials require an explicit architectural decision and are out of scope for the current system.
