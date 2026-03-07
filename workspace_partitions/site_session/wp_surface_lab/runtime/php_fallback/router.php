<?php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$full = __DIR__ . $path;
if ($path !== '/' && file_exists($full) && !is_dir($full)) {
    return false;
}
require __DIR__ . '/index.php';
