param(
    [string]$Repo = "",
    [int]$Cycles = 2,
    [int]$IterationsPerCycle = 6000,
    [double]$SleepSec = 0.1,
    [int]$Seed = 20260304,
    [string]$SheetName = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI not found. Install GitHub CLI first."
}

gh auth status | Out-Null

if (-not $Repo) {
    # Try to infer from current git remote.
    $origin = (git remote get-url origin 2>$null)
    if ($origin) {
        if ($origin -match "github\.com[:/](.+?)(\.git)?$") {
            $Repo = $Matches[1]
        }
    }
}
if (-not $Repo) {
    throw "Cannot infer repository. Pass -Repo owner/repo."
}

$args = @(
    "workflow", "run", "yangdo-internal-fuzz-remote.yml",
    "--repo", $Repo,
    "-f", ("cycles={0}" -f [Math]::Max(1, $Cycles)),
    "-f", ("iterations_per_cycle={0}" -f [Math]::Max(100, $IterationsPerCycle)),
    "-f", ("sleep_sec={0}" -f [Math]::Max(0, $SleepSec)),
    "-f", ("seed={0}" -f $Seed)
)
if ($SheetName) {
    $args += @("-f", ("sheet_name={0}" -f $SheetName))
}

gh @args
Write-Host ("triggered remote fuzz workflow on {0}" -f $Repo)
