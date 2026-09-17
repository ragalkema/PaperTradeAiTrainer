$ErrorActionPreference = "Stop"

python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
npm ci --prefix frontend

Write-Host "Setup complete. Copy .env.example to .env before running services."
