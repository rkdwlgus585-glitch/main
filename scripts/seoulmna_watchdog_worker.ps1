param(
    [string]$RepoRoot = "",
    [ValidateSet("listing", "monthly_recommend", "monthly_report", "admin_memo", "site_health", "permit")]
    [string]$Profile = "listing",
    [int]$StartupDelaySec = 0
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
$Profile = [string]$Profile.ToLowerInvariant()

$krOnlyLockPath = Join-Path $RepoRoot "logs\kr_only_mode.lock"
$mutexSuffix = [Math]::Abs($RepoRoot.ToLowerInvariant().GetHashCode())
$scriptName = "seoulmna_watchdog_worker.ps1"
$siteWriteMutexName = "Local\SeoulMNA_CoKr_SiteWrite_{0}" -f $mutexSuffix
$loopSleepSeconds = 30

function New-SingleInstanceMutex([string]$name) {
    $createdNew = $false
    try {
        $mutex = New-Object System.Threading.Mutex($true, $name, [ref]$createdNew)
        if (-not $createdNew) {
            try { $mutex.Dispose() } catch {}
            return $null
        }
        return $mutex
    } catch {
        return $null
    }
}

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
        } catch {}
    }

    if ($reason -match "(?i)run_calculator_autodrive|start_calculator_autodrive") {
        try { Remove-Item $lockPath -Force } catch {}
        return $false
    }

    return $true
}

if (Test-KrOnlyLockActive $krOnlyLockPath) {
    exit 0
}

