param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_Ops_Watchdog",
    [int]$StartupDelaySec = 0
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$delegate = Join-Path $RepoRoot "scripts\register_cokr_watchdog_tasks.ps1"
if (-not (Test-Path $delegate)) {
    throw "delegate not found: $delegate"
}

Write-Output "legacy register script detected; delegating to split co.kr watchdog task registration"
& $delegate -RepoRoot $RepoRoot -BaseStartupDelaySec $StartupDelaySec
