param(
    [int]$YangdoIterationsPerCycle = 1500,
    [int]$PermitIterationsPerCycle = 3000,
    [double]$SleepSec = 0.4,
    [int]$YangdoSeed = 20260306,
    [int]$PermitSeed = 20260306
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$sleepValue = [double]$SleepSec
if ($sleepValue -lt 0) {
    $sleepValue = 0.0
}

function Start-NormalMarketFuzzProcess {
    param(
        [string]$Name,
        [string[]]$ArgumentList,
        [string]$StatePath
    )

    if (Test-Path $StatePath) {
        try {
            $state = Get-Content $StatePath -Raw | ConvertFrom-Json
            if ($state -and $state.pid) {
                $running = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
                if ($running) {
                    return @{
                        status = "already_running"
                        pid = $running.Id
                    }
                }
            }
        } catch {
        }
    }

    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdout = Join-Path $logsDir ("{0}_stdout_{1}.log" -f $Name, $ts)
    $stderr = Join-Path $logsDir ("{0}_stderr_{1}.log" -f $Name, $ts)
    $proc = Start-Process -FilePath "py" -ArgumentList $ArgumentList -PassThru -WindowStyle Hidden -WorkingDirectory $repoRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $payload = @{
        pid = $proc.Id
        started = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        stdout = $stdout
        stderr = $stderr
        args = $ArgumentList
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -Path $StatePath -Encoding UTF8
    return @{
        status = "started"
        pid = $proc.Id
    }
}

$yangdoState = Join-Path $logsDir "yangdo_internal_fuzz_normal_market_process.json"
$yangdoArgs = @(
    "-3",
    "scripts/run_yangdo_internal_fuzz_loop.py",
    "--forever",
    "--iterations-per-cycle", [string]([Math]::Max(1000, $YangdoIterationsPerCycle)),
    "--sleep-sec", [string]$sleepValue,
    "--seed", [string]$YangdoSeed,
    "--profile", "normal-market",
    "--report", "logs/yangdo_internal_fuzz_normal_market_latest.json",
    "--jsonl", "logs/yangdo_internal_fuzz_normal_market_cycles.jsonl"
)
$yangdo = Start-NormalMarketFuzzProcess -Name "yangdo_internal_fuzz_normal_market" -ArgumentList $yangdoArgs -StatePath $yangdoState

$permitState = Join-Path $logsDir "permit_diagnosis_input_fuzz_normal_market_process.json"
$permitArgs = @(
    "-3",
    "scripts/run_permit_diagnosis_input_fuzz.py",
    "--forever",
    "--iterations", [string]([Math]::Max(1000, $PermitIterationsPerCycle)),
    "--sleep-sec", [string]$sleepValue,
    "--seed", [string]$PermitSeed,
    "--profile", "normal-market",
    "--report", "logs/permit_diagnosis_input_fuzz_normal_market_latest.json",
    "--jsonl", "logs/permit_diagnosis_input_fuzz_normal_market_cycles.jsonl"
)
$permit = Start-NormalMarketFuzzProcess -Name "permit_diagnosis_input_fuzz_normal_market" -ArgumentList $permitArgs -StatePath $permitState

[pscustomobject]@{
    yangdo_status = $yangdo.status
    yangdo_pid = $yangdo.pid
    permit_status = $permit.status
    permit_pid = $permit.pid
} | ConvertTo-Json -Depth 3