if (-not (Test-Path (Join-Path $RepoRoot "utils.py"))) {
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

$instanceMutexName = "Local\SeoulMNA_{0}_Watchdog_{1}" -f $Profile.ToUpperInvariant(), $mutexSuffix
$watchdogMutex = New-SingleInstanceMutex $instanceMutexName
if (-not $watchdogMutex) {
    exit 0
}

$profilePattern = '(?i)-Profile"?\s+"?' + [regex]::Escape($Profile) + '"?'
$dupeRows = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^powershell(?:\.exe)?$' -and
    $_.CommandLine -match [regex]::Escape($scriptName) -and
    $_.CommandLine -match $profilePattern
}
if (($dupeRows | Measure-Object).Count -gt 1) {
    try { $watchdogMutex.ReleaseMutex() | Out-Null } catch {}
    try { $watchdogMutex.Dispose() } catch {}
    exit 0
}

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$slug = $Profile.Replace('_', '-')
$watchdogLog = Join-Path $logsDir ("watchdog_{0}.log" -f $slug)
$statePath = Join-Path $logsDir ("watchdog_{0}_state.json" -f $slug)

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $watchdogLog -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Load-State {
    if (-not (Test-Path $statePath)) {
        return $null
    }
    try {
        return Get-Content -Path $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Save-State([hashtable]$payload) {
    $payload["updated_at"] = (Get-Date).ToString("s")
    $payload["profile"] = $Profile
    try {
        $json = $payload | ConvertTo-Json -Depth 6
        Set-Content -Path $statePath -Encoding UTF8 -Value $json
    } catch {}
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

function Invoke-RepoSiteWriteCommand([string]$jobName, [string]$repoCommand, [int]$WaitTimeoutSec = 7200) {
    $mutex = $null
    $acquired = $false
    try {
        $mutex = New-Object System.Threading.Mutex($false, $siteWriteMutexName)
    } catch {
        Write-Log ("{0} failed site-write mutex open: {1}" -f $jobName, $_.Exception.Message)
        return 1
    }

    try {
        Write-Log ("{0} wait site-write lock" -f $jobName)
        try {
            $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds([double]$WaitTimeoutSec))
        } catch [System.Threading.AbandonedMutexException] {
            $acquired = $true
            Write-Log ("{0} site-write lock abandoned; continuing" -f $jobName)
        }
        if (-not $acquired) {
            Write-Log ("{0} skip: site-write lock-timeout {1}s" -f $jobName, [int]$WaitTimeoutSec)
            return 1
        }
        Write-Log ("{0} acquired site-write lock" -f $jobName)
        return Invoke-RepoCommand $jobName $repoCommand
    } finally {
        if ($acquired) {
            try { $mutex.ReleaseMutex() | Out-Null } catch {}
            Write-Log ("{0} released site-write lock" -f $jobName)
        }
        if ($mutex) {
            try { $mutex.Dispose() } catch {}
        }
    }
}

function Test-IsWeekend([datetime]$ts) {
    return ($ts.DayOfWeek -eq [System.DayOfWeek]::Saturday -or $ts.DayOfWeek -eq [System.DayOfWeek]::Sunday)
}

function Get-WeekendAdjustedInterval([datetime]$ts, [int]$weekdayMinutes, [int]$weekendMinutes) {
    if (Test-IsWeekend $ts) { return $weekendMinutes }
    return $weekdayMinutes
}

function Get-ActiveWindowInfo([datetime]$ts) {
    if (Test-IsWeekend $ts) {
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

function Get-NextFixedSlotRun([datetime]$ts, [int[]]$slotHours) {
    $base = $ts
    foreach ($hour in $slotHours) {
        $candidate = $base.Date.AddHours([double]$hour)
        if ($base -lt $candidate.AddMinutes(1)) {
            return $candidate
        }
    }
    return $base.Date.AddDays(1).AddHours([double]$slotHours[0])
}

$script:KrHolidayCache = @{}
$script:KrLunarCalendar = New-Object System.Globalization.KoreanLunisolarCalendar
$script:KrLunarEra = $script:KrLunarCalendar.Eras[0]

function Add-HolidayDate([hashtable]$holidays, [datetime]$date) {
    $key = $date.Date.ToString("yyyy-MM-dd")
    $count = 0
    if ($holidays.ContainsKey($key)) {
        $count = [int]$holidays[$key]
    }
    $holidays[$key] = $count + 1
}

function Convert-KoreanLunarToSolar([int]$lunarYear, [int]$lunarMonth, [int]$lunarDay) {
    $monthIndex = [int]$lunarMonth
    $leapMonth = $script:KrLunarCalendar.GetLeapMonth($lunarYear, $script:KrLunarEra)
    if ($leapMonth -gt 0 -and $leapMonth -le $lunarMonth) {
        $monthIndex += 1
    }
    return $script:KrLunarCalendar.ToDateTime($lunarYear, $monthIndex, [int]$lunarDay, 0, 0, 0, 0, $script:KrLunarEra).Date
}

function Get-NextObservedHoliday([datetime]$anchorDate, [hashtable]$holidays) {
    $cursor = $anchorDate.Date.AddDays(1)
    while ($true) {
        $key = $cursor.ToString("yyyy-MM-dd")
        $isWeekend = Test-IsWeekend $cursor
        if ((-not $isWeekend) -and (-not $holidays.ContainsKey($key))) {
            return $cursor
        }
        $cursor = $cursor.AddDays(1)
    }
}

function Get-KoreanHolidayTable([int]$year) {
    $cacheKey = [string]$year
    if ($script:KrHolidayCache.ContainsKey($cacheKey)) {
        return $script:KrHolidayCache[$cacheKey]
    }

    $holidays = @{}
    $solarDates = @(
        (Get-Date -Year $year -Month 1 -Day 1),
        (Get-Date -Year $year -Month 3 -Day 1),
        (Get-Date -Year $year -Month 5 -Day 5),
        (Get-Date -Year $year -Month 6 -Day 6),
        (Get-Date -Year $year -Month 8 -Day 15),
        (Get-Date -Year $year -Month 10 -Day 3),
        (Get-Date -Year $year -Month 10 -Day 9),
        (Get-Date -Year $year -Month 12 -Day 25)
    )
    foreach ($date in $solarDates) { Add-HolidayDate $holidays $date }

    $seollal = Convert-KoreanLunarToSolar $year 1 1
    $seollalSpan = @($seollal.AddDays(-1), $seollal, $seollal.AddDays(1))
    foreach ($date in $seollalSpan) { Add-HolidayDate $holidays $date }

    $buddha = Convert-KoreanLunarToSolar $year 4 8
    Add-HolidayDate $holidays $buddha

    $chuseok = Convert-KoreanLunarToSolar $year 8 15
    $chuseokSpan = @($chuseok.AddDays(-1), $chuseok, $chuseok.AddDays(1))
    foreach ($date in $chuseokSpan) { Add-HolidayDate $holidays $date }

    $observedSingles = @(
        (Get-Date -Year $year -Month 3 -Day 1),
        (Get-Date -Year $year -Month 5 -Day 5),
        $buddha,
        (Get-Date -Year $year -Month 8 -Day 15),
        (Get-Date -Year $year -Month 10 -Day 3),
        (Get-Date -Year $year -Month 10 -Day 9),
        (Get-Date -Year $year -Month 12 -Day 25)
    )
    foreach ($date in $observedSingles) {
        $key = $date.ToString("yyyy-MM-dd")
        $needsObserved = (
            $date.DayOfWeek -eq [System.DayOfWeek]::Saturday -or
            $date.DayOfWeek -eq [System.DayOfWeek]::Sunday -or
            [int]$holidays[$key] -gt 1
        )
        if ($needsObserved) {
            $observed = Get-NextObservedHoliday $date $holidays
            Add-HolidayDate $holidays $observed
        }
    }

    foreach ($group in @($seollalSpan, $chuseokSpan)) {
        $needsObserved = $false
        foreach ($date in $group) {
            $key = $date.ToString("yyyy-MM-dd")
            if ($date.DayOfWeek -eq [System.DayOfWeek]::Sunday -or [int]$holidays[$key] -gt 1) {
                $needsObserved = $true
                break
            }
        }
        if ($needsObserved) {
            $anchor = ($group | Sort-Object | Select-Object -Last 1)
            $observed = Get-NextObservedHoliday $anchor $holidays
            Add-HolidayDate $holidays $observed
        }
    }

    $script:KrHolidayCache[$cacheKey] = $holidays
    return $holidays
}

function Test-KoreanHoliday([datetime]$ts) {
    $holidays = Get-KoreanHolidayTable $ts.Year
    return $holidays.ContainsKey($ts.Date.ToString("yyyy-MM-dd"))
}

function Get-MemoCapacityMultiplier([datetime]$ts) {
    if (Test-IsWeekend $ts -or (Test-KoreanHoliday $ts)) {
        return 2
    }
    return 1
}

function Get-MemoDailyCap([datetime]$ts) {
    return 10 * (Get-MemoCapacityMultiplier $ts)
}

function Get-MemoIncrementalIntervalMinutes([datetime]$ts) {
    return 30
}

function Get-MemoIncrementalLimit([datetime]$ts) {
    return 1 * (Get-MemoCapacityMultiplier $ts)
}

function Get-MemoIncrementalDelaySec([datetime]$ts) {
    if (Test-IsWeekend $ts) { return 1.2 }
    return 2.0
}

function Get-TodayMemoFullTarget([datetime]$ts) {
    $win = Get-ActiveWindowInfo $ts
    return $ts.Date.AddHours([double][int]$win.MemoFullHour).AddMinutes([double][int]$win.MemoFullMinute)
}

function Test-AdminMemoFinalizeReady([string]$statusPath) {
    if (-not (Test-Path $statusPath)) {
        return $false
    }
    try {
        $raw = Get-Content -Path $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $false
    }
    if (-not $raw) {
        return $false
    }
    $complete = $false
    $remaining = 999999
    try { $complete = [bool]$raw.complete } catch { $complete = $false }
    try { $remaining = [int]$raw.remaining } catch { $remaining = 999999 }
    return ($complete -and $remaining -le 0)
}

function Invoke-AdminMemoFinalizeIfReady([string]$statusPath, [string]$repoCommand, [bool]$enabled) {
    if (-not $enabled) {
        return
    }
    if (-not (Test-AdminMemoFinalizeReady $statusPath)) {
        return
    }
    Write-Log 'admin memo finalize trigger: backlog complete'
    [void](Invoke-RepoCommand 'admin_memo_finalize' $repoCommand)
}

function Run-ListingWatchdog {
    $nextNowRun = Get-NextFixedSlotRun (Get-Date) @(12, 18)
    $nextPublishRun = (Get-Date).AddMinutes(8)
    $nextLocalSyncRun = (Get-Date).AddMinutes(10)
    $nowFailStreak = 0

    $cmdNowToSheet = 'scripts\run_startup_now_to_sheet.cmd'
    $cmdConfirmedPublish = (
        '{0} scripts\republish_from_audit.py --key-mode year --delay-sec 1.8 --request-buffer 120 --write-buffer 12 --state-file logs\republish_from_audit_state.json --skip-if-source-unchanged --yes >> logs\auto_confirmed_publish.log 2>&1' -f $pythonPrefix
    )
    $cmdLocalMnaSync = 'scripts\run_mna_state_local_sync.cmd >> logs\auto_mna_state_local_sync.log 2>&1'

    Write-Log 'listing watchdog loop started'
    Write-Log ('listing slots: 12:00, 18:00 / next={0}' -f $nextNowRun.ToString('s'))
    Write-Log 'listing policy: now scan + sheet sync always; site upload only when claim price exists; reconcile included'
    Write-Log ('confirmed publish interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 90 60), $nextPublishRun.ToString('s'))
    Write-Log ('local mna sync interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 90 120), $nextLocalSyncRun.ToString('s'))

    while ($true) {
        $now = Get-Date
        if (-not (Test-InActiveWindow $now)) {
            Save-State @{
                next_now_to_sheet = $nextNowRun.ToString('s')
                next_confirmed_publish = $nextPublishRun.ToString('s')
                next_local_mna_sync = $nextLocalSyncRun.ToString('s')
                now_fail_streak = [int]$nowFailStreak
            }
            Start-Sleep -Seconds $loopSleepSeconds
            continue
        }

        if ($now -ge $nextNowRun) {
            Write-Log ('listing fixed slot trigger={0}' -f $nextNowRun.ToString('HH:mm'))
            $rc = Invoke-RepoSiteWriteCommand 'listing_now_to_sheet' $cmdNowToSheet
            if ($rc -eq 0) { $nowFailStreak = 0 } else { $nowFailStreak += 1 }
            $nextNowRun = Get-NextFixedSlotRun ((Get-Date).AddMinutes(1)) @(12, 18)
            Write-Log ('listing next slot={0} fail_streak={1}' -f $nextNowRun.ToString('s'), [int]$nowFailStreak)
        }

        $now = Get-Date
        if ($now -ge $nextPublishRun) {
            [void](Invoke-RepoSiteWriteCommand 'listing_confirmed_publish' $cmdConfirmedPublish)
            $nextPublishRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 90 60))
        }

        $now = Get-Date
        if ($now -ge $nextLocalSyncRun) {
            [void](Invoke-RepoCommand 'listing_local_mna_sync' $cmdLocalMnaSync)
            $nextLocalSyncRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 90 120))
        }

        Save-State @{
            next_now_to_sheet = $nextNowRun.ToString('s')
            next_confirmed_publish = $nextPublishRun.ToString('s')
            next_local_mna_sync = $nextLocalSyncRun.ToString('s')
            now_fail_streak = [int]$nowFailStreak
        }
        Start-Sleep -Seconds $loopSleepSeconds
    }
}

function Run-NoticeWatchdog {
    $nextNoticeRun = (Get-Date).AddMinutes(20)
    $cmdNoticeArchive = 'scripts\run_startup_notice_archive.cmd'

    Write-Log 'monthly recommend watchdog loop started'
    Write-Log ('monthly recommend interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 180 120), $nextNoticeRun.ToString('s'))
    Write-Log 'monthly recommend policy: dedicated monthly recommendation notice pipeline only; isolated from monthly report and admin memo writes'

    while ($true) {
        $now = Get-Date
        if (-not (Test-InActiveWindow $now)) {
            Save-State @{ next_notice_archive = $nextNoticeRun.ToString('s') }
            Start-Sleep -Seconds $loopSleepSeconds
            continue
        }

        if ($now -ge $nextNoticeRun) {
            [void](Invoke-RepoSiteWriteCommand 'notice_archive_refresh' $cmdNoticeArchive)
            $nextNoticeRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 180 120))
        }

        Save-State @{ next_notice_archive = $nextNoticeRun.ToString('s') }
        Start-Sleep -Seconds $loopSleepSeconds
    }
}

function Run-MonthlyReportWatchdog {
    $nextMonthlyReportRun = (Get-Date).AddMinutes(30)
    $cmdMonthlyReport = 'scripts\run_startup_monthly_market_report.cmd'

    Write-Log 'monthly report watchdog loop started'
    Write-Log ('monthly report interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 360 240), $nextMonthlyReportRun.ToString('s'))
    Write-Log 'monthly report policy: use existing build/review/publish pipeline; isolated from monthly recommend and admin memo writes'

    while ($true) {
        $now = Get-Date
        if (-not (Test-InActiveWindow $now)) {
            Save-State @{ next_monthly_market_report = $nextMonthlyReportRun.ToString('s') }
            Start-Sleep -Seconds $loopSleepSeconds
            continue
        }

        if ($now -ge $nextMonthlyReportRun) {
            [void](Invoke-RepoSiteWriteCommand 'monthly_market_report_refresh' $cmdMonthlyReport)
            $nextMonthlyReportRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 360 240))
        }

        Save-State @{ next_monthly_market_report = $nextMonthlyReportRun.ToString('s') }
        Start-Sleep -Seconds $loopSleepSeconds
    }
}

