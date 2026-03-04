param(
    [switch]$ClearKrLock
)

$ErrorActionPreference = "SilentlyContinue"

$stopped = 0
$stoppedHeadless = 0

$rows = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^(?:python|py)(?:\.exe)?$" -and $_.CommandLine -match "run_calculator_autodrive\.py"
}

foreach ($r in $rows) {
    try {
        Stop-Process -Id $r.ProcessId -Force
        $stopped += 1
    } catch {
    }
}

# Stop webdriver/headless remnants created by automation only (safe scope).
$headlessRows = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq "chromedriver.exe") -or
    ($_.Name -eq "chrome.exe" -and $_.CommandLine -match "headless|webdriver|enable-automation|scoped_dir")
}
foreach ($r in $headlessRows) {
    try {
        Stop-Process -Id $r.ProcessId -Force
        $stoppedHeadless += 1
    } catch {
    }
}

Write-Output ("stopped={0}" -f $stopped)
Write-Output ("stopped_headless={0}" -f $stoppedHeadless)

$repoRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $repoRoot "logs\calculator_autodrive_state.json"
$latestPath = Join-Path $repoRoot "logs\calculator_autodrive_latest.json"
$pidPath = Join-Path $repoRoot "logs\calculator_autodrive.pid"
$krLockPath = Join-Path (Split-Path -Parent $PSScriptRoot) "logs\kr_only_mode.lock"

if (Test-Path $pidPath) {
    try {
        Remove-Item $pidPath -Force
        Write-Output ("pid_removed={0}" -f $pidPath)
    } catch {
        Write-Output ("pid_remove_failed={0}" -f $pidPath)
    }
}

if (Test-Path $statePath) {
    try {
        $state = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $state.status = "stopped"
        $state.message = "stopped_by_script"
        $state.stopped_at = (Get-Date).ToString("s")
        $state | ConvertTo-Json -Depth 12 | Set-Content -Path $statePath -Encoding UTF8
        Write-Output ("state_updated={0}" -f $statePath)
    } catch {
        Write-Output ("state_update_failed={0}" -f $statePath)
    }
}

if (Test-Path $latestPath) {
    try {
        $latest = Get-Content $latestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $latest | Add-Member -NotePropertyName status -NotePropertyValue "stopped" -Force
        $latest | Add-Member -NotePropertyName generated_at -NotePropertyValue ((Get-Date).ToString("s")) -Force
        $latest | Add-Member -NotePropertyName message -NotePropertyValue "stopped_by_script" -Force
        $latest | ConvertTo-Json -Depth 12 | Set-Content -Path $latestPath -Encoding UTF8
        Write-Output ("latest_updated={0}" -f $latestPath)
    } catch {
        Write-Output ("latest_update_failed={0}" -f $latestPath)
    }
}

if ($ClearKrLock -and (Test-Path $krLockPath)) {
    try {
        Remove-Item $krLockPath -Force
        Write-Output ("kr_lock_cleared={0}" -f $krLockPath)
    } catch {
        Write-Output ("kr_lock_clear_failed={0}" -f $krLockPath)
    }
} else {
    Write-Output ("kr_lock={0}" -f $(if (Test-Path $krLockPath) { "present" } else { "absent" }))
}
