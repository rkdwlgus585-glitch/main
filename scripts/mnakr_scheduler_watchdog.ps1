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
$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$watchdogLog = Join-Path $logsDir "mnakr_scheduler_watchdog.log"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $watchdogLog -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Test-CalculatorAutodriveRunning {
    $rows = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^(?:python|py)(?:\.exe)?$" -and $_.CommandLine -match "run_calculator_autodrive\.py"
    }
    return [bool]($rows | Select-Object -First 1)
}

function Test-KrOnlyLockActive([string]$lockPath) {
    if (-not (Test-Path $lockPath)) {
        return $false
    }

    if (Test-CalculatorAutodriveRunning) {
        return $true
    }

    $raw = ""
    $reason = ""
    try {
        $raw = Get-Content -Path $lockPath -Raw -Encoding UTF8
    } catch {
        $raw = ""
    }

    if (-not [string]::IsNullOrWhiteSpace($raw) -and $raw.TrimStart().StartsWith("{")) {
        try {
            $obj = $raw | ConvertFrom-Json
            if ($obj -and $obj.reason) {
                $reason = [string]$obj.reason
            }
        } catch {
        }
    }

    if ($reason -match "(?i)run_calculator_autodrive|start_calculator_autodrive") {
        try {
            Remove-Item $lockPath -Force
        } catch {
        }
        return $false
    }

    return $true
}

if (Test-KrOnlyLockActive $krOnlyLockPath) {
    Write-Log "kr-only lock active: skip mnakr scheduler watchdog"
    exit 0
}

if (-not (Test-Path (Join-Path $RepoRoot "mnakr.py"))) {
    Write-Log "mnakr.py missing: watchdog stop"
    exit 1
}

$pythonExe = "C:\Users\rkdwl\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $pythonExe = $pyLauncher.Source
    } else {
        Write-Log "python launcher not found: watchdog stop"
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
    Write-Log "duplicate watchdog detected: exit current process"
    exit 0
}

$delaySec = [int]$StartupDelaySec
if ($delaySec -gt 0) {
    Write-Log ("startup delay begin: {0}s" -f $delaySec)
    Start-Sleep -Seconds $delaySec
    Write-Log "startup delay end"
}

$loopCount = 0
Write-Log ("watchdog loop started (repo={0})" -f $RepoRoot)
while ($true) {
    $loopCount += 1
    if (-not (Test-SchedulerRunning)) {
        Write-Log "scheduler process missing: attempting restart"
        Start-Scheduler
        Start-Sleep -Seconds 2
        if (Test-SchedulerRunning) {
            Write-Log "scheduler restart success"
        } else {
            Write-Log "scheduler restart attempted but process still missing"
        }
    } elseif (($loopCount % 20) -eq 0) {
        Write-Log "scheduler healthy"
    }
    Start-Sleep -Seconds 30
}