function Run-AdminMemoWatchdog {
    $state = Load-State
    $nextMemoIncrementalRun = (Get-Date).AddMinutes(12)
    $lastMemoFullDate = ''
    $memoDailyDate = (Get-Date).ToString('yyyy-MM-dd')
    $memoDailyCount = 0
    if ($state) {
        try { if ($state.last_admin_memo_full_date) { $lastMemoFullDate = [string]$state.last_admin_memo_full_date } } catch {}
        try { if ($state.admin_memo_daily_date) { $memoDailyDate = [string]$state.admin_memo_daily_date } } catch {}
        try { $memoDailyCount = [int]$state.admin_memo_daily_count } catch { $memoDailyCount = 0 }
    }

    $cmdMemoFull = (
        '{0} ..\ALL\all.py --fix-admin-memo --fix-admin-memo-all --fix-admin-memo-pages 0 --fix-admin-memo-limit 0 --fix-admin-memo-delay-sec 1.2 --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 --fix-admin-memo-state-file logs/admin_memo_sync_state.json --confirm-bulk YES >> logs\auto_admin_memo_sync.log 2>&1' -f $pythonPrefix
    )
    $adminMemoStatusPath = Join-Path $logsDir 'admin_memo_sync_status.json'
    $adminMemoOutputDir = Join-Path ([Environment]::GetFolderPath('Desktop')) ([string]([char]99)+[char]108+[char]105+[char]54617+[char]49845)
    $cmdAdminMemoFinalize = (
        '{0} scripts\admin_memo_compact_finalize.py --state-file logs/admin_memo_sync_state.json --output-dir "{1}" --txt-name seoulmna_admin_memo_compact_latest.txt --marker-file logs/admin_memo_compact_finalize_marker.json --trim-log-path logs/auto_admin_memo_sync.log --trim-log-lines 200 >> logs\auto_admin_memo_finalize.log 2>&1' -f $pythonPrefix, $adminMemoOutputDir
    )
    $enableAdminMemoCompactFinalize = $false
    $enableMemoFull = $false

    Write-Log 'admin memo watchdog loop started'
    Write-Log ('admin memo incremental interval={0}m' -f [int](Get-MemoIncrementalIntervalMinutes (Get-Date)))
    Write-Log ('admin memo policy: per-run-limit={0}, daily-cap={1}, capacity-multiplier={2}' -f [int](Get-MemoIncrementalLimit (Get-Date)), [int](Get-MemoDailyCap (Get-Date)), [int](Get-MemoCapacityMultiplier (Get-Date)))
    Write-Log 'admin memo policy: dedicated worker; site writes serialized by shared lock'
    Write-Log ('admin memo full-run enabled={0} compact-finalize={1}' -f $enableMemoFull, $enableAdminMemoCompactFinalize)

    while ($true) {
        $now = Get-Date
        $todayMemoKey = $now.ToString('yyyy-MM-dd')
        $memoDailyCap = Get-MemoDailyCap $now
        if ($memoDailyDate -ne $todayMemoKey) {
            $memoDailyDate = $todayMemoKey
            $memoDailyCount = 0
            Write-Log ('admin memo daily counter reset: {0} (cap={1})' -f $memoDailyDate, [int]$memoDailyCap)
        }

        if (-not (Test-InActiveWindow $now)) {
            Save-State @{
                next_admin_memo_incremental = $nextMemoIncrementalRun.ToString('s')
                last_admin_memo_full_date = [string]$lastMemoFullDate
                admin_memo_daily_date = [string]$memoDailyDate
                admin_memo_daily_count = [int]$memoDailyCount
            }
            Start-Sleep -Seconds $loopSleepSeconds
            continue
        }

        if ($now -ge $nextMemoIncrementalRun) {
            if ($memoDailyCount -ge $memoDailyCap) {
                Write-Log ('admin memo incremental skip: daily cap reached ({0}/{1})' -f [int]$memoDailyCount, [int]$memoDailyCap)
            } else {
                $memoLimit = Get-MemoIncrementalLimit (Get-Date)
                $memoDelay = Get-MemoIncrementalDelaySec (Get-Date)
                $cmdMemoIncremental = (
                    '{0} ..\ALL\all.py --fix-admin-memo --fix-admin-memo-all --fix-admin-memo-pages 3 --fix-admin-memo-limit {1} --fix-admin-memo-delay-sec {2} --fix-admin-memo-request-buffer 120 --fix-admin-memo-write-buffer 12 --fix-admin-memo-state-file logs/admin_memo_sync_state.json --confirm-bulk YES >> logs\auto_admin_memo_sync.log 2>&1' -f $pythonPrefix, [int]$memoLimit, [double]$memoDelay
                )
                $memoRc = Invoke-RepoSiteWriteCommand 'admin_memo_incremental' $cmdMemoIncremental
                if ($memoRc -eq 0) {
                    Invoke-AdminMemoFinalizeIfReady $adminMemoStatusPath $cmdAdminMemoFinalize $enableAdminMemoCompactFinalize
                }
                $memoDailyCount += 1
                Write-Log ('admin memo incremental progress: {0}/{1} for {2}' -f [int]$memoDailyCount, [int]$memoDailyCap, $memoDailyDate)
            }
            $nextMemoIncrementalRun = (Get-Date).AddMinutes([int](Get-MemoIncrementalIntervalMinutes (Get-Date)))
        }

        $now = Get-Date
        $todayKey = $now.ToString('yyyy-MM-dd')
        $memoFullTarget = Get-TodayMemoFullTarget $now
        if ($enableMemoFull -and $lastMemoFullDate -ne $todayKey -and $now -ge $memoFullTarget) {
            $fullRc = Invoke-RepoSiteWriteCommand 'admin_memo_full' $cmdMemoFull
            if ($fullRc -eq 0) {
                $lastMemoFullDate = $todayKey
                Invoke-AdminMemoFinalizeIfReady $adminMemoStatusPath $cmdAdminMemoFinalize $enableAdminMemoCompactFinalize
            }
        }

        Save-State @{
            next_admin_memo_incremental = $nextMemoIncrementalRun.ToString('s')
            last_admin_memo_full_date = [string]$lastMemoFullDate
            admin_memo_daily_date = [string]$memoDailyDate
            admin_memo_daily_count = [int]$memoDailyCount
        }
        Start-Sleep -Seconds $loopSleepSeconds
    }
}

