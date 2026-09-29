param([string]$Workspace = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$mutex = New-Object System.Threading.Mutex($false, 'Local\PaperTradeAiTrainer-PublicResearch')
if (-not $mutex.WaitOne(0)) { $mutex.Dispose(); exit 0 }
$workers = @{}
try {
    $python = Join-Path $Workspace '.venv\Scripts\python.exe'
    $configPath = Join-Path $Workspace 'experiments\results\research-runtime.json'
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $models = @()
    foreach ($model in $config.models) {
        $path = (Resolve-Path -LiteralPath (Join-Path $Workspace $model.path)).Path
        if (-not $path.StartsWith($Workspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Model path outside workspace'
        }
        if ((Get-FileHash -LiteralPath $path).Hash -ne $model.sha256) { throw 'Frozen model changed' }
        $models += ('"' + $path + '"')
    }
    $logDir = Join-Path $Workspace 'logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $stopFile = Join-Path $Workspace 'experiments\results\public-research.stop'
    $statusFile = Join-Path $logDir 'public-research-supervisor.json'
    $roles = @{
        'public-collector' = @('-u','-m','data_operations','run-public')
        'content-shadow' = @('-u','-m','ai_trainer','shadow-content','--models') + $models + @('--watch')
    }
    $nextStart = @{}
    $starts = @{}
    $dockerReady = $false
    $nextDocker = [DateTime]::MinValue
    while (-not (Test-Path -LiteralPath $stopFile)) {
        $now = [DateTime]::UtcNow
        if (-not $dockerReady -and $now -ge $nextDocker) {
            $nextDocker = $now.AddMinutes(1)
            $desktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
            if (-not (Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue) -and
                (Test-Path -LiteralPath $desktop)) {
                Start-Process -FilePath $desktop -WindowStyle Hidden | Out-Null
            }
            # Start only the existing project database; never recreate or delete volumes.
            $docker = Start-Process -FilePath 'docker.exe' -ArgumentList 'start','paper-trade-ai-postgres-1' `
                -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'database-start.stdout.log') `
                -RedirectStandardError (Join-Path $logDir 'database-start.stderr.log')
            # Cache the native handle before waiting; otherwise Windows PowerShell can lose ExitCode.
            $null = $docker.Handle
            if ($docker.WaitForExit(10000)) {
                $docker.Refresh()
                $dockerReady = $docker.ExitCode -eq 0
            }
            else { $docker.Kill() }
        }
        $state = @()
        foreach ($role in $roles.Keys) {
            $worker = $workers[$role]
            if (-not $worker -or $worker.HasExited) {
                if (-not $nextStart.ContainsKey($role)) { $nextStart[$role] = $now }
                if ($now -ge $nextStart[$role]) {
                    $stamp = $now.ToString('yyyyMMdd-HHmmss-fff')
                    $workers[$role] = Start-Process -FilePath $python -ArgumentList $roles[$role] `
                        -WorkingDirectory $Workspace -WindowStyle Hidden -PassThru `
                        -RedirectStandardOutput (Join-Path $logDir "$role.managed-$stamp.stdout.log") `
                        -RedirectStandardError (Join-Path $logDir "$role.managed-$stamp.stderr.log")
                    $starts[$role] = 1 + [int]$starts[$role]
                    $nextStart[$role] = $now.AddSeconds(30)
                    $worker = $workers[$role]
                }
            }
            $state += @{ role=$role; pid=if ($worker) {$worker.Id} else {$null};
                         running=($worker -and -not $worker.HasExited); starts=$starts[$role] }
        }
        @{at=$now.ToString('o');supervisor_pid=$PID;database_started=$dockerReady;workers=$state} |
            ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ($statusFile + '.tmp') -Encoding UTF8
        Move-Item -LiteralPath ($statusFile + '.tmp') -Destination $statusFile -Force
        Start-Sleep -Seconds 10
    }
} finally {
    foreach ($worker in $workers.Values) {
        if ($worker -and -not $worker.HasExited) {
            # Only trees launched by this supervisor; include virtualenv's Python child.
            & taskkill.exe /PID $worker.Id /T /F | Out-Null
        }
    }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
