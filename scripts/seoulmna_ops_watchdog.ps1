# Keeps SeoulMNA listing-side automation alive for the current user session.
param(
    [string]$RepoRoot = "",
    [int]$StartupDelaySec = 0
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
$scriptName = "seoulmna_ops_watchdog.ps1"
$krOnlyLockPath = Join-Path $RepoRoot "logs\kr_only_mode.lock"

function Test-CalculatorAutodriveRunning {
    $rows = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^(?:python|py)(?:\.exe)?$" -and $_.CommandLine -match "run_calculator_autodrive\.py"
    }
    return [bool]($rows | Select-Object -First 1)
}

function Test-KrOnlyLockActive([string]$lockPath) {
    if (-not (Test-Path $lockPath)) {
        return $false
    }

    if (Test-CalculatorAutodriveRunning) {
        return $true
    }

    $raw = ""
    $reason = ""
    try {
        $raw = Get-Content -Path $lockPath -Raw -Encoding UTF8
    } catch {
        $raw = ""
    }

    if (-not [string]::IsNullOrWhiteSpace($raw) -and $raw.TrimStart().StartsWith("{")) {
        try {
            $obj = $raw | ConvertFrom-Json
            if ($obj -and $obj.reason) {
                $reason = [string]$obj.reason
            }
        } catch {
        }
    }

    if ($reason -match "(?i)run_calculator_autodrive|start_calculator_autodrive") {
        try {
            Remove-Item $lockPath -Force
        } catch {
        }
        return $false
    }

    return $true
}

if (Test-KrOnlyLockActive $krOnlyLockPath) {
    exit 0
}

if (-not (Test-Path (Join-Path $RepoRoot "all.py"))) {
    exit 1
}

$pythonExe = "C:\Users\rkdwl\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $pythonExe = $pyLauncher.Source
    } else {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            $pythonExe = $pythonCmd.Source
        } else {
            exit 1
        }
    }
}

function Get-PythonPrefix {
    if ($pythonExe.ToLowerInvariant().EndsWith("py.exe")) {
        return ('"{0}" -3' -f $pythonExe)
    }
    return ('"{0}"' -f $pythonExe)
}

$pythonPrefix = Get-PythonPrefix

# Prevent duplicate watchdog loops.
$dupeRows = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^powershell(?:\.exe)?$" -and $_.CommandLine -match [regex]::Escape($scriptName)
}
if (($dupeRows | Measure-Object).Count -gt 1) {
    exit 0
}

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$watchdogLog = Join-Path $logsDir "ops_watchdog.log"
$statePath = Join-Path $logsDir "ops_watchdog_state.json"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $watchdogLog -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Save-State(
    [datetime]$nextNowRun,
    [int]$nowFailStreak,
    [datetime]$nextPublishRun,
    [datetime]$nextNoticeArchiveRun,
    [datetime]$nextMemoIncrementalRun,
    [string]$lastMemoFullDate,
    [datetime]$nextSiteGuardRun,
    [datetime]$nextRankMathDetailRun,
    [datetime]$nextCxProbeRun,
    [datetime]$nextDomSnapshotRun,
    [datetime]$nextCxForceRecoverRun,
    [datetime]$nextCxHealthDigestRun,
    [datetime]$nextLocalSyncRun
) {
    $payload = @{
        updated_at = (Get-Date).ToString("s")
        next_now_to_sheet = $nextNowRun.ToString("s")
        now_fail_streak = [int]$nowFailStreak
        next_confirmed_publish = $nextPublishRun.ToString("s")
        next_notice_archive = $nextNoticeArchiveRun.ToString("s")
        next_admin_memo_incremental = $nextMemoIncrementalRun.ToString("s")
        last_admin_memo_full_date = [string]$lastMemoFullDate
        next_wp_site_guard = $nextSiteGuardRun.ToString("s")
        next_rankmath_detail = $nextRankMathDetailRun.ToString("s")
        next_site_cx_probe = $nextCxProbeRun.ToString("s")
        next_site_dom_snapshot = $nextDomSnapshotRun.ToString("s")
        next_site_cx_force_recover = $nextCxForceRecoverRun.ToString("s")
        next_site_cx_health_digest = $nextCxHealthDigestRun.ToString("s")
        next_local_mna_sync = $nextLocalSyncRun.ToString("s")
    }
    try {
        $json = $payload | ConvertTo-Json -Depth 4
        Set-Content -Path $statePath -Encoding UTF8 -Value $json
    } catch {
    }
}

