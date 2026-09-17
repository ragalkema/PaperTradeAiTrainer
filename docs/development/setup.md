# Development setup

Requirements are Python 3.12+, Node.js 24 LTS (20.19+ remains locally compatible), npm, and Docker Compose.

On PowerShell:

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
docker compose up -d
```

On POSIX shells use `cp .env.example .env` and `./scripts/setup.sh`. Development database credentials are local-only. Public market data and paper trading must not require trading-enabled Bitvavo credentials.

Run the API with `uvicorn paper_trading.interfaces.api:app --reload` and the dashboard with `npm run dev --prefix frontend`.
