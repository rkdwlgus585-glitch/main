param(
  [string]$SnapshotPath = "C:\Users\rkdwl\Desktop\auto\logs\pause_snapshot_latest.json"
)

$ErrorActionPreference = "SilentlyContinue"
Set-Location "C:\Users\rkdwl\Desktop\auto"

$taskNames = @(
  "Auto-Quality-Daily",
  "G2B_Auto",
  "SeoulMNA_All_Startup",
  "SeoulMNA_Blog_StartupOnce",
  "SeoulMNA_MnakrScheduler_Watchdog",
  "SeoulMNA_Ops_Watchdog",
  "SeoulMNA_Tistory_DailyOnce",
  "SeoulMNA_Resume_FromPause_Afternoon"
)

Write-Host "=== SeoulMNA Auto Status ==="
Write-Host ("CheckedAt: {0}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz"))
Write-Host ""

Write-Host "[1] Local Scheduled Tasks"
$rows = foreach ($name in $taskNames) {
  $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if ($null -eq $t) {
    [pscustomobject]@{
      TaskName = $name
      Enabled = $null
      State = "NotFound"
      NextRun = $null
    }
    continue
  }
  $info = Get-ScheduledTaskInfo -TaskName $name -ErrorAction SilentlyContinue
  [pscustomobject]@{
    TaskName = $name
    Enabled = [bool]$t.Settings.Enabled
    State = [string]$t.State
    NextRun = if ($info -and $info.NextRunTime -and $info.NextRunTime.Year -gt 2000) { $info.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "-" }
  }
}
$rows | Format-Table -AutoSize

Write-Host ""
Write-Host "[2] Local Running Automation Processes"
$procs = Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and (($_.CommandLine -like "*mnakr.py --scheduler*") -or ($_.CommandLine -like "*mnakr_scheduler_watchdog*") -or ($_.CommandLine -like "*seoulmna_ops_watchdog*") -or ($_.CommandLine -like "*run_local_auto_state_bridge*") -or ($_.CommandLine -like "* all.py*")) -and ($_.CommandLine -notlike "*Get-CimInstance Win32_Process*")
} | Select-Object ProcessId, Name, CommandLine
if ($procs) {
  $procs | Format-Table -AutoSize
} else {
  Write-Host "None"
}

Write-Host ""
Write-Host "[3] GitHub Auto Variables"
try {
  $rawVars = gh variable list --json name,value 2>$null
  $allVars = @()
  if (-not [string]::IsNullOrWhiteSpace($rawVars)) {
    $allVars = $rawVars | ConvertFrom-Json
  }
  $vars = $allVars | Where-Object { $_.name -in @("ENABLE_CALCULATOR_INTERNAL_AUTODRIVE_SCHEDULE","ENABLE_REMOTE_FUZZ_SCHEDULE","CALCULATOR_AUTODRIVE_DATE_KST") }
  if ($vars) {
    $vars | Sort-Object name | Format-Table -AutoSize
  } else {
    Write-Host "No matching variables."
  }
} catch {
  Write-Host "gh variable list failed."
}

Write-Host ""
Write-Host "[4] Resume Baseline (from snapshot)"
if (Test-Path $SnapshotPath) {
  try {
    $snap = Get-Content -Raw $SnapshotPath | ConvertFrom-Json
    $snap.tasks | Select-Object TaskName, Enabled, State | Sort-Object TaskName | Format-Table -AutoSize
  } catch {
    Write-Host "Snapshot parse failed: $SnapshotPath"
  }
} else {
  Write-Host "Snapshot not found: $SnapshotPath"
}