function Load-LastMemoFullDate {
    if (-not (Test-Path $statePath)) {
        return ""
    }
    try {
        $raw = Get-Content -Path $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($raw -and $raw.last_admin_memo_full_date) {
            return [string]$raw.last_admin_memo_full_date
        }
    } catch {
    }
    return ""
}

function Invoke-RepoCommand([string]$jobName, [string]$repoCommand) {
    $argLine = ('/d /c chcp 65001 >nul && cd /d "{0}" && {1}' -f $RepoRoot, $repoCommand)
    Write-Log ("{0} start: {1}" -f $jobName, $repoCommand)
    try {
        $proc = Start-Process -FilePath "cmd.exe" -ArgumentList $argLine -WindowStyle Hidden -PassThru -Wait
        $rc = 0
        if ($proc) {
            $rc = [int]$proc.ExitCode
        }
        Write-Log ("{0} end rc={1}" -f $jobName, $rc)
        return $rc
    } catch {
        Write-Log ("{0} failed to start: {1}" -f $jobName, $_.Exception.Message)
        return 1
    }
}

function Ensure-LocalAutoBridge([string]$repoCommand) {
    $bridgeRows = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^(?:python|py)(?:\.exe)?$" -and $_.CommandLine -match "local_auto_state_bridge\.py"
    }
    if (($bridgeRows | Measure-Object).Count -ge 1) {
        return
    }
    $launcherRows = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^cmd(?:\.exe)?$" -and $_.CommandLine -match "run_local_auto_state_bridge\.cmd"
    }
    if (($launcherRows | Measure-Object).Count -ge 1) {
        return
    }
    $argLine = ('/d /c chcp 65001 >nul && cd /d "{0}" && {1}' -f $RepoRoot, $repoCommand)
    try {
        Start-Process -FilePath "cmd.exe" -ArgumentList $argLine -WindowStyle Hidden | Out-Null
        Write-Log "local_auto_bridge started"
    } catch {
        Write-Log ("local_auto_bridge failed to start: {0}" -f $_.Exception.Message)
    }
}

function Get-ActiveWindowInfo([datetime]$ts) {
    # User machine availability:
    # - Weekday: 09:00 ~ 23:00
    # - Weekend: 14:00 ~ 23:00
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) {
        return @{
            StartHour = 14
            EndHour = 23
            MemoFullHour = 15
            MemoFullMinute = 0
            Label = "weekend"
        }
    }
    return @{
        StartHour = 9
        EndHour = 23
        MemoFullHour = 10
        MemoFullMinute = 0
        Label = "weekday"
    }
}

function Test-InActiveWindow([datetime]$ts) {
    $win = Get-ActiveWindowInfo $ts
    return ($ts.Hour -ge [int]$win.StartHour) -and ($ts.Hour -lt [int]$win.EndHour)
}

function Get-TodayMemoFullTarget([datetime]$ts) {
    $win = Get-ActiveWindowInfo $ts
    return $ts.Date.AddHours([double][int]$win.MemoFullHour).AddMinutes([double][int]$win.MemoFullMinute)
}

function Get-MemoIncrementalIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) {
        # Weekend: increase admin-memo throughput
        return 45
    }
    # Weekday: keep conservative baseline
    return 90
}

$publishIntervalMinutes = 90
$noticeArchiveIntervalMinutes = 180
$loopSleepSeconds = 30

function Get-NextNowToSheetRun([datetime]$ts) {
    $base = $ts
    $slotNoon = $base.Date.AddHours(12)
    $slotEvening = $base.Date.AddHours(18)

    if ($base -lt $slotNoon) { return $slotNoon }
    if ($base -lt $slotEvening) { return $slotEvening }
    return $base.Date.AddDays(1).AddHours(12)
}

function Get-PublishIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 60 }
    return 90
}

function Get-NoticeArchiveIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 120 }
    return 180
}

function Get-QualityIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 120 }
    return 240
}

function Get-SiteGuardIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 90 }
    return 120
}

function Get-RankMathDetailIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 180 }
    return 240
}