function Run-SiteHealthWatchdog {
    $nextQualityDailyRun = (Get-Date).AddMinutes(25)
    $nextSiteGuardRun = (Get-Date).AddMinutes(15)
    $nextRankMathDetailRun = (Get-Date).AddMinutes(28)
    $nextCxProbeRun = (Get-Date).AddMinutes(18)
    $nextDomSnapshotRun = (Get-Date).AddMinutes(22)
    $nextCxForceRecoverRun = (Get-Date).AddMinutes(14)
    $nextCxHealthDigestRun = (Get-Date).AddMinutes(16)
    $nextSustainabilityGuardRun = (Get-Date).AddMinutes(35)

    $cmdQualityDaily = 'scripts\run_quality_daily.cmd'
    $cmdDailyDashboard = (
        '{0} ..\ALL\all.py --daily-dashboard --dashboard-live --dashboard-days 7 >> logs\auto_daily_dashboard.log 2>&1' -f $pythonPrefix
    )
    $cmdSiteGuard = (
        '{0} scripts\optimize_wp_kr.py --report logs/wp_site_guard_latest.json --state-file logs/wp_site_guard_state.json --skip-if-ok-today >> logs\auto_wp_site_guard.log 2>&1' -f $pythonPrefix
    )
    $cmdRankMathDetail = (
        '{0} scripts\rankmath_detail_optimizer.py --report logs/rankmath_detail_opt_latest.json --state-file logs/rankmath_detail_state.json --skip-if-ok-today >> logs\auto_rankmath_detail.log 2>&1' -f $pythonPrefix
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
    $cmdSustainabilityGuard = (
        '{0} scripts\sustainability_guard.py --contract quality_contracts/sustainability_guard.contract.json --report logs/sustainability_guard_latest.json >> logs\auto_sustainability_guard.log 2>&1' -f $pythonPrefix
    )

    Write-Log 'site health watchdog loop started'
    Write-Log ('quality interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 240 120), $nextQualityDailyRun.ToString('s'))
    Write-Log ('wp site guard interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 120 90), $nextSiteGuardRun.ToString('s'))
    Write-Log ('rankmath detail interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 240 180), $nextRankMathDetailRun.ToString('s'))
    Write-Log ('site cx probe interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 90 60), $nextCxProbeRun.ToString('s'))
    Write-Log ('site dom snapshot interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 120 90), $nextDomSnapshotRun.ToString('s'))
    Write-Log ('site force recover interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 30 20), $nextCxForceRecoverRun.ToString('s'))
    Write-Log ('site health digest interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 180 120), $nextCxHealthDigestRun.ToString('s'))
    Write-Log ('sustainability guard interval={0}m / next={1}' -f [int](Get-WeekendAdjustedInterval (Get-Date) 480 360), $nextSustainabilityGuardRun.ToString('s'))
    Write-Log 'site health policy: write-capable jobs use shared site-write lock; probes and reports stay isolated'

    while ($true) {
        $now = Get-Date
        if (-not (Test-InActiveWindow $now)) {
            Save-State @{
                next_quality_daily = $nextQualityDailyRun.ToString('s')
                next_wp_site_guard = $nextSiteGuardRun.ToString('s')
                next_rankmath_detail = $nextRankMathDetailRun.ToString('s')
                next_site_cx_probe = $nextCxProbeRun.ToString('s')
                next_site_dom_snapshot = $nextDomSnapshotRun.ToString('s')
                next_site_cx_force_recover = $nextCxForceRecoverRun.ToString('s')
                next_site_cx_health_digest = $nextCxHealthDigestRun.ToString('s')
                next_sustainability_guard = $nextSustainabilityGuardRun.ToString('s')
            }
            Start-Sleep -Seconds $loopSleepSeconds
            continue
        }

        if ($now -ge $nextQualityDailyRun) {
            [void](Invoke-RepoCommand 'site_quality_daily' $cmdQualityDaily)
            [void](Invoke-RepoCommand 'site_daily_dashboard' $cmdDailyDashboard)
            $nextQualityDailyRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 240 120))
        }

        $now = Get-Date
        if ($now -ge $nextSiteGuardRun) {
            [void](Invoke-RepoSiteWriteCommand 'site_wp_guard' $cmdSiteGuard)
            $nextSiteGuardRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 120 90))
        }

        $now = Get-Date
        if ($now -ge $nextRankMathDetailRun) {
            [void](Invoke-RepoSiteWriteCommand 'site_rankmath_detail' $cmdRankMathDetail)
            $nextRankMathDetailRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 240 180))
        }

        $now = Get-Date
        if ($now -ge $nextCxProbeRun) {
            [void](Invoke-RepoCommand 'site_cx_probe' $cmdCxProbe)
            [void](Invoke-RepoSiteWriteCommand 'site_cx_autoheal' $cmdCxAutoHeal)
            [void](Invoke-RepoCommand 'site_cx_health_rollup' $cmdCxHealthRollup)
            $nextCxProbeRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 90 60))
        }

        $now = Get-Date
        if ($now -ge $nextDomSnapshotRun) {
            [void](Invoke-RepoCommand 'site_dom_snapshot' $cmdDomSnapshot)
            [void](Invoke-RepoCommand 'site_cx_health_rollup' $cmdCxHealthRollup)
            $nextDomSnapshotRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 120 90))
        }

        $now = Get-Date
        if ($now -ge $nextCxForceRecoverRun) {
            [void](Invoke-RepoSiteWriteCommand 'site_cx_force_recover' $cmdCxForceRecover)
            $nextCxForceRecoverRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 30 20))
        }

        $now = Get-Date
        if ($now -ge $nextCxHealthDigestRun) {
            [void](Invoke-RepoCommand 'site_cx_health_digest' $cmdCxHealthDigest)
            $nextCxHealthDigestRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 180 120))
        }

        $now = Get-Date
        if ($now -ge $nextSustainabilityGuardRun) {
            [void](Invoke-RepoCommand 'site_sustainability_guard' $cmdSustainabilityGuard)
            $nextSustainabilityGuardRun = (Get-Date).AddMinutes([int](Get-WeekendAdjustedInterval (Get-Date) 480 360))
        }

        Save-State @{
            next_quality_daily = $nextQualityDailyRun.ToString('s')
            next_wp_site_guard = $nextSiteGuardRun.ToString('s')
            next_rankmath_detail = $nextRankMathDetailRun.ToString('s')
            next_site_cx_probe = $nextCxProbeRun.ToString('s')
            next_site_dom_snapshot = $nextDomSnapshotRun.ToString('s')
            next_site_cx_force_recover = $nextCxForceRecoverRun.ToString('s')
            next_site_cx_health_digest = $nextCxHealthDigestRun.ToString('s')
            next_sustainability_guard = $nextSustainabilityGuardRun.ToString('s')
        }
        Start-Sleep -Seconds $loopSleepSeconds
    }
}

