param(
    [string]$TaskName = "SeoulMNA_Ops_Watchdog"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$delegate = Join-Path $repoRoot "scripts\unregister_cokr_watchdog_tasks.ps1"
if (-not (Test-Path $delegate)) {
    throw "delegate not found: $delegate"
}

Write-Output "legacy unregister script detected; removing split co.kr watchdog tasks"
& $delegate
