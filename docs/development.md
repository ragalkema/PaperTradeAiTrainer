# Development workflow

## Branches

`main` is stable, `dev` is the integration branch, and `feature/*` branches start from and merge into `dev`. Release pull requests merge `dev` into `main`. Do not rewrite shared history.

Recommended solo-friendly repository rules:

### `main`

- Require a pull request with one approval when another maintainer is available; allow zero required approvals for a solo repository.
- Require `Backend CI / quality` and `Frontend CI / quality` when applicable.
- Require conversation resolution.
- Block force pushes and deletion.
- Require branches to be up to date only if merge-queue churn is acceptable.
- Restrict bypass to the repository administrator for emergencies.

### `dev`

- Use pull requests for normal feature work.
- Require applicable backend/frontend checks.
- Block force pushes and deletion.
- Do not require an approval for a solo maintainer.

Because path-filtered workflows may not create a status on unrelated changes, GitHub rules should not require both path-filtered checks unconditionally. Use rulesets with file-path conditions, or add a lightweight aggregate check before making both mandatory.

## Local checks

From `backend`: `ruff check .`, `ruff format --check .`, `mypy .`, and `pytest`.

From `frontend`: `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build`.

Optional pre-commit setup: install `pre-commit`, run `pre-commit install`, then `pre-commit run --all-files`.