function Get-CXProbeIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 60 }
    return 90
}

function Get-DomSnapshotIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 90 }
    return 120
}

function Get-CXForceRecoverIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 20 }
    return 30
}

function Get-CXHealthDigestIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 120 }
    return 180
}

function Get-LocalMnaSyncIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 120 }
    return 90
}

function Get-SustainabilityGuardIntervalMinutes([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 360 }
    return 480
}

function Get-PermitCollectIntervalMinutes([datetime]$ts) {
    return 1440
}

function Get-MemoIncrementalLimit([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 40 }
    return 20
}

function Get-MemoIncrementalDelaySec([datetime]$ts) {
    $isWeekend = ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
    if ($isWeekend) { return 1.2 }
    return 2.0
}

$nextNowRun = Get-NextNowToSheetRun (Get-Date)
$nextPublishRun = (Get-Date).AddMinutes(8)
$nextNoticeArchiveRun = (Get-Date).AddMinutes(20)
$nextMemoIncrementalRun = (Get-Date).AddMinutes(12)
$nextQualityDailyRun = (Get-Date).AddMinutes(25)
$nextSiteGuardRun = (Get-Date).AddMinutes(15)
$nextRankMathDetailRun = (Get-Date).AddMinutes(28)
$nextCxProbeRun = (Get-Date).AddMinutes(18)
$nextDomSnapshotRun = (Get-Date).AddMinutes(22)
$nextCxForceRecoverRun = (Get-Date).AddMinutes(14)
$nextCxHealthDigestRun = (Get-Date).AddMinutes(16)
$nextLocalSyncRun = (Get-Date).AddMinutes(10)
$nextSustainabilityGuardRun = (Get-Date).AddMinutes(35)
$nextPermitCollectRun = (Get-Date).AddMinutes(40)
$nowFailStreak = 0
$lastMemoFullDate = Load-LastMemoFullDate

$cmdNowToSheet = 'scripts\run_startup_now_to_sheet.cmd'
$cmdConfirmedPublish = (
    '{0} scripts\republish_from_audit.py --key-mode year --delay-sec 1.8 --request-buffer 120 --write-buffer 12 --yes >> logs\auto_confirmed_publish.log 2>&1' -f $pythonPrefix
)
$cmdNoticeArchive = 'scripts\run_startup_notice_archive.cmd'
$cmdMemoFull = (
    '{0} all.py --fix-admin-memo --fix-admin-memo-all --fix-admin-memo-pages 0 --fix-admin-memo-limit 0 --fix-admin-memo-delay-sec 1.2 --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 --fix-admin-memo-state-file logs/admin_memo_sync_state.json >> logs\auto_admin_memo_sync.log 2>&1' -f $pythonPrefix
)
$cmdQualityDaily = 'scripts\run_quality_daily.cmd'
$cmdDailyDashboard = (
    '{0} all.py --daily-dashboard --dashboard-live --dashboard-days 7 >> logs\auto_daily_dashboard.log 2>&1' -f $pythonPrefix
)
$cmdSiteGuard = (
    '{0} scripts\optimize_wp_kr.py --report logs/wp_site_guard_latest.json >> logs\auto_wp_site_guard.log 2>&1' -f $pythonPrefix
)
$cmdRankMathDetail = (
    '{0} scripts\rankmath_detail_optimizer.py --report logs/rankmath_detail_opt_latest.json >> logs\auto_rankmath_detail.log 2>&1' -f $pythonPrefix
)
$cmdCxProbe = (
    '{0} scripts\site_cx_probe.py --report logs/site_cx_probe_latest.json >> logs\auto_site_cx_probe.log 2>&1' -f $pythonPrefix
)
$cmdCxAutoHeal = (
    '{0} scripts\site_cx_autoheal.py --probe-report logs/site_cx_probe_latest.json --summary-report logs/site_cx_autoheal_latest.json --apply-report logs/co_global_banner_apply_latest.json >> logs\auto_site_cx_autoheal.log 2>&1' -f $pythonPrefix
)
$cmdDomSnapshot = (
    '{0} scripts\site_dom_snapshot.py --report logs/site_dom_snapshot_latest.json >> logs\auto_site_dom_snapshot.log 2>&1' -f $pythonPrefix
)
$cmdCxHealthRollup = (
    '{0} scripts\site_cx_health_rollup.py --latest-report logs/site_cx_health_rollup_latest.json --history logs/site_cx_health_history.jsonl --alert-on-change --alert-state logs/site_cx_health_alert_state.json --alert-repeat-min 120 >> logs\auto_site_cx_health_rollup.log 2>&1' -f $pythonPrefix
)
$cmdCxForceRecover = (
    '{0} scripts\site_cx_force_recover.py --rollup-file logs/site_cx_health_rollup_latest.json --rollup-history logs/site_cx_health_history.jsonl --state-file logs/site_cx_force_recover_state.json --report logs/site_cx_force_recover_latest.json --failure-threshold 2 --cooldown-min 180 >> logs\auto_site_cx_force_recover.log 2>&1' -f $pythonPrefix
)
$cmdCxHealthDigest = (
    '{0} scripts\site_cx_health_digest.py --history logs/site_cx_health_history.jsonl --rollup logs/site_cx_health_rollup_latest.json --latest-json logs/site_cx_health_digest_latest.json --latest-md logs/site_cx_health_digest_latest.md --days 7 >> logs\auto_site_cx_health_digest.log 2>&1' -f $pythonPrefix
)
$cmdLocalAutoBridge = 'scripts\run_local_auto_state_bridge.cmd >> logs\auto_local_state_bridge.log 2>&1'
$cmdLocalMnaSync = 'scripts\run_mna_state_local_sync.cmd >> logs\auto_mna_state_local_sync.log 2>&1'
$cmdSustainabilityGuard = (
    '{0} scripts\sustainability_guard.py --contract quality_contracts/sustainability_guard.contract.json --report logs/sustainability_guard_latest.json >> logs\auto_sustainability_guard.log 2>&1' -f $pythonPrefix
)
$cmdPermitCollect = (
    '{0} scripts\collect_kr_permit_industries.py --output config/kr_permit_industries_localdata.json >> logs\auto_permit_collect.log 2>&1' -f $pythonPrefix
)

