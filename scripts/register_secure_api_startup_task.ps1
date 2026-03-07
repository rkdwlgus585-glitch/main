param(
    [string]$RepoRoot = "",
    [string]$TaskName = "SeoulMNA_SecureAPI_Startup"
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\run_secure_api_stack.ps1"
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
    -Description "Ensure SeoulMNA secure API stack (consult + blackbox) is running at user logon." `
    -Force | Out-Null

Write-Output "registered task: $TaskName"
