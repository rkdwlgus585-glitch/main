# Apply or preview SeoulMNA execution profile.
# Default mode is PLAN-ONLY (no changes). Use -Apply to execute changes.
param(
    [string]$RepoRoot = "",
    [switch]$Apply,
    [switch]$EnableBlogStartupOnce,
    [switch]$EnableTistoryDailyOnce,
    [switch]$SkipStartupArtifactCleanup
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

function Write-Plan([string]$message) {
    Write-Output ("[PLAN] {0}" -f $message)
}

function Write-Apply([string]$message) {
    Write-Output ("[APPLY] {0}" -f $message)
}

function Get-TaskState([string]$name) {
    try {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
        return [string]$task.State
    } catch {
        return "Missing"
    }
}

function Get-UserStartupFolder {
    return [Environment]::GetFolderPath("Startup")
}

function Get-LegacyStartupArtifacts {
    $startupDir = Get-UserStartupFolder
    if (-not (Test-Path $startupDir)) {
        return @()
    }
    return @(Get-ChildItem -Force $startupDir | Where-Object {
        $_.Name -match '\.bak_\d{8}' `
        -or $_.Name -match '\.disabled_\d{8}' `
        -or $_.Name -match '^MNAKR_AutoScheduler\.cmd(\..+)?$' `
        -or $_.Name -match '^SeoulMNA_.*\.vbs(\..+)?$'
    })
}

function Cleanup-LegacyStartupArtifacts {
    if ($SkipStartupArtifactCleanup) {
        if ($Apply) {
            Write-Apply "Skip startup artifact cleanup by flag."
        } else {
            Write-Plan "Skip startup artifact cleanup by flag."
        }
        return
    }

    $artifacts = Get-LegacyStartupArtifacts
    if (($artifacts | Measure-Object).Count -eq 0) {
        if ($Apply) {
            Write-Apply "No legacy startup artifacts found."
        } else {
            Write-Plan "No legacy startup artifacts found."
        }
        return
    }

    $startupDir = Get-UserStartupFolder
    if (-not $Apply) {
        Write-Plan ("Startup cleanup target folder: {0}" -f $startupDir)
        foreach ($item in $artifacts) {
            Write-Plan ("Archive startup artifact: {0}" -f $item.Name)
        }
        return
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $archiveRoot = Join-Path $RepoRoot "logs\startup_artifacts_archive\$stamp"
    New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
    foreach ($item in $artifacts) {
        $dest = Join-Path $archiveRoot $item.Name
        Move-Item -LiteralPath $item.FullName -Destination $dest -Force
        Write-Apply ("Archived startup artifact: {0}" -f $item.Name)
    }
}

function Set-TaskEnabledState([string]$name, [bool]$enableFlag) {
    if (-not $Apply) {
        if ($enableFlag) {
            Write-Plan ("Enable task: {0}" -f $name)
        } else {
            Write-Plan ("Disable task: {0}" -f $name)
        }
        return
    }
    try {
        if ($enableFlag) {
            Enable-ScheduledTask -TaskName $name | Out-Null
            Write-Apply ("Enabled: {0}" -f $name)
        } else {
            Disable-ScheduledTask -TaskName $name | Out-Null
            Write-Apply ("Disabled: {0}" -f $name)
        }
    } catch {
        Write-Apply ("Skipped {0}: {1}" -f $name, $_.Exception.Message)
    }
}

function Invoke-RepoScript([string]$relativePath, [string[]]$arguments) {
    $scriptPath = Join-Path $RepoRoot $relativePath
    if (-not (Test-Path $scriptPath)) {
        throw "script missing: $scriptPath"
    }
    $argLine = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $scriptPath) + $arguments
    if (-not $Apply) {
        Write-Plan ("Run script: powershell.exe {0}" -f ($argLine -join " "))
        return
    }
    & powershell.exe @argLine
}

Write-Output "=== SeoulMNA Execution Profile ==="
Write-Output ("repo={0}" -f $RepoRoot)
Write-Output ("mode={0}" -f ($(if ($Apply) { "APPLY" } else { "PLAN_ONLY" })))
Write-Output ("blog_startup_once={0}" -f ($(if ($EnableBlogStartupOnce) { "ENABLED" } else { "DISABLED" })))
Write-Output ("tistory_daily_once={0}" -f ($(if ($EnableTistoryDailyOnce) { "ENABLED" } else { "DISABLED" })))
Write-Output ("startup_artifact_cleanup={0}" -f ($(if ($SkipStartupArtifactCleanup) { "SKIP" } else { "ENABLED" })))
Write-Output ""
$cokrTaskNames = @(
    "SeoulMNA_CoKr_Listing_Watchdog",
    "SeoulMNA_CoKr_Notice_Watchdog",
    "SeoulMNA_CoKr_AdminMemo_Watchdog",
    "SeoulMNA_CoKr_SiteHealth_Watchdog",
    "SeoulMNA_Permit_Data_Watchdog"
)


# 0) Cleanup legacy startup artifacts that can trigger popup noise at logon.
Cleanup-LegacyStartupArtifacts

# 1) Keep split mode: disable old unified startup task.
Set-TaskEnabledState -name "SeoulMNA_All_Startup" -enableFlag:$false

# 2) Register split co.kr watchdog tasks with recommended startup delays.
Invoke-RepoScript -relativePath "scripts\register_cokr_watchdog_tasks.ps1" -arguments @("-RepoRoot", $RepoRoot, "-BaseStartupDelaySec", "0")
Invoke-RepoScript -relativePath "scripts\register_mnakr_scheduler_watchdog_task.ps1" -arguments @("-RepoRoot", $RepoRoot, "-StartupDelaySec", "60")

foreach ($taskName in $cokrTaskNames) {
    Set-TaskEnabledState -name $taskName -enableFlag:$true
}
Set-TaskEnabledState -name "SeoulMNA_MnakrScheduler_Watchdog" -enableFlag:$true

# 3) Optional startup-once tasks.
Invoke-RepoScript -relativePath "scripts\register_blog_startup_once_task.ps1" -arguments @("-RepoRoot", $RepoRoot, "-StartupDelaySec", "180")
Invoke-RepoScript -relativePath "scripts\register_tistory_daily_startup_task.ps1" -arguments @("-RepoRoot", $RepoRoot, "-StartupDelaySec", "360")

Set-TaskEnabledState -name "SeoulMNA_Blog_StartupOnce" -enableFlag:$EnableBlogStartupOnce
Set-TaskEnabledState -name "SeoulMNA_Tistory_DailyOnce" -enableFlag:$EnableTistoryDailyOnce

$summaryTaskNames = $cokrTaskNames + @(
    "SeoulMNA_MnakrScheduler_Watchdog",
    "SeoulMNA_Blog_StartupOnce",
    "SeoulMNA_Tistory_DailyOnce",
    "SeoulMNA_All_Startup"
)

Write-Output ""
Write-Output "=== Task States (after profile plan/apply) ==="
foreach ($taskName in $summaryTaskNames) {
    $state = Get-TaskState -name $taskName
    Write-Output ("- {0}: {1}" -f $taskName, $state)
}
