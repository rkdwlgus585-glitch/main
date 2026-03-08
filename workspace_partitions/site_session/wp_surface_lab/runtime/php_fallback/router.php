<?php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$siteRoot = realpath(getcwd()) ?: getcwd();
$file = $siteRoot . $path;
if ($path !== '/' && file_exists($file) && !is_dir($file)) {
    return false;
}
require $siteRoot . '/index.php';
