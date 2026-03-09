# Registers hidden Windows Task Scheduler job:
# At user logon -> run unified startup runner (all major jobs together).
param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_All_Startup",
    [switch]$DisableLegacyTasks
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\run_startup_all.ps1"
if (-not (Test-Path $runner)) {
    throw "runner not found: $runner"
}
$hiddenLauncher = Join-Path $RepoRoot "scripts\run_hidden_ps.vbs"
if (-not (Test-Path $hiddenLauncher)) {
    throw "hidden launcher not found: $hiddenLauncher"
}

$userId = "$env:USERDOMAIN\$env:USERNAME"
$wscriptExe = Join-Path $env:SystemRoot "System32\wscript.exe"
if (-not (Test-Path $wscriptExe)) {
    $wscriptExe = "wscript.exe"
}
$arg = "`"$hiddenLauncher`" `"$runner`" -RepoRoot `"$RepoRoot`""

$action = New-ScheduledTaskAction -Execute $wscriptExe -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -Hidden `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Run SeoulMNA secure API startup helper at logon. co.kr watchdogs are managed by dedicated split tasks." `
    -Force | Out-Null

if ($DisableLegacyTasks) {
    $legacy = @(
        "SeoulMNA_Ops_Watchdog"
    )
    foreach ($name in $legacy) {
        try {
            Disable-ScheduledTask -TaskName $name | Out-Null
            Write-Output "disabled legacy task: $name"
        } catch {
        }
    }
}

Write-Output "registered task: $TaskName"
