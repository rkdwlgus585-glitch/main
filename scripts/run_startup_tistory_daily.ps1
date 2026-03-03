# Runs tistory daily-once publish mode once at startup/logon.
param(
    [string]$RepoRoot = "",
    [string]$StartRegistration = "7540",
    [int]$StartupDelaySec = 0,
    [int]$PublishRetries = 2,
    [int]$PublishRetryBackoffSec = 20,
    [int]$TimeoutSec = 60
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
if (-not (Test-Path (Join-Path $RepoRoot "tistory_ops\run.py"))) {
    exit 1
}

$pythonExe = "C:\Users\rkdwl\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $pythonExe = $pyLauncher.Source
    } else {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            $pythonExe = $pythonCmd.Source
        } else {
            exit 1
        }
    }
}

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$logFile = Join-Path $logsDir "startup_tistory_daily.log"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

Write-Log "START tistory daily-once"

if ($StartupDelaySec -gt 0) {
    Write-Log ("startup delay begin: {0}s" -f [int]$StartupDelaySec)
    Start-Sleep -Seconds ([int]$StartupDelaySec)
    Write-Log "startup delay end"
}

Push-Location $RepoRoot
try {
    $args = @(
        "tistory_ops/run.py",
        "daily-once",
        "--start-registration", $StartRegistration,
        "--audit-tag", "startup_daily",
        "--no-interactive-login",
        "--login-wait-sec", "45",
        "--timeout-sec", "$TimeoutSec",
        "--publish-retries", "$PublishRetries",
        "--publish-retry-backoff-sec", "$PublishRetryBackoffSec"
    )
    $cmdOutput = $null
    if ($pythonExe.ToLowerInvariant().EndsWith("py.exe")) {
        $cmdOutput = & $pythonExe -3 @args 2>&1
    } else {
        $cmdOutput = & $pythonExe @args 2>&1
    }
    if ($null -ne $cmdOutput) {
        foreach ($line in $cmdOutput) {
            Add-Content -Path $logFile -Encoding UTF8 -Value ([string]$line)
        }
    }
    $rc = 0
    if ($LASTEXITCODE -ne $null) {
        $rc = [int]$LASTEXITCODE
    }
    Write-Log ("END tistory daily-once rc={0}" -f $rc)
    exit $rc
} catch {
    Write-Log ("ERROR tistory daily-once: {0}" -f $_.Exception.Message)
    exit 1
} finally {
    Pop-Location
}
