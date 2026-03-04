# Runs tomorrow follow-up operations once at next eligible logon,
# then removes scheduled-task traces.
param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_Tomorrow_Followup_Once",
    [int]$StartupDelaySec = 90
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

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logsDir "tomorrow_followup_once.log"
$reportFile = Join-Path $logsDir ("tomorrow_followup_execution_{0}.json" -f $timestamp)
$registrationMarker = Join-Path $logsDir "tomorrow_followup_registration.json"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Resolve-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, "-3")
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }
    return @()
}

function Invoke-Step([hashtable]$step, [string[]]$pythonPrefix) {
    $result = [ordered]@{
        name = $step.name
        started_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        command = ""
        rc = 1
        ok = $false
    }
    $scriptPath = Join-Path $RepoRoot $step.script
    if (-not (Test-Path $scriptPath)) {
        $result.command = "missing script: $($step.script)"
        $result.rc = 1
        $result.ok = $false
        return $result
    }

    $args = @($scriptPath) + $step.args
    if ($pythonPrefix.Count -gt 0) {
        $cmdDisplay = ($pythonPrefix + $args) -join " "
        $result.command = $cmdDisplay
        Write-Log ("RUN {0} -> {1}" -f $step.name, $cmdDisplay)
        if ($pythonPrefix.Count -eq 1) {
            & $pythonPrefix[0] @args *>> $logFile
        } else {
            $prefixRest = @()
            if ($pythonPrefix.Count -gt 1) {
                $prefixRest = @($pythonPrefix[1..($pythonPrefix.Count - 1)])
            }
            & $pythonPrefix[0] @($prefixRest + $args) *>> $logFile
        }
    } else {
        $result.command = "python-not-found"
        Write-Log ("RUN {0} -> python not found" -f $step.name)
        $result.rc = 1
        $result.ok = $false
        return $result
    }

    $rc = 0
    if ($LASTEXITCODE -ne $null) {
        $rc = [int]$LASTEXITCODE
    }
    $result.rc = $rc
    $result.ok = ($rc -eq 0)
    Write-Log ("END {0} rc={1}" -f $step.name, $rc)
    return $result
}

function Cleanup-ReservationTraces([string]$taskName, [string]$markerPath) {
    try {
        if ($taskName) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false | Out-Null
            Write-Log ("CLEANUP unregistered task: {0}" -f $taskName)
        }
    } catch {
        Write-Log ("CLEANUP unregister skipped: {0}" -f $_.Exception.Message)
    }
    try {
        if ($markerPath -and (Test-Path $markerPath)) {
            Remove-Item -Path $markerPath -Force
            Write-Log ("CLEANUP removed marker: {0}" -f $markerPath)
        }
    } catch {
        Write-Log ("CLEANUP marker remove skipped: {0}" -f $_.Exception.Message)
    }
}

Write-Log "START tomorrow followup once"

if ($StartupDelaySec -gt 0) {
    Write-Log ("startup delay begin: {0}s" -f [int]$StartupDelaySec)
    Start-Sleep -Seconds ([int]$StartupDelaySec)
    Write-Log "startup delay end"
}

$pythonPrefix = Resolve-PythonCommand
if ($pythonPrefix.Count -eq 0) {
    Write-Log "ERROR python command not found"
    Cleanup-ReservationTraces -taskName $TaskName -markerPath $registrationMarker
    exit 1
}

$steps = @(
    @{
        name = "prepare_banner_snippet"
        script = "scripts\prepare_co_global_banner_snippet.py"
        args = @("--snippet-out", "logs/co_global_banner_snippet.html", "--guide-out", "logs/co_global_banner_apply_guide.md")
    },
    @{
        name = "apply_banner_admin"
        script = "scripts\apply_co_global_banner_admin.py"
        args = @("--snippet-file", "logs/co_global_banner_snippet.html", "--report", "logs/co_global_banner_apply_latest.json", "--force")
    },
    @{
        name = "generate_internal_sitemap"
        script = "scripts\generate_internal_sitemap.py"
        args = @("--base-url", "https://seoulmna.co.kr", "--out", "output/sitemap.xml", "--report", "logs/internal_sitemap_report_latest.json", "--max-board-pages", "140", "--max-static-pages", "140")
    }
)

$results = @()
foreach ($step in $steps) {
    $stepResult = Invoke-Step -step $step -pythonPrefix $pythonPrefix
    $results += [pscustomobject]$stepResult
}

$failedCount = ($results | Where-Object { -not $_.ok } | Measure-Object).Count
$overallOk = ($failedCount -eq 0)
$summary = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    task_name = $TaskName
    startup_delay_sec = [int]$StartupDelaySec
    overall_ok = $overallOk
    failed_count = [int]$failedCount
    steps = $results
    cleanup = [ordered]@{
        unregister_task_attempted = $true
        marker_remove_attempted = $true
    }
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $reportFile -Encoding UTF8
Write-Log ("REPORT {0}" -f $reportFile)

Cleanup-ReservationTraces -taskName $TaskName -markerPath $registrationMarker
Write-Log ("END tomorrow followup once ok={0}" -f $overallOk)

if ($overallOk) {
    exit 0
}
exit 1
