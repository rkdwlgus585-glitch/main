param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$logFile = Join-Path $logsDir "secure_api_stack.log"
$mutexName = "Local\SeoulMNA_SecureApiStack"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Resolve-Python() {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return "py -3" }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return "python" }
    return ""
}

function Is-Running([string]$scriptName) {
    $items = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^python(?:\.exe)?$|^py(?:\.exe)?$" -and $_.CommandLine -match [regex]::Escape($scriptName)
    }
    return (($items | Measure-Object).Count -ge 1)
}

function Start-Api([string]$scriptName, [string]$jobName) {
    if (Is-Running $scriptName) {
        Write-Log ("KEEP {0}: already running" -f $jobName)
        return
    }
    $pyCmd = Resolve-Python
    if (-not $pyCmd) {
        Write-Log ("FAIL {0}: python runtime not found" -f $jobName)
        return
    }
    $psArg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"Set-Location -LiteralPath '$RepoRoot'; & $pyCmd '$scriptName'`""
    Start-Process -FilePath "powershell.exe" -ArgumentList $psArg -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
    Write-Log ("START {0}" -f $jobName)
}

$mutex = $null
$hasHandle = $false
try {
    $mutex = New-Object System.Threading.Mutex($false, $mutexName)
    try {
        $hasHandle = $mutex.WaitOne(0, $false)
    } catch [System.Threading.AbandonedMutexException] {
        $hasHandle = $true
    }
    if (-not $hasHandle) {
        Write-Log "SKIP secure_api_stack ensure: mutex locked"
        exit 0
    }
    Write-Log "RUN secure_api_stack ensure"
    Start-Api -scriptName "yangdo_consult_api.py" -jobName "consult_api"
    Start-Api -scriptName "yangdo_blackbox_api.py" -jobName "blackbox_api"
    Write-Log "DONE secure_api_stack ensure"
    exit 0
}
catch {
    Write-Log ("FAIL secure_api_stack ensure: {0}" -f $_.Exception.Message)
    exit 1
}
finally {
    if ($hasHandle -and $mutex) {
        try { $mutex.ReleaseMutex() | Out-Null } catch {}
    }
    if ($mutex) {
        try { $mutex.Dispose() } catch {}
    }
}
