$ErrorActionPreference = 'SilentlyContinue'
$pidFile = 'C:/Users/rkdwl/Desktop/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/php-site.pid'
if (Test-Path $pidFile) {
  $pid = Get-Content $pidFile -Raw
  if ($pid) { Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue }
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}
