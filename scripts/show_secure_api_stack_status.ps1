param(
    [string]$RepoRoot = "",
    [string]$JsonPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
if (-not $JsonPath) {
    $JsonPath = Join-Path $RepoRoot "logs\secure_api_status_latest.json"
}

$apiConfigs = @(
    [pscustomobject]@{
        Name = "consult"
        ScriptName = "yangdo_consult_api.py"
        Port = 8788
        HealthUrl = "http://127.0.0.1:8788/health"
    },
    [pscustomobject]@{
        Name = "blackbox"
        ScriptName = "yangdo_blackbox_api.py"
        Port = 8790
        HealthUrl = "http://127.0.0.1:8790/health"
    }
)

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

function Get-WorkerRows([string]$scriptName) {
    return @(Get-PythonRows $scriptName | Where-Object { $_.Name -match '^python(?:\.exe)?$' })
}

function Get-ShimRows([string]$scriptName) {
    return @(Get-PythonRows $scriptName | Where-Object { $_.Name -match '^py(?:\.exe)?$' })
}

function Get-LauncherRows([string]$scriptName) {
    $pattern = New-ScriptRegex $scriptName
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.Name -match '^powershell(?:\.exe)?$|^pwsh(?:\.exe)?$' -and
        $_.ProcessId -ne $PID -and
        $_.CommandLine -match $pattern
    } | Sort-Object ProcessId -Unique)
}

function Invoke-Health([string]$url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 8 -UseBasicParsing
        return [pscustomobject]@{
            ok = $true
            status = [int]$resp.StatusCode
        }
    } catch {
        $status = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        return [pscustomobject]@{
            ok = $false
            status = $status
            error = $_.Exception.Message
        }
    }
}

$rows = foreach ($cfg in $apiConfigs) {
    $listener = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $cfg.Port } | Select-Object -First 1
    $workers = @(Get-WorkerRows $cfg.ScriptName)
    $shims = @(Get-ShimRows $cfg.ScriptName)
    $launchers = @(Get-LauncherRows $cfg.ScriptName)
    $health = Invoke-Health $cfg.HealthUrl
    $listenerPid = if ($listener) { $listener.OwningProcess } elseif ($workers.Count -ge 1) { $workers[0].ProcessId } else { $null }
    $status = if (-not $health.ok -or $workers.Count -lt 1) {
        "DOWN"
    } elseif ($workers.Count -gt 1 -or $launchers.Count -gt 1) {
        "DUPLICATE"
    } else {
        "OK"
    }
    [pscustomobject]@{
        Api = $cfg.Name
        Port = $cfg.Port
        Listening = [bool]$listener
        ListenerPid = $listenerPid
        WorkerCount = $workers.Count
        ShimCount = $shims.Count
        LauncherCount = $launchers.Count
        Status = $status
        HealthOk = $health.ok
        HealthStatus = $health.status
        HealthError = $health.error
    }
}

Write-Host ("CheckedAt: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz"))
Write-Host ""
$rows | Format-Table -AutoSize
Write-Host ""

$snapshot = [pscustomobject]@{
    checked_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    rows = $rows
}
$snapshot | ConvertTo-Json -Depth 6 | Set-Content -Path $JsonPath -Encoding UTF8

foreach ($cfg in $apiConfigs) {
    Write-Host ("[{0}] Python processes" -f $cfg.Name)
    $pyRows = Get-PythonRows $cfg.ScriptName | Select-Object ProcessId, ParentProcessId, Name, CommandLine
    if ($pyRows) {
        $pyRows | Format-Table -AutoSize
    } else {
        Write-Host "None"
    }
    Write-Host ""
    Write-Host ("[{0}] Launcher processes" -f $cfg.Name)
    $launcherRows = Get-LauncherRows $cfg.ScriptName | Select-Object ProcessId, ParentProcessId, Name, CommandLine
    if ($launcherRows) {
        $launcherRows | Format-Table -AutoSize
    } else {
        Write-Host "None"
    }
    Write-Host ""
}
