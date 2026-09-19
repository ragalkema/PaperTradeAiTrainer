$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepositoryRoot
docker compose up -d postgres
python -m alembic upgrade head
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-File", (Join-Path $PSScriptRoot "run-data-operations.ps1")
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-File", (Join-Path $PSScriptRoot "run-dashboard.ps1")
Write-Host "PostgreSQL, Data Operations, and Dashboard were started explicitly."
