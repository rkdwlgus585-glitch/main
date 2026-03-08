$ErrorActionPreference = 'Stop'
$php = 'H:/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/php/php.exe'
$ini = 'H:/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/php/php.ini'
$root = Split-Path -Parent $PSScriptRoot
$site = Join-Path $root 'site'
$router = 'H:/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/router.php'
$proc = Start-Process -FilePath $php -ArgumentList @('-c', $ini, '-q', '-S', '127.0.0.1:18081', $router) -WorkingDirectory $site -PassThru
$proc.Id | Set-Content -Path (Join-Path $PSScriptRoot 'php-server.pid') -Encoding ASCII
Write-Output $proc.Id
