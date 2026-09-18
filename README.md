# PaperTradeAiTrainer

A modular research platform for collecting crypto context, simulating virtual trading, and training/comparing AI trading agents under reproducible market conditions.

> **Paper trading only.** This repository cannot execute real trades and is not financial advice. It has no real-order interface, and bots never receive exchange credentials.

## Architecture

```mermaid
flowchart LR
    BV[Bitvavo public market data]
    NEWS[Crypto news - future]
    SOCIAL[Social media - future]
    NEWS --> DC[DataCollector]
    SOCIAL --> DC
    BV --> PT[PaperTrading]
    DC --> DATA[(Research data)]
    PT --> DATA
    DATA --> AI[AiTrainer]
    AI -->|BotAction| PT
    PT -->|MarketState / TradeResult| AI
    PT --> RESULTS[(Paper results)]
    AI --> EXP[(Experiments)]
```

The repository is one deployable-by-choice monorepo with strong logical boundaries:

- **DataCollector** asks what is happening outside the market. It will acquire and normalize news/social data while preserving immutable raw input.
- **PaperTrading** retrieves public Bitvavo market data and deterministically simulates spot BUY/SELL/HOLD with independent virtual portfolios.
- **AiTrainer** currently supplies three baseline bots and reproducible historical comparison; future ML/RL training stays here.
- **shared** defines the small, framework-neutral language those projects use to communicate.
- **Dashboard** is the native PySide6 observer/controller and primary interface.
- **frontend** remains an archived web-interface foundation rather than the primary UI.

Each Python project follows pragmatic Clean Architecture: interfaces and infrastructure depend on application/domain, while application defines ports and domain remains framework-free. Projects do not import one another's internals. See [architecture overview](docs/architecture/overview.md).

## Repository map

```text
DataCollector/    external text acquisition and normalization
PaperTrading/     market observations and virtual execution
AiTrainer/        bots, training, backtesting, evaluation
shared/           inter-project contracts only
tests/            architecture, contract, and end-to-end tests
validation/       trust checks for boundaries/environment/system
data/             ignored local raw/normalized/feature data
models/           ignored model artifacts
experiments/      versioned configs; ignored results/reports
database/         Alembic migration foundation
frontend/         React/TypeScript/Vite dashboard foundation
Dashboard/        native PySide6 research dashboard and Windows build
docs/             architecture, data, and development guidance
```

## Setup

Requirements: Python 3.12+, Node.js 24 LTS, npm, and Docker Compose.

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
docker compose up -d
```

POSIX shells can use `cp .env.example .env` and `./scripts/setup.sh`. PostgreSQL and Redis bind only to localhost and use obvious development-only credentials.

Run the PaperTrading status API:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn paper_trading.interfaces.api:app --reload
```

`GET /health` returns `{"status":"healthy","trading_mode":"paper"}`. Run the native dashboard with `.\scripts\run-dashboard.ps1`.

Use the functional MVP:

```powershell
# Public data; no API credentials required
python -m paper_trading price BTC-EUR
python -m paper_trading candles BTC-EUR 1h --limit 100

# Interactive virtual account
python -m paper_trading trade

# Three independent baseline bots on identical historical candles
python scripts/run_experiment.py BTC-EUR 1h --limit 100 --seed 42
```

See [PaperTrading](PaperTrading/README.md), [AiTrainer](AiTrainer/README.md), and the [MVP execution notes](docs/development/paper-trading.md).

## Tests and validation

```powershell
.\scripts\test.ps1
.\scripts\test.ps1 -m unit
.\scripts\test.ps1 -m "not slow"
.\scripts\validate.ps1
```

Tests verify expected software behavior. Validation checks whether actual data, configuration, contracts, or system state can be trusted. Project-local tests stay with each owner; root tests cover cross-project compatibility. Details are in [testing](docs/development/testing.md) and [validation](docs/development/validation.md).

Quality checks:

```powershell
ruff check .
ruff format --check .
mypy
pytest
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend
```

## Data and ML safety

Raw data is immutable. The pipeline is raw → normalized → features → training/backtesting. At time T, bots see only information available at or before T. External text retains `published_at`, `received_at`, and `processed_at`; training uses chronological splits and training-only normalization statistics. See [data pipeline](docs/data/data-pipeline.md), [timestamps](docs/data/timestamps.md), and [leakage prevention](docs/data/leakage-prevention.md).

Generated datasets, model binaries, experiment results, logs, database dumps, and secrets are ignored. Store large artifacts in versioned local/object storage with checksums and provenance. Heavy dependencies such as PyTorch, TensorFlow, Stable-Baselines3, Transformers, and XGBoost are intentionally absent.

## Security

`.env` is ignored; `.env.example` contains placeholders only. Public market data and paper trading must not require trading-enabled credentials. Never log secrets or expose `BITVAVO_API_SECRET` to bots. Any future real-trading capability would require a separately reviewed architecture and does not belong in PaperTrading.

CodeQL, Dependabot, per-project CI, architecture CI, frontend CI, pre-commit, and repository templates are configured. GitHub secret scanning, push protection, default branch, and repository rules must be enabled in GitHub settings.

## Development workflow and roadmap

Use `feature/*` → `dev` → `main`; see [Git workflow](docs/development/git-workflow.md). Shared market contracts, public Bitvavo data, deterministic spot paper execution, baseline bots, and initial historical comparison are implemented. See the remaining [roadmap](docs/roadmap.md).

## License

[MIT](LICENSE)
