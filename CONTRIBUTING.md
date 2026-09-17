# Contributing

Use `feature/<short-description>` branches from `dev`. Keep changes focused, add meaningful tests, and open a pull request into `dev`. Releases move from `dev` to `main` through a reviewed pull request.

Before opening a pull request, run root Ruff, mypy, pytest, and validation checks plus the frontend lint, typecheck, test, and build commands documented in the root README. Keep project-local behavior and tests inside its bounded context; use `shared` only for genuine communication contracts. Never commit secrets, raw datasets, model binaries, logs, or database dumps.

This is a paper-trading-only project. Contributions that introduce real-order execution or expose trading credentials require an explicit architectural decision and are out of scope for the current system.
