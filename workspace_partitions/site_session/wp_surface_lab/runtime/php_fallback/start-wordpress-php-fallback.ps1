$ErrorActionPreference = 'Stop'
$php = 'C:/Users/rkdwl/Desktop/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/php/php.exe'
$ini = 'C:/Users/rkdwl/Desktop/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/php/php.ini'
$site = 'C:/Users/rkdwl/Desktop/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/site'
$router = 'C:/Users/rkdwl/Desktop/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/site/router.php'
$pidFile = 'C:/Users/rkdwl/Desktop/auto/workspace_partitions/site_session/wp_surface_lab/runtime/php_fallback/php-site.pid'
$proc = Start-Process -FilePath $php -ArgumentList @('-c', $ini, '-S', '127.0.0.1:18081', $router) -WorkingDirectory $site -PassThru
$proc.Id | Set-Content -Path $pidFile -Encoding ASCII
Write-Output $proc.Id