Write-Log "ops watchdog loop started"
$delaySec = [int]$StartupDelaySec
if ($delaySec -gt 0) {
    Write-Log ("startup delay begin: {0}s" -f $delaySec)
    Start-Sleep -Seconds $delaySec
    Write-Log "startup delay end"
}
$bootWindow = Get-ActiveWindowInfo (Get-Date)
Write-Log ("active window profile={0} start={1:00}:00 end={2:00}:00 memo_full={3:00}:{4:00}" -f $bootWindow.Label, [int]$bootWindow.StartHour, [int]$bootWindow.EndHour, [int]$bootWindow.MemoFullHour, [int]$bootWindow.MemoFullMinute)
$memoIntervalBoot = Get-MemoIncrementalIntervalMinutes (Get-Date)
Write-Log ("admin memo incremental interval={0}m" -f [int]$memoIntervalBoot)
Write-Log ("now-to-sheet fixed slots: 12:00, 18:00 / next={0}" -f $nextNowRun.ToString("s"))
Write-Log ("wp site guard interval={0}m / next={1}" -f [int](Get-SiteGuardIntervalMinutes (Get-Date)), $nextSiteGuardRun.ToString("s"))
Write-Log ("rankmath detail interval={0}m / next={1}" -f [int](Get-RankMathDetailIntervalMinutes (Get-Date)), $nextRankMathDetailRun.ToString("s"))
Write-Log ("site cx probe interval={0}m / next={1}" -f [int](Get-CXProbeIntervalMinutes (Get-Date)), $nextCxProbeRun.ToString("s"))
Write-Log ("site dom snapshot interval={0}m / next={1}" -f [int](Get-DomSnapshotIntervalMinutes (Get-Date)), $nextDomSnapshotRun.ToString("s"))
Write-Log ("site force recover interval={0}m / next={1}" -f [int](Get-CXForceRecoverIntervalMinutes (Get-Date)), $nextCxForceRecoverRun.ToString("s"))
Write-Log ("site health digest interval={0}m / next={1}" -f [int](Get-CXHealthDigestIntervalMinutes (Get-Date)), $nextCxHealthDigestRun.ToString("s"))
Write-Log ("local mna sync interval={0}m / next={1}" -f [int](Get-LocalMnaSyncIntervalMinutes (Get-Date)), $nextLocalSyncRun.ToString("s"))
Write-Log ("sustainability guard interval={0}m / next={1}" -f [int](Get-SustainabilityGuardIntervalMinutes (Get-Date)), $nextSustainabilityGuardRun.ToString("s"))
Write-Log ("permit collect interval={0}m / next={1}" -f [int](Get-PermitCollectIntervalMinutes (Get-Date)), $nextPermitCollectRun.ToString("s"))
Write-Log "site cx auto-heal: enabled (runs right after site_cx_probe)"
Write-Log "site cx health rollup: enabled (runs after site_cx_autoheal)"
Ensure-LocalAutoBridge $cmdLocalAutoBridge

