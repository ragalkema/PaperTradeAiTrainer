param([string]$OutputDirectory = "backups")
$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$ResolvedOutput = Join-Path $RepositoryRoot $OutputDirectory
New-Item -ItemType Directory -Path $ResolvedOutput -Force | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutputFile = Join-Path $ResolvedOutput "papertrading-$Timestamp.dump"
docker compose exec -T postgres pg_dump -U papertrading -d papertrading -Fc > $OutputFile
Write-Host "Backup written to $OutputFile (ignored by Git)."