function Run-PermitWatchdog {
    $nextPermitCollectRun = (Get-Date).AddMinutes(40)
    $cmdPermitCollect = (
        '{0} scripts\collect_kr_permit_industries.py --output config/kr_permit_industries_localdata.json >> logs\auto_permit_collect.log 2>&1' -f $pythonPrefix
    )

    Write-Log 'permit watchdog loop started'
    Write-Log ('permit collect interval={0}m / next={1}' -f 1440, $nextPermitCollectRun.ToString('s'))
    Write-Log 'permit policy: split out from co.kr site jobs to avoid operator confusion'

    while ($true) {
        $now = Get-Date
        if (-not (Test-InActiveWindow $now)) {
            Save-State @{ next_permit_collect = $nextPermitCollectRun.ToString('s') }
            Start-Sleep -Seconds $loopSleepSeconds
            continue
        }

        if ($now -ge $nextPermitCollectRun) {
            [void](Invoke-RepoCommand 'permit_collect' $cmdPermitCollect)
            $nextPermitCollectRun = (Get-Date).AddMinutes(1440)
        }

        Save-State @{ next_permit_collect = $nextPermitCollectRun.ToString('s') }
        Start-Sleep -Seconds $loopSleepSeconds
    }
}

if ($StartupDelaySec -gt 0) {
    Start-Sleep -Seconds ([int]$StartupDelaySec)
}

$bootWindow = Get-ActiveWindowInfo (Get-Date)
Write-Log ('worker start profile={0} active_window={1} start={2:00}:00 end={3:00}:00' -f $Profile, $bootWindow.Label, [int]$bootWindow.StartHour, [int]$bootWindow.EndHour)

switch ($Profile) {
    'listing' { Run-ListingWatchdog }
    'monthly_recommend' { Run-NoticeWatchdog }
    'monthly_report' { Run-MonthlyReportWatchdog }
    'admin_memo' { Run-AdminMemoWatchdog }
    'site_health' { Run-SiteHealthWatchdog }
    'permit' { Run-PermitWatchdog }
    default {
        Write-Log ('unknown profile={0}' -f $Profile)
        exit 1
    }
}
