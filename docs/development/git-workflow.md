# Git workflow

Use `feature/*` → `dev` → `main`. `main` is stable; `dev` integrates reviewed features. Do not force-push or delete protected branches.

For `main`, require pull requests, applicable CI, conversation resolution, and block force pushes/deletion. For a solo repository, zero mandatory approvals is practical. For `dev`, require normal feature pull requests and applicable CI, but avoid settings that prevent emergency solo maintenance. Because workflows are path-filtered, do not require unrelated project checks unconditionally.
