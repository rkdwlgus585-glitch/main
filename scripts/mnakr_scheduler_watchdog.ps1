# Keeps mnakr scheduler alive for the current user session.
param(
    [string]$RepoRoot = "",
    [int]$StartupDelaySec = 0
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
$scriptName = "mnakr_scheduler_watchdog.ps1"
$krOnlyLockPath = Join-Path $RepoRoot "logs\kr_only_mode.lock"

if (Test-Path $krOnlyLockPath) {
    exit 0
}

if (-not (Test-Path (Join-Path $RepoRoot "mnakr.py"))) {
    exit 1
}

$pythonExe = "C:\Users\rkdwl\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $pythonExe = $pyLauncher.Source
    } else {
        exit 1
    }
}

function Test-SchedulerRunning {
    $rows = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^python(?:\.exe)?$" -and $_.CommandLine -match "mnakr\.py\s+--scheduler"
    }
    return [bool]($rows | Select-Object -First 1)
}

function Start-Scheduler {
    if ($pythonExe.ToLowerInvariant().EndsWith("py.exe")) {
        Start-Process -FilePath $pythonExe -ArgumentList "-3 mnakr.py --scheduler" -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
    } else {
        Start-Process -FilePath $pythonExe -ArgumentList "mnakr.py --scheduler" -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
    }
}

# Prevent duplicate watchdog loops.
$currentPid = $PID
$dupeRows = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^powershell(?:\.exe)?$" `
    -and $_.ProcessId -ne $currentPid `
    -and $_.CommandLine -match "(?i)-file\s+" `
    -and $_.CommandLine -match [regex]::Escape($scriptName)
}
if (($dupeRows | Measure-Object).Count -gt 0) {
    exit 0
}

$delaySec = [int]$StartupDelaySec
if ($delaySec -gt 0) {
    Start-Sleep -Seconds $delaySec
}

while ($true) {
    if (-not (Test-SchedulerRunning)) {
        Start-Scheduler
    }
    Start-Sleep -Seconds 30
}