while ($true) {
    $now = Get-Date
    Ensure-LocalAutoBridge $cmdLocalAutoBridge
    if (-not (Test-InActiveWindow $now)) {
        Save-State $nextNowRun $nowFailStreak $nextPublishRun $nextNoticeArchiveRun $nextMemoIncrementalRun $lastMemoFullDate $nextSiteGuardRun $nextRankMathDetailRun $nextCxProbeRun $nextDomSnapshotRun $nextCxForceRecoverRun $nextCxHealthDigestRun $nextLocalSyncRun
        Start-Sleep -Seconds $loopSleepSeconds
        continue
    }

    if ($now -ge $nextNowRun) {
        $rc = Invoke-RepoCommand "now_to_sheet" $cmdNowToSheet
        if ($rc -eq 0) { $nowFailStreak = 0 } else { $nowFailStreak += 1 }
        $nextNowRun = Get-NextNowToSheetRun ((Get-Date).AddMinutes(1))
        Write-Log ("now-to-sheet next slot={0} fail_streak={1}" -f $nextNowRun.ToString("s"), [int]$nowFailStreak)
    }

    $now = Get-Date
    if ($now -ge $nextPublishRun) {
        [void](Invoke-RepoCommand "confirmed_publish" $cmdConfirmedPublish)
        $publishInterval = Get-PublishIntervalMinutes (Get-Date)
        $nextPublishRun = (Get-Date).AddMinutes($publishInterval)
    }

    $now = Get-Date
    if ($now -ge $nextNoticeArchiveRun) {
        [void](Invoke-RepoCommand "notice_archive_refresh" $cmdNoticeArchive)
        $archiveInterval = Get-NoticeArchiveIntervalMinutes (Get-Date)
        $nextNoticeArchiveRun = (Get-Date).AddMinutes($archiveInterval)
    }

    $now = Get-Date
    if ($now -ge $nextMemoIncrementalRun) {
        $memoLimit = Get-MemoIncrementalLimit (Get-Date)
        $memoDelay = Get-MemoIncrementalDelaySec (Get-Date)
        $cmdMemoIncremental = (
            '{0} all.py --fix-admin-memo --fix-admin-memo-all --fix-admin-memo-pages 3 --fix-admin-memo-limit {1} --fix-admin-memo-delay-sec {2} --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 --fix-admin-memo-state-file logs/admin_memo_sync_state.json >> logs\auto_admin_memo_sync.log 2>&1' -f $pythonPrefix, [int]$memoLimit, [double]$memoDelay
        )
        [void](Invoke-RepoCommand "admin_memo_incremental" $cmdMemoIncremental)
        $memoIntervalMinutes = Get-MemoIncrementalIntervalMinutes (Get-Date)
        $nextMemoIncrementalRun = (Get-Date).AddMinutes([int]$memoIntervalMinutes)
    }

    $now = Get-Date
    if ($now -ge $nextQualityDailyRun) {
        [void](Invoke-RepoCommand "quality_daily" $cmdQualityDaily)
        [void](Invoke-RepoCommand "daily_dashboard" $cmdDailyDashboard)
        $qualityInterval = Get-QualityIntervalMinutes (Get-Date)
        $nextQualityDailyRun = (Get-Date).AddMinutes([int]$qualityInterval)
    }

    $now = Get-Date
    if ($now -ge $nextSiteGuardRun) {
        [void](Invoke-RepoCommand "wp_site_guard" $cmdSiteGuard)
        $siteGuardInterval = Get-SiteGuardIntervalMinutes (Get-Date)
        $nextSiteGuardRun = (Get-Date).AddMinutes([int]$siteGuardInterval)
    }

    $now = Get-Date
    if ($now -ge $nextRankMathDetailRun) {
        [void](Invoke-RepoCommand "rankmath_detail_opt" $cmdRankMathDetail)
        $rankMathInterval = Get-RankMathDetailIntervalMinutes (Get-Date)
        $nextRankMathDetailRun = (Get-Date).AddMinutes([int]$rankMathInterval)
    }

    $now = Get-Date
    if ($now -ge $nextCxProbeRun) {
        [void](Invoke-RepoCommand "site_cx_probe" $cmdCxProbe)
        [void](Invoke-RepoCommand "site_cx_autoheal" $cmdCxAutoHeal)
        [void](Invoke-RepoCommand "site_cx_health_rollup" $cmdCxHealthRollup)
        $cxInterval = Get-CXProbeIntervalMinutes (Get-Date)
        $nextCxProbeRun = (Get-Date).AddMinutes([int]$cxInterval)
    }

    $now = Get-Date
    if ($now -ge $nextDomSnapshotRun) {
        [void](Invoke-RepoCommand "site_dom_snapshot" $cmdDomSnapshot)
        [void](Invoke-RepoCommand "site_cx_health_rollup" $cmdCxHealthRollup)
        $domInterval = Get-DomSnapshotIntervalMinutes (Get-Date)
        $nextDomSnapshotRun = (Get-Date).AddMinutes([int]$domInterval)
    }

    $now = Get-Date
    if ($now -ge $nextCxForceRecoverRun) {
        [void](Invoke-RepoCommand "site_cx_force_recover" $cmdCxForceRecover)
        $recoverInterval = Get-CXForceRecoverIntervalMinutes (Get-Date)
        $nextCxForceRecoverRun = (Get-Date).AddMinutes([int]$recoverInterval)
    }

    $now = Get-Date
    if ($now -ge $nextCxHealthDigestRun) {
        [void](Invoke-RepoCommand "site_cx_health_digest" $cmdCxHealthDigest)
        $digestInterval = Get-CXHealthDigestIntervalMinutes (Get-Date)
        $nextCxHealthDigestRun = (Get-Date).AddMinutes([int]$digestInterval)
    }

    $now = Get-Date
    if ($now -ge $nextLocalSyncRun) {
        [void](Invoke-RepoCommand "mna_state_local_sync" $cmdLocalMnaSync)
        $localSyncInterval = Get-LocalMnaSyncIntervalMinutes (Get-Date)
        $nextLocalSyncRun = (Get-Date).AddMinutes([int]$localSyncInterval)
    }

    $now = Get-Date
    if ($now -ge $nextSustainabilityGuardRun) {
        [void](Invoke-RepoCommand "sustainability_guard" $cmdSustainabilityGuard)
        $sustainabilityInterval = Get-SustainabilityGuardIntervalMinutes (Get-Date)
        $nextSustainabilityGuardRun = (Get-Date).AddMinutes([int]$sustainabilityInterval)
    }

    $now = Get-Date
    if ($now -ge $nextPermitCollectRun) {
        [void](Invoke-RepoCommand "permit_collect" $cmdPermitCollect)
        $permitCollectInterval = Get-PermitCollectIntervalMinutes (Get-Date)
        $nextPermitCollectRun = (Get-Date).AddMinutes([int]$permitCollectInterval)
    }

    $now = Get-Date
    $todayKey = $now.ToString("yyyy-MM-dd")
    $memoFullTarget = Get-TodayMemoFullTarget $now
    if ($lastMemoFullDate -ne $todayKey -and $now -ge $memoFullTarget) {
        $fullRc = Invoke-RepoCommand "admin_memo_full" $cmdMemoFull
        if ($fullRc -eq 0) {
            $lastMemoFullDate = $todayKey
        }
    }

    Save-State $nextNowRun $nowFailStreak $nextPublishRun $nextNoticeArchiveRun $nextMemoIncrementalRun $lastMemoFullDate $nextSiteGuardRun $nextRankMathDetailRun $nextCxProbeRun $nextDomSnapshotRun $nextCxForceRecoverRun $nextCxHealthDigestRun $nextLocalSyncRun
    Start-Sleep -Seconds $loopSleepSeconds
}
