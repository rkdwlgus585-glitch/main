# Registers one-shot followup task:
# - Trigger: next logon from tomorrow date onward.
# - Runner self-cleans task + registration marker after execution.
param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_Tomorrow_Followup_Once",
    [int]$StartupDelaySec = 90
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\run_tomorrow_followup_once.ps1"
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

$arg = "`"$hiddenLauncher`" `"$runner`" -RepoRoot `"$RepoRoot`" -TaskName `"$TaskName`" -StartupDelaySec $StartupDelaySec"
$action = New-ScheduledTaskAction -Execute $wscriptExe -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId

# Do not run on today's logon. Start from tomorrow 00:00 local time.
$startBoundary = (Get-Date).Date.AddDays(1).ToString("yyyy-MM-dd'T'00:00:00")
$trigger.StartBoundary = $startBoundary

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
    -Description "Run SeoulMNA tomorrow follow-up once at next logon, then self-clean." `
    -Force | Out-Null

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$marker = Join-Path $logsDir "tomorrow_followup_registration.json"
$payload = [ordered]@{
    registered_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    task_name = $TaskName
    user_id = $userId
    start_boundary = $startBoundary
    startup_delay_sec = [int]$StartupDelaySec
    runner = $runner
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $marker -Encoding UTF8

Write-Output "registered task: $TaskName"
Write-Output "start boundary: $startBoundary"
Write-Output "marker: $marker"
