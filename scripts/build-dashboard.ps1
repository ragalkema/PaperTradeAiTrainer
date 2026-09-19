param([switch]$OneFile)
$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepositoryRoot
python -m pip install -e ".[build]"
if ($OneFile) {
    python -m PyInstaller --noconfirm --clean --windowed --onefile `
        --name PaperTradeAiTrainer `
        --paths Dashboard/src --paths DataCollector/src --paths DataOperations/src --paths PaperTrading/src --paths shared/src `
        Dashboard/src/dashboard/main.py
} else {
    python -m PyInstaller --noconfirm --clean Dashboard/PaperTradeAiTrainer.spec
}
$Executable = if ($OneFile) {
    Join-Path $RepositoryRoot "dist\PaperTradeAiTrainer.exe"
} else {
    Join-Path $RepositoryRoot "dist\PaperTradeAiTrainer\PaperTradeAiTrainer.exe"
}
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Dashboard executable was not produced: $Executable"
}
Write-Host "Built $Executable"
