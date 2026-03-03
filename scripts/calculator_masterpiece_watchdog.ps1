# Calculator runtime watchdog:
# - Runs until next morning (default 09:00 local)
# - Verifies runtime health
# - Auto-heals by redeploying KR + CO bridge if checks fail
param(
    [string]$RepoRoot = "",
    [string]$EndAt = "",
    [int]$IntervalSec = 900,
    [int]$StartupDelaySec = 0
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)
$krOnlyLockPath = Join-Path $RepoRoot "logs\kr_only_mode.lock"
$krOnlyMode = Test-Path $krOnlyLockPath

if ($krOnlyMode) {
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
$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$logPath = Join-Path $logsDir "calculator_masterpiece_watchdog.log"
$statePath = Join-Path $logsDir "calculator_masterpiece_watchdog_state.json"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logPath -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Save-State([string]$status, [datetime]$nextRun, [int]$failStreak, [string]$lastAction) {
    $payload = @{
        updated_at = (Get-Date).ToString("s")
        status = [string]$status
        next_run = $nextRun.ToString("s")
        fail_streak = [int]$failStreak
        last_action = [string]$lastAction
    }
    try {
        ($payload | ConvertTo-Json -Depth 4) | Set-Content -Path $statePath -Encoding UTF8
    } catch {
    }
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

function Resolve-EndTime([string]$endAtRaw) {
    $now = Get-Date
    if ([string]::IsNullOrWhiteSpace($endAtRaw)) {
        # default: next 09:00 local
        $target = $now.Date.AddHours(9)
        if ($now -ge $target) {
            $target = $target.AddDays(1)
        }
        return $target
    }

    # Accept "HH:mm" or absolute parseable datetime.
    $parsed = $null
    if ([datetime]::TryParse($endAtRaw, [ref]$parsed)) {
        if ($parsed -le $now) {
            return $parsed.AddDays(1)
        }
        return $parsed
    }

    return $now.Date.AddDays(1).AddHours(9)
}

function Send-Discord([string]$text) {
    $envPath = Join-Path $RepoRoot ".env"
    if (-not (Test-Path $envPath)) { return }
    $webhook = ""
    try {
        $lines = Get-Content -Path $envPath -Encoding UTF8
        foreach ($ln in $lines) {
            $s = [string]$ln
            if ($s.StartsWith("DISCORD_WEBHOOK_URL=")) {
                $webhook = $s.Substring("DISCORD_WEBHOOK_URL=".Length).Trim()
                break
            }
        }
    } catch {
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) { return }

    try {
        $payload = @{ content = $text } | ConvertTo-Json -Depth 3
        Invoke-RestMethod -Method Post -Uri $webhook -ContentType "application/json" -Body $payload | Out-Null
    } catch {
    }
}

$endTime = Resolve-EndTime $EndAt
$interval = [Math]::Max(120, [int]$IntervalSec)
$failStreak = 0
$nextRun = Get-Date

$cmdVerify = (
    '{0} scripts\verify_calculator_runtime.py --allow-no-browser --report logs\verify_calculator_runtime_latest.json' -f $pythonPrefix
)
$cmdHealKr = (
    '{0} scripts\deploy_yangdo_kr_banner_bridge.py --skip-co-publish --max-train-rows 260 --report logs\yangdo_kr_bridge_latest.json' -f $pythonPrefix
)
$cmdHealCo = (
    '{0} scripts\deploy_b_plan_masterpiece.py --skip-gas-bundle --report logs\b_plan_masterpiece_latest.json' -f $pythonPrefix
)

Write-Log ("calculator watchdog started, end_at={0}, interval={1}s" -f $endTime.ToString("s"), $interval)
if ($StartupDelaySec -gt 0) {
    Start-Sleep -Seconds ([int]$StartupDelaySec)
}

while ((Get-Date) -lt $endTime) {
    $now = Get-Date
    if ($now -lt $nextRun) {
        Save-State "sleep" $nextRun $failStreak ""
        Start-Sleep -Seconds 20
        continue
    }

    $rcVerify = Invoke-RepoCommand "calc_verify" $cmdVerify
    if ($rcVerify -eq 0) {
        $failStreak = 0
        $nextRun = (Get-Date).AddSeconds($interval)
        Save-State "healthy" $nextRun $failStreak "verify_ok"
        continue
    }

    $failStreak += 1
    Write-Log ("verify failed, fail_streak={0}; start auto-heal" -f $failStreak)
    Send-Discord ("[SeoulMNA Calc Watchdog] verify failed (streak={0}), auto-heal started." -f $failStreak)

    [void](Invoke-RepoCommand "heal_kr" $cmdHealKr)
    if (-not $krOnlyMode) {
        [void](Invoke-RepoCommand "heal_co" $cmdHealCo)
    }
    $rcReverify = Invoke-RepoCommand "calc_reverify" $cmdVerify

    if ($rcReverify -eq 0) {
        Write-Log "auto-heal success"
        Send-Discord "[SeoulMNA Calc Watchdog] auto-heal success."
        $failStreak = 0
        $nextRun = (Get-Date).AddSeconds($interval)
        Save-State "recovered" $nextRun $failStreak "auto_heal_success"
    } else {
        Write-Log "auto-heal failed"
        Send-Discord "[SeoulMNA Calc Watchdog] auto-heal failed. manual check needed."
        $nextRun = (Get-Date).AddMinutes(10)
        Save-State "degraded" $nextRun $failStreak "auto_heal_failed"
    }
}

Write-Log "calculator watchdog ended by schedule"
Save-State "ended" (Get-Date) $failStreak "schedule_end"
