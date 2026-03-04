$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$statePath = Join-Path $repoRoot "logs/yangdo_internal_fuzz_process.json"

if (-not (Test-Path $statePath)) {
    Write-Host "no_state_file"
    exit 0
}

try {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
} catch {
    Write-Host "invalid_state_file"
    exit 0
}

$procId = 0
if ($state -and $state.pid) {
    $procId = [int]$state.pid
}
if ($procId -le 0) {
    Write-Host "no_pid"
    exit 0
}

$proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "already_stopped"
    exit 0
}

Stop-Process -Id $procId -Force
Write-Host ("stopped pid={0}" -f $procId)
