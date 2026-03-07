param(
    [ValidateSet("consult", "blackbox", "all")]
    [string]$Target = "all",
    [string]$RepoRoot = "",
    [int]$TimeoutSec = 25
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
$logFile = Join-Path $logsDir "secure_api_restart.log"
$runner = Join-Path $RepoRoot "scripts\run_secure_api_stack.ps1"
if (-not (Test-Path $runner)) {
    throw "runner not found: $runner"
}

$apiConfigs = @{
    consult = @{
        ScriptName = "yangdo_consult_api.py"
        Port = 8788
        HealthUrl = "http://127.0.0.1:8788/health"
        JobName = "consult_api"
    }
    blackbox = @{
        ScriptName = "yangdo_blackbox_api.py"
        Port = 8790
        HealthUrl = "http://127.0.0.1:8790/health"
        JobName = "blackbox_api"
    }
}

if ($Target -eq "all") {
    $targets = @("consult", "blackbox")
} else {
    $targets = @($Target)
}

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function New-ScriptRegex([string]$scriptName) {
    return '(?i)(?:^|[\s''"/\\])' + [regex]::Escape($scriptName) + '(?:$|[\s''"/\\])'
}

function Get-PythonRows([string]$scriptName) {
    $pattern = New-ScriptRegex $scriptName
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.Name -match '^python(?:\.exe)?$|^py(?:\.exe)?$' -and
        $_.CommandLine -match $pattern
    } | Sort-Object ProcessId -Unique)
}

function Get-LauncherRows([string]$scriptName) {
    $pattern = New-ScriptRegex $scriptName
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.ProcessId -ne $PID -and
        $_.Name -match '^powershell(?:\.exe)?$|^pwsh(?:\.exe)?$' -and
        $_.CommandLine -match $pattern
    } | Sort-Object ProcessId -Unique)
}

function Stop-Rows([object[]]$rows, [string]$kind) {
    foreach ($row in $rows) {
        Write-Log ("STOP {0}: pid={1} parent={2}" -f $kind, $row.ProcessId, $row.ParentProcessId)
        try {
            Stop-Process -Id $row.ProcessId -Force -ErrorAction Stop
        } catch {
            Write-Log ("WARN {0}: stop failed for pid={1}: {2}" -f $kind, $row.ProcessId, $_.Exception.Message)
        }
    }
}

function Test-PortListening([int]$port) {
    $rows = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $port }
    return (($rows | Measure-Object).Count -ge 1)
}

function Wait-PortState([int]$port, [bool]$shouldListen, [int]$timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    do {
        $isListening = Test-PortListening $port
        if ($isListening -eq $shouldListen) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Invoke-Health([string]$url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 8 -UseBasicParsing
        return [pscustomobject]@{
            ok = $true
            status_code = [int]$resp.StatusCode
        }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        return [pscustomobject]@{
            ok = $false
            status_code = $statusCode
            error = $_.Exception.Message
        }
    }
}

foreach ($targetName in $targets) {
    $cfg = $apiConfigs[$targetName]
    Write-Log ("RESTART {0}: begin" -f $cfg.JobName)
    $launchers = Get-LauncherRows $cfg.ScriptName
    $pythons = Get-PythonRows $cfg.ScriptName
    Stop-Rows -rows $launchers -kind ("launcher:{0}" -f $cfg.JobName)
    Stop-Rows -rows $pythons -kind ("python:{0}" -f $cfg.JobName)
    if (-not (Wait-PortState -port $cfg.Port -shouldListen $false -timeoutSec $TimeoutSec)) {
        throw ("port {0} did not stop for {1}" -f $cfg.Port, $cfg.JobName)
    }
    Write-Log ("RESTART {0}: stopped" -f $cfg.JobName)
}

Write-Log ("ENSURE stack via {0}" -f $runner)
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) {
    throw ("secure api runner failed with exit code {0}" -f $LASTEXITCODE)
}

$results = foreach ($targetName in $targets) {
    $cfg = $apiConfigs[$targetName]
    if (-not (Wait-PortState -port $cfg.Port -shouldListen $true -timeoutSec $TimeoutSec)) {
        throw ("port {0} did not start for {1}" -f $cfg.Port, $cfg.JobName)
    }
    $listener = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $cfg.Port } | Select-Object -First 1
    $health = Invoke-Health $cfg.HealthUrl
    Write-Log ("RESTART {0}: pid={1} health_ok={2} health_status={3}" -f $cfg.JobName, $listener.OwningProcess, $health.ok, $health.status_code)
    [pscustomobject]@{
        target = $targetName
        script = $cfg.ScriptName
        port = $cfg.Port
        pid = $listener.OwningProcess
        health_ok = $health.ok
        health_status = $health.status_code
        health_error = $health.error
    }
}

$results | Format-Table -AutoSize
