$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'php-site.pid'
if (-not (Test-Path $pidFile)) { exit 0 }
$targetPid = (Get-Content $pidFile -Raw).Trim()
if ($targetPid -match '^[0-9]+$') {
  try { taskkill /PID $targetPid /T /F | Out-Null } catch { }
  Start-Sleep -Milliseconds 800
}
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
exit 0
