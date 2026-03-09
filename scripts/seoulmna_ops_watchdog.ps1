# Legacy compatibility shim.
# The mixed watchdog has been replaced by split profile workers:
# - listing
# - notice
# - admin_memo
# - site_health
# - permit
param(
    [string]$RepoRoot = "",
    [int]$StartupDelaySec = 0
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\seoulmna_watchdog_worker.ps1"
if (-not (Test-Path $runner)) {
    exit 1
}

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$logFile = Join-Path $logsDir "ops_watchdog_legacy.log"

function Write-LegacyLog([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

if ($StartupDelaySec -gt 0) {
    Start-Sleep -Seconds ([int]$StartupDelaySec)
}

$profiles = @("listing", "notice", "admin_memo", "site_health", "permit")
Write-LegacyLog "legacy mixed watchdog shim start"
foreach ($profile in $profiles) {
    $arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`" -RepoRoot `"$RepoRoot`" -Profile `"$profile`""
    try {
        Start-Process -FilePath "powershell.exe" -ArgumentList $arg -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
        Write-LegacyLog ("spawned profile={0}" -f $profile)
    } catch {
        Write-LegacyLog ("failed profile={0}: {1}" -f $profile, $_.Exception.Message)
    }
}
Write-LegacyLog "legacy mixed watchdog shim exit"
exit 0
