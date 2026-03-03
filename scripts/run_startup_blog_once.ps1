# Runs mnakr startup publish mode once per day.
param(
    [string]$RepoRoot = "",
    [int]$StartupDelaySec = 0,
    [int]$RetryOnDeferredMax = 0,
    [int]$RetryOnDeferredWaitSec = 75
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
if (-not (Test-Path (Join-Path $RepoRoot "mnakr.py"))) {
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
$logFile = Join-Path $logsDir "startup_blog_once.log"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

Write-Log "START startup-once publish"

if ($StartupDelaySec -gt 0) {
    Write-Log ("startup delay begin: {0}s" -f [int]$StartupDelaySec)
    Start-Sleep -Seconds ([int]$StartupDelaySec)
    Write-Log "startup delay end"
}

Push-Location $RepoRoot
try {
    function Invoke-StartupOnce {
        if ($pythonExe.ToLowerInvariant().EndsWith("py.exe")) {
            & $pythonExe -3 mnakr.py --startup-once *>> $logFile
        } else {
            & $pythonExe mnakr.py --startup-once *>> $logFile
        }
        if ($LASTEXITCODE -ne $null) {
            return [int]$LASTEXITCODE
        }
        return 0
    }

    $rc = Invoke-StartupOnce
    $retryCount = 0
    while ($rc -eq 2 -and $retryCount -lt [int]$RetryOnDeferredMax) {
        $retryCount += 1
        Write-Log ("deferred rc=2 retry {0}/{1} after {2}s" -f $retryCount, [int]$RetryOnDeferredMax, [int]$RetryOnDeferredWaitSec)
        Start-Sleep -Seconds ([int]$RetryOnDeferredWaitSec)
        $rc = Invoke-StartupOnce
    }

    Write-Log ("END startup-once publish rc={0}" -f $rc)
    exit $rc
} catch {
    Write-Log ("ERROR startup-once publish: {0}" -f $_.Exception.Message)
    exit 1
} finally {
    Pop-Location
}
