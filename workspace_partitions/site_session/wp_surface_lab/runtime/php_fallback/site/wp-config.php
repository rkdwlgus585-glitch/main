<?php
define('DB_NAME', 'seoulmna_sqlite');
define('DB_USER', 'root');
define('DB_PASSWORD', '');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');

define('AUTH_KEY', 'seoulmna-lab-auth-key');
define('SECURE_AUTH_KEY', 'seoulmna-lab-secure-auth-key');
define('LOGGED_IN_KEY', 'seoulmna-lab-logged-in-key');
define('NONCE_KEY', 'seoulmna-lab-nonce-key');
define('AUTH_SALT', 'seoulmna-lab-auth-salt');
define('SECURE_AUTH_SALT', 'seoulmna-lab-secure-auth-salt');
define('LOGGED_IN_SALT', 'seoulmna-lab-logged-in-salt');
define('NONCE_SALT', 'seoulmna-lab-nonce-salt');

$table_prefix = 'wp_';

define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
define('WP_HOME', 'http://127.0.0.1:18081');
define('WP_SITEURL', 'http://127.0.0.1:18081');
define('DISALLOW_FILE_EDIT', true);
define('AUTOMATIC_UPDATER_DISABLED', true);

if ( ! defined('ABSPATH') ) {
    define('ABSPATH', __DIR__ . '/');
}

require_once ABSPATH . 'wp-settings.php';
