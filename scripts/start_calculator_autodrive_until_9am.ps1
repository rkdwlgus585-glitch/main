param(
    [string]$RepoRoot = "",
    [string]$EndAt = "",
    [int]$PilotMinutes = 20,
    [double]$PilotSleepSec = 1.5,
    [int]$StressYangdoIterations = 120,
    [int]$StressAcqIterations = 120,
    [int]$CycleCooldownSec = 20,
    [int]$MaxTrainRows = 260,
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\run_calculator_autodrive.py"
if (-not (Test-Path $runner)) {
    throw "runner not found: $runner"
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^(?:python|py)(?:\.exe)?$" -and $_.CommandLine -match "run_calculator_autodrive\.py"
}

if ($existing -and -not $ForceRestart) {
    $ids = ($existing | Select-Object -ExpandProperty ProcessId) -join ","
    Write-Output ("already_running pid={0}" -f $ids)
    exit 0
}

if ($existing -and $ForceRestart) {
    foreach ($p in $existing) {
        try {
            Stop-Process -Id $p.ProcessId -Force
        } catch {
        }
    }
    Start-Sleep -Seconds 1
}

$pythonExe = ""
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    $pythonExe = $py.Source
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $pythonExe = $python.Source
    } else {
        throw "python launcher not found (py/python)"
    }
}

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$krOnlyLock = Join-Path $logsDir "kr_only_mode.lock"
@{
    enabled = $true
    reason = "start_calculator_autodrive_until_9am.ps1"
    locked_at = (Get-Date).ToString("s")
} | ConvertTo-Json -Depth 4 | Set-Content -Path $krOnlyLock -Encoding UTF8

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$stdoutPath = Join-Path $logsDir ("calculator_autodrive_stdout_{0}.log" -f $ts)
$stderrPath = Join-Path $logsDir ("calculator_autodrive_stderr_{0}.log" -f $ts)
$pidPath = Join-Path $logsDir "calculator_autodrive.pid"

$argList = @()
if ($pythonExe.ToLowerInvariant().EndsWith("py.exe")) {
    $argList += "-3"
}
$argList += "scripts/run_calculator_autodrive.py"
if (-not [string]::IsNullOrWhiteSpace($EndAt)) {
    $argList += @("--end-at", $EndAt)
}
$argList += @(
    "--pilot-minutes", [string]([Math]::Max(1, $PilotMinutes)),
    "--pilot-sleep-sec", [string]([Math]::Max(0.1, $PilotSleepSec)),
    "--stress-yangdo-iterations", [string]([Math]::Max(20, $StressYangdoIterations)),
    "--stress-acq-iterations", [string]([Math]::Max(20, $StressAcqIterations)),
    "--cycle-cooldown-sec", [string]([Math]::Max(5, $CycleCooldownSec)),
    "--max-train-rows", [string]([Math]::Max(100, $MaxTrainRows)),
    "--context-file", "docs/calculator_autopilot_context.json",
    "--skills-doc", "docs/skills_context_booster.md",
    "--ensure-kr-lock"
)

$proc = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList $argList `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -PassThru

Set-Content -Path $pidPath -Value ([string]$proc.Id) -Encoding UTF8

Write-Output ("started pid={0}" -f $proc.Id)
Write-Output ("stdout={0}" -f $stdoutPath)
Write-Output ("stderr={0}" -f $stderrPath)
Write-Output ("state={0}" -f (Join-Path $logsDir "calculator_autodrive_state.json"))
Write-Output ("latest={0}" -f (Join-Path $logsDir "calculator_autodrive_latest.json"))
Write-Output ("backlog={0}" -f (Join-Path $logsDir "calculator_autodrive_backlog.md"))
Write-Output ("kr_lock={0}" -f $krOnlyLock)
