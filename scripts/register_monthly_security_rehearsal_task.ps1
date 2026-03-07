param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_Monthly_Security_Rehearsal",
    [int]$DayOfMonth = 1,
    [string]$StartTime = "03:30"
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\run_monthly_security_rehearsal.ps1"
if (-not (Test-Path $runner)) {
    throw "runner not found: $runner"
}

$day = [Math]::Min(31, [Math]::Max(1, [int]$DayOfMonth))
$time = [string]$StartTime
if ($time -notmatch '^\d{2}:\d{2}$') {
    throw "StartTime must be HH:mm format, example 03:30"
}

$userId = "$env:USERDOMAIN\$env:USERNAME"
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -RepoRoot `"$RepoRoot`""
$taskCommand = "powershell.exe"

$createArgs = @(
    "/Create",
    "/F",
    "/SC", "MONTHLY",
    "/D", "$day",
    "/ST", "$time",
    "/TN", "$TaskName",
    "/TR", "`"$taskCommand $arg`"",
    "/RU", $userId
)

$null = & schtasks.exe @createArgs
if ($LASTEXITCODE -ne 0) {
    throw "failed to register task by schtasks.exe"
}

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$marker = Join-Path $logsDir "monthly_security_rehearsal_task_registration.json"
$payload = [ordered]@{
    registered_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    task_name = $TaskName
    user_id = $userId
    schedule = [ordered]@{
        type = "MONTHLY"
        day_of_month = $day
        start_time = $time
    }
    runner = $runner
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $marker -Encoding UTF8

Write-Output "registered task: $TaskName monthly day=$day time=$time"
Write-Output "marker: $marker"
