# Startup runner (split-mode):
# - Unified all-at-once execution is disabled to reduce load/429 risk.
# - Keep only listing/site ops watchdog here.
# - Blog/Tistory should be launched separately via their own launchers.
param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$logFile = Join-Path $logsDir "startup_all.log"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Start-HiddenPowerShell([string]$scriptPath, [string]$argLine, [string]$jobName) {
    if (-not (Test-Path $scriptPath)) {
        Write-Log ("SKIP {0}: script missing ({1})" -f $jobName, $scriptPath)
        return
    }
    $arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" {0}" -f $argLine
    Start-Process -FilePath "powershell.exe" -ArgumentList $arg -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
    Write-Log ("START {0}" -f $jobName)
}

function Ensure-Watchdog([string]$scriptName, [string]$scriptPath, [string]$argLine, [string]$jobName) {
    $exists = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^powershell(?:\.exe)?$" -and $_.CommandLine -match [regex]::Escape($scriptName)
    }
    if (($exists | Measure-Object).Count -ge 1) {
        Write-Log ("KEEP {0}: already running" -f $jobName)
        return
    }
    Start-HiddenPowerShell -scriptPath $scriptPath -argLine $argLine -jobName $jobName
}

Write-Log "START unified startup"

$opsWatchdog = Join-Path $RepoRoot "scripts\seoulmna_ops_watchdog.ps1"
$secureApiStack = Join-Path $RepoRoot "scripts\run_secure_api_stack.ps1"
Write-Log "SPLIT mode enabled: skip all-in-one startup(blog/tistory/wp scheduler)"
Write-Log "Use separate launchers: launchers\\launch_blog.bat, launchers\\launch_tistory_publish.bat"
Write-Log "SKIP ops_watchdog: dedicated startup task owns watchdog lifecycle"
Ensure-Watchdog -scriptName "run_secure_api_stack.ps1" -scriptPath $secureApiStack -argLine "-RepoRoot `"$RepoRoot`"" -jobName "secure_api_stack"

Write-Log "END unified startup"
exit 0
