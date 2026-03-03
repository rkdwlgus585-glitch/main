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

if (Test-Path $krOnlyLockPath) {
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
    [string]$lastMemoFullDate
) {
    $payload = @{
        updated_at = (Get-Date).ToString("s")
        next_now_to_sheet = $nextNowRun.ToString("s")
        now_fail_streak = [int]$nowFailStreak
        next_confirmed_publish = $nextPublishRun.ToString("s")
        next_notice_archive = $nextNoticeArchiveRun.ToString("s")
        next_admin_memo_incremental = $nextMemoIncrementalRun.ToString("s")
        last_admin_memo_full_date = [string]$lastMemoFullDate
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

while ($true) {
    $now = Get-Date
    if (-not (Test-InActiveWindow $now)) {
        Save-State $nextNowRun $nowFailStreak $nextPublishRun $nextNoticeArchiveRun $nextMemoIncrementalRun $lastMemoFullDate
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
    $todayKey = $now.ToString("yyyy-MM-dd")
    $memoFullTarget = Get-TodayMemoFullTarget $now
    if ($lastMemoFullDate -ne $todayKey -and $now -ge $memoFullTarget) {
        $fullRc = Invoke-RepoCommand "admin_memo_full" $cmdMemoFull
        if ($fullRc -eq 0) {
            $lastMemoFullDate = $todayKey
        }
    }

    Save-State $nextNowRun $nowFailStreak $nextPublishRun $nextNoticeArchiveRun $nextMemoIncrementalRun $lastMemoFullDate
    Start-Sleep -Seconds $loopSleepSeconds
}
