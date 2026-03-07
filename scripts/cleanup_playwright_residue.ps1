param(
    [int]$NodeMaxAgeMinutes = 30,
    [int]$ChromeMaxAgeMinutes = 30,
    [int]$TempRetentionHours = 6,
    [string]$ReportPath = "logs/playwright_residue_cleanup_latest.json",
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-Info([string]$msg) {
    if (-not $Quiet) {
        Write-Output $msg
    }
}

function To-DateTime([string]$wmiDate) {
    if (-not $wmiDate) { return $null }
    try { return [System.Management.ManagementDateTimeConverter]::ToDateTime($wmiDate) } catch { return $null }
}

function Is-Alive([int]$procId) {
    if ($procId -le 0) { return $false }
    return [bool](Get-Process -Id $procId -ErrorAction SilentlyContinue)
}

function Kill-Tree([int]$procId, [string]$reason, [hashtable]$summary) {
    if ($procId -le 0) { return }
    if (-not (Is-Alive -procId $procId)) { return }
    if ($DryRun) {
        $summary.killed += [ordered]@{ pid = $procId; reason = $reason; dry_run = $true }
        return
    }
    try {
        & taskkill /PID $procId /T /F 2>$null | Out-Null
        $summary.killed += [ordered]@{ pid = $procId; reason = $reason; dry_run = $false }
    } catch {
        $summary.kill_errors += [ordered]@{ pid = $procId; reason = $reason; error = $_.Exception.Message }
    }
}

function Ensure-Dir([string]$path) {
    $parent = Split-Path -Path $path -Parent
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -Path $parent -ItemType Directory -Force | Out-Null
    }
}

$start = Get-Date
$now = Get-Date
$reportAbs = if ([System.IO.Path]::IsPathRooted($ReportPath)) { $ReportPath } else { Join-Path (Get-Location) $ReportPath }

$summary = [ordered]@{
    generated_at = $start.ToString("yyyy-MM-dd HH:mm:ss")
    node_max_age_minutes = $NodeMaxAgeMinutes
    chrome_max_age_minutes = $ChromeMaxAgeMinutes
    temp_retention_hours = $TempRetentionHours
    dry_run = [bool]$DryRun
    killed = @()
    kill_errors = @()
    removed_dirs = @()
    remove_dir_errors = @()
    removed_files = @()
    remove_file_errors = @()
}

# Build process commandline index once.
$allWmi = @()
try {
    $allWmi = Get-CimInstance Win32_Process -ErrorAction Stop
} catch {
    Write-Info "failed to list Win32_Process: $($_.Exception.Message)"
    $allWmi = @()
}

$cmdByPid = @{}
foreach ($p in $allWmi) {
    $cmdByPid[[int]$p.ProcessId] = [string]$p.CommandLine
}

# 1) Cleanup stale/orphan Playwright daemon node processes.
$pwNodes = $allWmi | Where-Object {
    $_.Name -ieq "node.exe" -and [string]$_.CommandLine -match "playwright\\cli\.js run-cli-server"
}

foreach ($n in $pwNodes) {
    $procId = [int]$n.ProcessId
    $created = To-DateTime([string]$n.CreationDate)
    $ageMin = if ($created) { [math]::Round(($now - $created).TotalMinutes, 2) } else { 99999 }
    $parentPid = [int]$n.ParentProcessId
    $parentAlive = Is-Alive -procId $parentPid
    $isOrphan = -not $parentAlive
    if ($isOrphan -or $ageMin -ge $NodeMaxAgeMinutes) {
        $reason = if ($isOrphan) { "playwright_node_orphan" } else { "playwright_node_stale_${ageMin}m" }
        Kill-Tree -procId $procId -reason $reason -summary $summary
    }
}

# 2) Cleanup stale/orphan Playwright chrome child processes.
$pwChromes = $allWmi | Where-Object {
    $_.Name -ieq "chrome.exe" -and [string]$_.CommandLine -match "playwright_chromiumdev_profile-"
}

foreach ($c in $pwChromes) {
    $procId = [int]$c.ProcessId
    $created = To-DateTime([string]$c.CreationDate)
    $ageMin = if ($created) { [math]::Round(($now - $created).TotalMinutes, 2) } else { 99999 }
    $parentPid = [int]$c.ParentProcessId
    $parentCmd = [string]($cmdByPid[$parentPid])
    $parentAlive = Is-Alive -procId $parentPid
    $parentIsPwNode = $parentCmd -match "playwright\\cli\.js run-cli-server"
    $isOrphan = (-not $parentAlive) -or (-not $parentIsPwNode)
    if ($isOrphan -or $ageMin -ge $ChromeMaxAgeMinutes) {
        $reason = if ($isOrphan) { "playwright_chrome_orphan" } else { "playwright_chrome_stale_${ageMin}m" }
        Kill-Tree -procId $procId -reason $reason -summary $summary
    }
}

