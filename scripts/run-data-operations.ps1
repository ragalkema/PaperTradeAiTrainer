$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = @(
    (Join-Path $RepositoryRoot "DataOperations\src")
    (Join-Path $RepositoryRoot "DataCollector\src")
    (Join-Path $RepositoryRoot "PaperTrading\src")
    (Join-Path $RepositoryRoot "shared\src")
) -join [IO.Path]::PathSeparator
Set-Location -LiteralPath $RepositoryRoot
python -m data_operations run
