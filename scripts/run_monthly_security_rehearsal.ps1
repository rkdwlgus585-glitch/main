param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = [System.IO.Path]::GetFullPath([string]$RepoRoot)

$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
$logFile = Join-Path $logsDir "monthly_security_rehearsal_task.log"

function Write-Log([string]$message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $logFile -Encoding UTF8 -Value ("[{0}] {1}" -f $ts, $message)
}

function Resolve-Python() {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return "py -3" }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return "python" }
    return ""
}

Write-Log "RUN monthly security rehearsal"
$pyCmd = Resolve-Python
if (-not $pyCmd) {
    Write-Log "FAIL python runtime not found"
    exit 1
}

$exitCode = 0
try {
    Set-Location -LiteralPath $RepoRoot
    if ($pyCmd -eq "py -3") {
        & py -3 "scripts/monthly_security_rehearsal.py"
    } else {
        & python "scripts/monthly_security_rehearsal.py"
    }
    $exitCode = $LASTEXITCODE
} catch {
    Write-Log ("FAIL exception: {0}" -f $_.Exception.Message)
    $exitCode = 1
}

Write-Log ("DONE monthly security rehearsal rc={0}" -f $exitCode)
exit $exitCode