# 3) Cleanup leftover preview process (localhost test proxy).
$previewProcs = $allWmi | Where-Object {
    [string]$_.CommandLine -match "build_co_banner_private_preview\.py"
}
foreach ($p in $previewProcs) {
    $procId = [int]$p.ProcessId
    $created = To-DateTime([string]$p.CreationDate)
    $ageMin = if ($created) { [math]::Round(($now - $created).TotalMinutes, 2) } else { 99999 }
    if ($ageMin -ge 15) {
        Kill-Tree -procId $procId -reason "preview_proxy_stale_${ageMin}m" -summary $summary
    }
}

# 4) Remove stale Playwright temp profiles not in active process commandline.
$activeCmdText = ($allWmi | ForEach-Object { [string]$_.CommandLine }) -join "`n"
$tempDir = [string]$env:TEMP
$cutoff = $now.AddHours(-1 * [Math]::Abs($TempRetentionHours))
$tmpPatterns = @(
    "playwright_chromiumdev_profile-*",
    "playwright_chromiumdev-*",
    "playwright_*"
)

$candidates = @()
foreach ($pat in $tmpPatterns) {
    try {
        $candidates += Get-ChildItem -Path $tempDir -Directory -Filter $pat -ErrorAction SilentlyContinue
    } catch {}
}

$seen = @{}
foreach ($d in $candidates) {
    if (-not $d) { continue }
    if ($seen.ContainsKey($d.FullName)) { continue }
    $seen[$d.FullName] = $true
    if ($d.LastWriteTime -gt $cutoff) { continue }
    if ($activeCmdText -like "*$($d.FullName)*") { continue }
    if ($DryRun) {
        $summary.removed_dirs += [ordered]@{ path = $d.FullName; dry_run = $true }
        continue
    }
    try {
        Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction Stop
        $summary.removed_dirs += [ordered]@{ path = $d.FullName; dry_run = $false }
    } catch {
        $summary.remove_dir_errors += [ordered]@{ path = $d.FullName; error = $_.Exception.Message }
    }
}

# 5) Remove stale daemon session files.
$daemonRoot = Join-Path $env:LOCALAPPDATA "ms-playwright\daemon"
if (Test-Path -LiteralPath $daemonRoot) {
    $sessionFiles = Get-ChildItem -Path $daemonRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "live*.session" -or $_.Name -like "*.session" }
    foreach ($f in $sessionFiles) {
        if ($f.LastWriteTime -gt $cutoff) { continue }
        if ($activeCmdText -like "*$($f.FullName)*") { continue }
        if ($DryRun) {
            $summary.removed_files += [ordered]@{ path = $f.FullName; dry_run = $true }
            continue
        }
        try {
            Remove-Item -LiteralPath $f.FullName -Force -ErrorAction Stop
            $summary.removed_files += [ordered]@{ path = $f.FullName; dry_run = $false }
        } catch {
            $summary.remove_file_errors += [ordered]@{ path = $f.FullName; error = $_.Exception.Message }
        }
    }
}

$summary.duration_sec = [math]::Round(((Get-Date) - $start).TotalSeconds, 2)
$summary.killed_count = @($summary.killed).Count
$summary.removed_dir_count = @($summary.removed_dirs).Count
$summary.removed_file_count = @($summary.removed_files).Count
$summary.ok = (@($summary.kill_errors).Count -eq 0 -and @($summary.remove_dir_errors).Count -eq 0 -and @($summary.remove_file_errors).Count -eq 0)

Ensure-Dir -path $reportAbs
($summary | ConvertTo-Json -Depth 8) | Set-Content -Path $reportAbs -Encoding UTF8

Write-Info ("[saved] {0}" -f $reportAbs)
Write-Info ("[ok] {0}" -f $summary.ok)
Write-Info ("[killed] {0}" -f $summary.killed_count)
Write-Info ("[removed_dirs] {0}" -f $summary.removed_dir_count)
Write-Info ("[removed_files] {0}" -f $summary.removed_file_count)
