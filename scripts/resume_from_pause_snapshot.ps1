param(
  [string]$SnapshotPath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($SnapshotPath)) {
  $SnapshotPath = Join-Path $repoRoot "logs\pause_snapshot_latest.json"
}
Set-Location $repoRoot

if (!(Test-Path $SnapshotPath)) {
  throw "Snapshot not found: $SnapshotPath"
}

$snap = Get-Content -Raw -Path $SnapshotPath | ConvertFrom-Json

foreach ($task in $snap.tasks) {
  if (-not $task.Exists) { continue }
  if ($task.Enabled -eq $true) {
    Enable-ScheduledTask -TaskName $task.TaskName -ErrorAction SilentlyContinue | Out-Null
  } else {
    Disable-ScheduledTask -TaskName $task.TaskName -ErrorAction SilentlyContinue | Out-Null
  }
}

# Restore GitHub repository variables captured in snapshot.
foreach ($v in $snap.githubVariables) {
  if ([string]::IsNullOrWhiteSpace($v.name)) { continue }
  if ($null -eq $v.value) { continue }
  gh variable set $v.name --body "$($v.value)" | Out-Null
}

# Restart core watchdog tasks immediately if they were enabled before pause.
$splitWatchdogTasks = @(
  "SeoulMNA_CoKr_Listing_Watchdog",
  "SeoulMNA_CoKr_MonthlyRecommend_Watchdog",
  "SeoulMNA_CoKr_MonthlyReport_Watchdog",
  "SeoulMNA_CoKr_AdminMemo_Watchdog",
  "SeoulMNA_CoKr_SiteHealth_Watchdog",
  "SeoulMNA_Permit_Data_Watchdog"
)
$legacyOpsTask = $snap.tasks | Where-Object { $_.TaskName -eq "SeoulMNA_Ops_Watchdog" } | Select-Object -First 1
$legacyOpsWasEnabled = [bool]($legacyOpsTask -and $legacyOpsTask.Exists -and $legacyOpsTask.Enabled -eq $true)
$restartCandidates = @("SeoulMNA_MnakrScheduler_Watchdog") + $splitWatchdogTasks
foreach ($name in $restartCandidates) {
  $task = $snap.tasks | Where-Object { $_.TaskName -eq $name } | Select-Object -First 1
  $shouldStart = [bool]($task -and $task.Exists -and $task.Enabled -eq $true)
  if (-not $shouldStart -and $legacyOpsWasEnabled -and ($name -in $splitWatchdogTasks)) {
    $liveTask = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    $shouldStart = [bool]($liveTask -and $liveTask.Settings.Enabled)
  }
  if ($shouldStart) {
    Start-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  }
}

$logDir = Join-Path $repoRoot "logs"
if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$statusPath = Join-Path $logDir ("resume_from_pause_{0}.json" -f $stamp)

$summaryTaskNames = @($snap.tasks | ForEach-Object { $_.TaskName })
foreach ($name in ($splitWatchdogTasks + @("SeoulMNA_MnakrScheduler_Watchdog"))) {
  if ($summaryTaskNames -notcontains $name) {
    $summaryTaskNames += $name
  }
}

$finalTasks = $summaryTaskNames | ForEach-Object {
  $taskName = [string]$_
  $t = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if ($null -eq $t) {
    [pscustomobject]@{
      TaskName = $taskName
      Exists = $false
      Enabled = $null
      State = $null
    }
  } else {
    [pscustomobject]@{
      TaskName = $taskName
      Exists = $true
      Enabled = [bool]$t.Settings.Enabled
      State = [string]$t.State
    }
  }
}

[pscustomobject]@{
  restoredAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
  snapshotPath = $SnapshotPath
  tasks = $finalTasks
} | ConvertTo-Json -Depth 6 | Set-Content -Path $statusPath -Encoding UTF8

Write-Output "Restored from snapshot. Status log: $statusPath"
