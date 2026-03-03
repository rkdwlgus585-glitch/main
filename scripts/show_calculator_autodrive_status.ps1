param(
    [string]$RepoRoot = ""
)

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$statePath = Join-Path $RepoRoot "logs\calculator_autodrive_state.json"
$latestPath = Join-Path $RepoRoot "logs\calculator_autodrive_latest.json"
$krLockPath = Join-Path $RepoRoot "logs\kr_only_mode.lock"
$trafficPath = Join-Path $RepoRoot "logs\calculator_autodrive_traffic_guard.json"

$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^(?:python|py)(?:\.exe)?$" -and $_.CommandLine -match "run_calculator_autodrive\.py"
}
if ($procs) {
    Write-Output "== process =="
    $procs | Select-Object ProcessId, Name, CreationDate, CommandLine
} else {
    Write-Output "process not running"
}

if (Test-Path $statePath) {
    Write-Output "== state =="
    Get-Content $statePath -Encoding UTF8
} else {
    Write-Output "state not found: $statePath"
}

if (Test-Path $latestPath) {
    Write-Output "== latest =="
    Get-Content $latestPath -Encoding UTF8
} else {
    Write-Output "latest not found: $latestPath"
}

if ((-not $procs) -and (Test-Path $latestPath)) {
    try {
        $latest = Get-Content $latestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($latest.status -eq "running") {
            Write-Output "note: latest.status=running but process not running (stale latest file)"
        }
    } catch {
    }
}

if (Test-Path $krLockPath) {
    Write-Output "== kr_only_mode.lock =="
    Get-Content $krLockPath -Encoding UTF8
} else {
    Write-Output "kr lock not found: $krLockPath"
}

if (Test-Path $trafficPath) {
    Write-Output "== traffic_guard =="
    Get-Content $trafficPath -Encoding UTF8
}
