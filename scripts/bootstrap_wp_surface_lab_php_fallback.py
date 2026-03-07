#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab"
DEFAULT_WP_LAB = ROOT / "logs" / "wp_surface_lab_latest.json"
DEFAULT_PHP_RUNTIME = ROOT / "logs" / "wp_surface_lab_php_runtime_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copytree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _stop_process_from_pidfile(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    try:
        raw = pid_file.read_text(encoding="utf-8").strip()
    except Exception:
        raw = ""
    stopped = False
    if raw:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(int(raw)), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            stopped = True
        except Exception:
            stopped = False
    try:
        pid_file.unlink(missing_ok=True)
    except Exception:
        pass
    if stopped:
        time.sleep(1.0)
    return stopped


def _clear_directory(path: Path) -> None:
    if not path.exists():
        return
    for _ in range(3):
        try:
            shutil.rmtree(path)
            return
        except Exception:
            time.sleep(0.8)
    shutil.rmtree(path, ignore_errors=True)


def _preserve_directory(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return True


def _router_script() -> str:
    return """<?php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$file = __DIR__ . $path;
if ($path !== '/' && file_exists($file) && !is_dir($file)) {
    return false;
}
require __DIR__ . '/index.php';
"""


def _wp_config(site_url: str) -> str:
    salts = {
        "AUTH_KEY": "seoulmna-lab-auth-key",
        "SECURE_AUTH_KEY": "seoulmna-lab-secure-auth-key",
        "LOGGED_IN_KEY": "seoulmna-lab-logged-in-key",
        "NONCE_KEY": "seoulmna-lab-nonce-key",
        "AUTH_SALT": "seoulmna-lab-auth-salt",
        "SECURE_AUTH_SALT": "seoulmna-lab-secure-auth-salt",
        "LOGGED_IN_SALT": "seoulmna-lab-logged-in-salt",
        "NONCE_SALT": "seoulmna-lab-nonce-salt",
    }
    salt_lines = "\n".join([f"define('{key}', '{value}');" for key, value in salts.items()])
    return f"""<?php
define('DB_NAME', 'seoulmna_sqlite');
define('DB_USER', 'root');
define('DB_PASSWORD', '');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', '');

{salt_lines}

$table_prefix = 'wp_';

define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
define('WP_HOME', '{site_url}');
define('WP_SITEURL', '{site_url}');
define('DISALLOW_FILE_EDIT', true);
define('AUTOMATIC_UPDATER_DISABLED', true);

if ( ! defined('ABSPATH') ) {{
    define('ABSPATH', __DIR__ . '/');
}}

require_once ABSPATH . 'wp-settings.php';
"""


def _build_db_dropin(plugin_root: Path) -> str:
    template = (plugin_root / "db.copy").read_text(encoding="utf-8")
    return (
        template.replace("{SQLITE_IMPLEMENTATION_FOLDER_PATH}", plugin_root.as_posix())
        .replace("{SQLITE_PLUGIN}", "sqlite-database-integration/load.php")
    )


def build_wp_surface_lab_php_fallback(
    *,
    lab_root: Path,
    wp_lab_path: Path,
    php_runtime_path: Path,
) -> Dict[str, Any]:
    wp_lab = _load_json(wp_lab_path)
    php_runtime = _load_json(php_runtime_path)
    runtime_root = lab_root / "runtime" / "php_fallback"
    site_root = runtime_root / "site"
    preserve_root = runtime_root / "_preserve"
    staging_root = lab_root / "staging"
    wordpress_src = staging_root / "wordpress"
    wp_content_src = staging_root / "wp-content"
    php_paths = php_runtime.get("paths") if isinstance(php_runtime.get("paths"), dict) else {}
    php_runtime_root = Path(str(php_paths.get("runtime_root") or runtime_root))
    php_exe = Path(str(php_paths.get("php_executable") or php_runtime_root / "php" / "php.exe"))
    php_ini = Path(str(php_paths.get("php_ini") or php_runtime_root / "php" / "php.ini"))
    router_path = site_root / "router.php"
    start_script = runtime_root / "start-wordpress-php-fallback.ps1"
    stop_script = runtime_root / "stop-wordpress-php-fallback.ps1"
    pid_file = runtime_root / "php-site.pid"
    site_url = str((php_runtime.get("runtime") or {}).get("localhost_url") or "http://127.0.0.1:18081")
    preserved_database = False
    preserved_uploads = False

    current_database = site_root / "wp-content" / "database"
    current_uploads = site_root / "wp-content" / "uploads"
    preserved_database_path = preserve_root / "database"
    preserved_uploads_path = preserve_root / "uploads"
    if current_database.exists():
        preserved_database = _preserve_directory(current_database, preserved_database_path)
    if current_uploads.exists():
        preserved_uploads = _preserve_directory(current_uploads, preserved_uploads_path)

    runtime_stopped = _stop_process_from_pidfile(pid_file)
    _clear_directory(site_root)

    if wordpress_src.exists():
        _copytree(wordpress_src, site_root)
    if wp_content_src.exists():
        target_wp_content = site_root / "wp-content"
        _copytree(wp_content_src, target_wp_content)

    (site_root / "wp-content" / "database").mkdir(parents=True, exist_ok=True)
    (site_root / "wp-content" / "uploads").mkdir(parents=True, exist_ok=True)
    if preserved_database_path.exists():
        restored_database = site_root / "wp-content" / "database"
        if restored_database.exists():
            shutil.rmtree(restored_database)
        shutil.copytree(preserved_database_path, restored_database)
    if preserved_uploads_path.exists():
        restored_uploads = site_root / "wp-content" / "uploads"
        if restored_uploads.exists():
            shutil.rmtree(restored_uploads)
        shutil.copytree(preserved_uploads_path, restored_uploads)

    sqlite_plugin_root = site_root / "wp-content" / "plugins" / "sqlite-database-integration"
    sqlite_plugin_ready = sqlite_plugin_root.is_dir() and (sqlite_plugin_root / "db.copy").is_file()
    db_dropin_path = site_root / "wp-content" / "db.php"
    if sqlite_plugin_ready:
        _write_text(db_dropin_path, _build_db_dropin(sqlite_plugin_root))

    wp_config_path = site_root / "wp-config.php"
    _write_text(wp_config_path, _wp_config(site_url))
    _write_text(router_path, _router_script())

    _write_text(
        start_script,
        "\n".join(
            [
                "$ErrorActionPreference = 'Stop'",
                f"$php = '{php_exe.as_posix()}'",
                f"$ini = '{php_ini.as_posix()}'",
                f"$site = '{site_root.as_posix()}'",
                f"$router = '{router_path.as_posix()}'",
                f"$pidFile = '{pid_file.as_posix()}'",
                "$proc = Start-Process -FilePath $php -ArgumentList @('-c', $ini, '-S', '127.0.0.1:18081', $router) -WorkingDirectory $site -PassThru",
                "$proc.Id | Set-Content -Path $pidFile -Encoding ASCII",
                "Write-Output $proc.Id",
                "",
            ]
        ),
    )
    _write_text(
        stop_script,
        "\n".join(
            [
                "$ErrorActionPreference = 'SilentlyContinue'",
                f"$pidFile = '{pid_file.as_posix()}'",
                "if (Test-Path $pidFile) {",
                "  $pid = Get-Content $pidFile -Raw",
                "  if ($pid) { Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue }",
                "  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue",
                "}",
                "",
            ]
        ),
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "site_url": site_url,
        "paths": {
            "site_root": str(site_root.resolve()),
            "wp_config": str(wp_config_path.resolve()),
            "db_dropin": str(db_dropin_path.resolve()),
            "router": str(router_path.resolve()),
            "start_script": str(start_script.resolve()),
            "stop_script": str(stop_script.resolve()),
            "php_executable": str(php_exe.resolve()) if php_exe.exists() else str(php_exe),
            "php_ini": str(php_ini.resolve()) if php_ini.exists() else str(php_ini),
        },
        "summary": {
            "staging_ready_count": int((wp_lab.get("summary") or {}).get("staging_ready_count") or 0),
            "php_runtime_ready": bool((php_runtime.get("summary") or {}).get("runtime_ready")),
            "sqlite_plugin_ready": sqlite_plugin_ready,
            "db_dropin_ready": db_dropin_path.is_file(),
            "site_root_ready": site_root.is_dir(),
            "preserved_database": preserved_database,
            "preserved_uploads": preserved_uploads,
            "runtime_stopped_before_bootstrap": runtime_stopped,
            "bootstrap_ready": bool((php_runtime.get("summary") or {}).get("runtime_ready")) and sqlite_plugin_ready and db_dropin_path.is_file(),
        },
        "commands": {
            "start_server": f'powershell -ExecutionPolicy Bypass -File "{start_script}"',
            "stop_server": f'powershell -ExecutionPolicy Bypass -File "{stop_script}"',
            "install_url": f"{site_url}/wp-admin/install.php",
            "admin_url": f"{site_url}/wp-admin/",
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    commands = payload.get("commands") if isinstance(payload.get("commands"), dict) else {}
    lines = [
        "# WordPress Surface Lab PHP Fallback Bootstrap",
        "",
        f"- site_root_ready: {summary.get('site_root_ready')}",
        f"- php_runtime_ready: {summary.get('php_runtime_ready')}",
        f"- sqlite_plugin_ready: {summary.get('sqlite_plugin_ready')}",
        f"- db_dropin_ready: {summary.get('db_dropin_ready')}",
        f"- bootstrap_ready: {summary.get('bootstrap_ready')}",
        f"- site_url: {payload.get('site_url') or '(none)'}",
        "",
        "## Commands",
    ]
    for key, value in commands.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose a Docker-free WordPress site root using the official SQLite integration plugin and the downloaded PHP runtime.")
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT)
    parser.add_argument("--wp-lab", type=Path, default=DEFAULT_WP_LAB)
    parser.add_argument("--php-runtime", type=Path, default=DEFAULT_PHP_RUNTIME)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_php_fallback_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab_php_fallback(
        lab_root=args.lab_root,
        wp_lab_path=args.wp_lab,
        php_runtime_path=args.php_runtime,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("site_root_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
