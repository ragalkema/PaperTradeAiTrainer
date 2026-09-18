# Database

PostgreSQL stores durable research facts. Apply migrations with `alembic upgrade head`; application
code must access these tables through PaperTrading repository/query ports. Dashboard does not own
the schema. Generated market/news datasets and model artifacts remain outside this database.

PostgreSQL stores normalized metadata, virtual trading records, and experiment results. Raw immutable datasets may later be referenced from object storage rather than stored directly in Git or relational rows.

Alembic owns schema changes through the root `alembic.ini`. The initial migration environment is in `migrations/`; add the first revision alongside the first persistent PaperTrading model.
