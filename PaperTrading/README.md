# PaperTrading

Owns normalized public market observations, virtual orders, portfolios, and deterministic simulation. It is paper-only: there is no real-order port, no withdrawal/deposit concept, and no bot access to exchange credentials.

Dependency direction is interfaces/infrastructure → application → domain. Bitvavo is reserved for a future public market-data adapter only. See `docs/architecture/paper-trading.md`.
