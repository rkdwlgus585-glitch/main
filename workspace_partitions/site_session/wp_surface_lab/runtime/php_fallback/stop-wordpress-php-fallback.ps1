$ErrorActionPreference = 'SilentlyContinue'
$pidFile = Join-Path $PSScriptRoot 'php-site.pid'
if (Test-Path $pidFile) {
  $pid = Get-Content $pidFile -Raw
  if ($pid) { Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue }
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
