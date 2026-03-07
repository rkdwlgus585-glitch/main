param(
    [int]$IterationsPerCycle = 4000,
    [double]$SleepSec = 0.4,
    [int]$Seed = 20260304,
    [string]$Profile = "full-spectrum"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$sleepValue = [double]$SleepSec
if ($sleepValue -lt 0) {
    $sleepValue = 0.0
}

$procState = Join-Path $logsDir "yangdo_internal_fuzz_process.json"
if (Test-Path $procState) {
    try {
        $state = Get-Content $procState -Raw | ConvertFrom-Json
        if ($state -and $state.pid) {
            $running = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
            if ($running) {
                Write-Host "already_running pid=$($running.Id)"
                exit 0
            }
        }
    } catch {
    }
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$stdout = Join-Path $logsDir ("yangdo_internal_fuzz_stdout_{0}.log" -f $ts)
$stderr = Join-Path $logsDir ("yangdo_internal_fuzz_stderr_{0}.log" -f $ts)
$args = @(
    "-3",
    "scripts/run_yangdo_internal_fuzz_loop.py",
    "--forever",
    "--iterations-per-cycle", [string]([Math]::Max(1000, $IterationsPerCycle)),
    "--sleep-sec", [string]$sleepValue,
    "--seed", [string]$Seed,
    "--profile", [string]$Profile,
    "--report", "logs/yangdo_internal_fuzz_latest.json",
    "--jsonl", "logs/yangdo_internal_fuzz_cycles.jsonl"
)

$proc = Start-Process -FilePath "py" -ArgumentList $args -PassThru -WindowStyle Hidden -WorkingDirectory $repoRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$payload = @{
    pid = $proc.Id
    started = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    stdout = $stdout
    stderr = $stderr
    iterations_per_cycle = [Math]::Max(1000, $IterationsPerCycle)
    sleep_sec = $sleepValue
    profile = [string]$Profile
}
$payload | ConvertTo-Json -Depth 3 | Set-Content -Path $procState -Encoding UTF8
Write-Host ("started pid={0}" -f $proc.Id)
