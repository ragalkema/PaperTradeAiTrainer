# Database

PostgreSQL stores normalized metadata, virtual trading records, and experiment results. Raw immutable datasets may later be referenced from object storage rather than stored directly in Git or relational rows.

Alembic owns schema changes. The initial migration environment is in `migrations/`; add the first revision alongside the first persistent model.
