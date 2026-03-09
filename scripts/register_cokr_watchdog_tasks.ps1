param(
    [string]$RepoRoot = "",
    [int]$BaseStartupDelaySec = 0
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$runner = Join-Path $RepoRoot "scripts\seoulmna_watchdog_worker.ps1"
$hiddenLauncher = Join-Path $RepoRoot "scripts\run_hidden_ps.vbs"
if (-not (Test-Path $runner)) {
    throw "runner not found: $runner"
}
if (-not (Test-Path $hiddenLauncher)) {
    throw "hidden launcher not found: $hiddenLauncher"
}

$userId = "$env:USERDOMAIN\$env:USERNAME"
$wscriptExe = Join-Path $env:SystemRoot "System32\wscript.exe"
if (-not (Test-Path $wscriptExe)) {
    $wscriptExe = "wscript.exe"
}

$profiles = @(
    @{ Profile = "listing"; TaskName = "SeoulMNA_CoKr_Listing_Watchdog"; Delay = 0; Description = "Run seoulmna.co.kr listing sync/upload watchdog at logon (hidden)." },
    @{ Profile = "notice"; TaskName = "SeoulMNA_CoKr_Notice_Watchdog"; Delay = 20; Description = "Run seoulmna.co.kr notice publish watchdog at logon (hidden)." },
    @{ Profile = "admin_memo"; TaskName = "SeoulMNA_CoKr_AdminMemo_Watchdog"; Delay = 40; Description = "Run seoulmna.co.kr admin memo sync watchdog at logon (hidden)." },
    @{ Profile = "site_health"; TaskName = "SeoulMNA_CoKr_SiteHealth_Watchdog"; Delay = 60; Description = "Run seoulmna.co.kr site health watchdog at logon (hidden)." },
    @{ Profile = "permit"; TaskName = "SeoulMNA_Permit_Data_Watchdog"; Delay = 80; Description = "Run permit data watchdog at logon (hidden)." }
)

foreach ($cfg in $profiles) {
    $delaySec = [int]$BaseStartupDelaySec + [int]$cfg.Delay
    $arg = "`"$hiddenLauncher`" `"$runner`" -RepoRoot `"$RepoRoot`" -Profile `"$($cfg.Profile)`" -StartupDelaySec $delaySec"

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
        -TaskName $cfg.TaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description $cfg.Description `
        -Force | Out-Null

    Write-Output ("registered task: {0} ({1})" -f $cfg.TaskName, $cfg.Profile)
}

$legacyTask = Get-ScheduledTask -TaskName "SeoulMNA_Ops_Watchdog" -ErrorAction SilentlyContinue
if ($legacyTask) {
    Unregister-ScheduledTask -TaskName "SeoulMNA_Ops_Watchdog" -Confirm:$false
    Write-Output "unregistered legacy task: SeoulMNA_Ops_Watchdog"
}
