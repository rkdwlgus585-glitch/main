param(
    [string]$TaskName = "SeoulMNA_Playwright_Residue_Cleanup",
    [int]$EveryMinutes = 10,
    [int]$NodeMaxAgeMinutes = 30,
    [int]$ChromeMaxAgeMinutes = 30,
    [int]$TempRetentionHours = 6
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$cleanupScript = Join-Path $repoRoot "scripts\cleanup_playwright_residue.ps1"
 $hiddenRunner = Join-Path $repoRoot "scripts\run_hidden_ps.vbs"
if (-not (Test-Path -LiteralPath $cleanupScript)) {
    throw "cleanup script not found: $cleanupScript"
}
if (-not (Test-Path -LiteralPath $hiddenRunner)) {
    throw "hidden runner not found: $hiddenRunner"
}

$arg = @(
    ('"{0}"' -f $hiddenRunner),
    ('"{0}"' -f $cleanupScript),
    "-Quiet",
    "-NodeMaxAgeMinutes", [string][Math]::Max(5, $NodeMaxAgeMinutes),
    "-ChromeMaxAgeMinutes", [string][Math]::Max(5, $ChromeMaxAgeMinutes),
    "-TempRetentionHours", [string][Math]::Max(1, $TempRetentionHours),
    "-ReportPath", ('"{0}"' -f (Join-Path $repoRoot "logs\playwright_residue_cleanup_latest.json"))
) -join " "

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $arg

$startAt = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At $startAt `
    -RepetitionInterval (New-TimeSpan -Minutes ([Math]::Max(5, $EveryMinutes))) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -Hidden `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Auto-clean stale Playwright/node/headless-chrome residue" `
    -Force | Out-Null

Write-Output ("[task] {0}" -f $TaskName)
Write-Output ("[interval_minutes] {0}" -f ([Math]::Max(5, $EveryMinutes)))
Write-Output ("[cleanup_script] {0}" -f $cleanupScript)
