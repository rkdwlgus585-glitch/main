$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$php = Join-Path $base 'php\php.exe'
$ini = Join-Path $base 'php\php.ini'
$site = Join-Path $base 'site'
$router = Join-Path $base 'router.php'
$pidFile = Join-Path $base 'php-site.pid'
$proc = Start-Process -FilePath $php -ArgumentList @('-c', $ini, '-q', '-S', '127.0.0.1:18081', $router) -WorkingDirectory $site -PassThru
$proc.Id | Set-Content -Path $pidFile -Encoding ASCII
Write-Output $proc.Id
