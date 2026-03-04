param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_Tomorrow_Followup_Once"
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null

$marker = Join-Path $RepoRoot "logs\tomorrow_followup_registration.json"
if (Test-Path $marker) {
    Remove-Item -Path $marker -Force
}

Write-Output "unregistered task: $TaskName"
Write-Output "removed marker: $marker"
