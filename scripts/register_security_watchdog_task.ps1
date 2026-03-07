param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_Security_Watchdog",
    [int]$IntervalMinutes = 15
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
$watchdog = Join-Path $RepoRoot "scripts\security_event_watchdog.py"
if (-not (Test-Path $watchdog)) {
    throw "watchdog not found: $watchdog"
}

$pythonExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Launcher\py.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "py"
}
$arg = "-3 `"$watchdog`" --lookback-min $([Math]::Max(5,$IntervalMinutes))"

$startAt = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $startAt `
    -RepetitionInterval (New-TimeSpan -Minutes ([Math]::Max(5,$IntervalMinutes))) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $arg -WorkingDirectory $RepoRoot
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -Hidden `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Run SeoulMNA API security watchdog on a fixed interval." `
    -Force | Out-Null

Write-Output "registered task: $TaskName interval=${IntervalMinutes}m"
