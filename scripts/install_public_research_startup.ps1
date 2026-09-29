param([string]$Workspace = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$watcher = Join-Path $Workspace 'scripts\watch_public_research.ps1'
$shellPath = (Get-Command powershell.exe).Source
$arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $watcher + '"'
$taskName = 'PaperTradeAiTrainer-PublicResearch'
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and $existing.Actions.Arguments -ne $arguments) {
    throw 'Existing task has different configuration; refusing to overwrite'
}
try {
    $action = New-ScheduledTaskAction -Execute $shellPath -Argument $arguments -WorkingDirectory $Workspace
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $account
    $principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Principal $principal -Settings $settings -Force | Out-Null
    Write-Output 'Installed scheduled task at user logon, with supervisor restart on failure.'
} catch {
    # Standard-user fallback; no stored passwords, elevation or machine-wide changes.
    $startup = [Environment]::GetFolderPath('Startup')
    $shortcutPath = Join-Path $startup ($taskName + '.lnk')
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    if ((Test-Path -LiteralPath $shortcutPath) -and $shortcut.Arguments -ne $arguments) {
        throw 'Existing startup shortcut differs; refusing to overwrite'
    }
    $shortcut.TargetPath = $shellPath
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = $Workspace
    $shortcut.WindowStyle = 7
    $shortcut.Save()
    Write-Output 'Task Scheduler unavailable: installed per-user Startup shortcut. Worker restart is handled by the supervisor.'
    Write-Output $shortcutPath
}
