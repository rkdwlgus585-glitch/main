#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab"
DEFAULT_WP_LAB = ROOT / "logs" / "wp_surface_lab_latest.json"
DEFAULT_WP_ASSETS = ROOT / "logs" / "wp_platform_assets_latest.json"


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


def build_wp_surface_lab_runtime(
    *,
    lab_root: Path,
    wp_lab_path: Path,
    wp_assets_path: Path,
) -> Dict[str, Any]:
    wp_lab = _load_json(wp_lab_path)
    wp_assets = _load_json(wp_assets_path)

    runtime_root = lab_root / "runtime"
    data_root = runtime_root / "data"
    (data_root / "db").mkdir(parents=True, exist_ok=True)
    (data_root / "logs").mkdir(parents=True, exist_ok=True)

    for marker in (
        data_root / "db" / ".gitkeep",
        data_root / "logs" / ".gitkeep",
    ):
        if not marker.exists():
            marker.write_text("", encoding="utf-8")

    env_example = """# Local-only WordPress surface lab environment
# Docker runtime defaults use 18080.
# PHP fallback defaults use 18081 and do not require Docker.
# WP_HTTP_PORT / WP_SITE_URL are kept for docker-compose compatibility.
WP_HTTP_PORT=18080
WP_SITE_URL=http://127.0.0.1:18080
WP_PHP_FALLBACK_PORT=18081
WP_PHP_FALLBACK_SITE_URL=http://127.0.0.1:18081
WP_ACTIVE_RUNTIME=php_fallback
WP_SITE_TITLE=SeoulMNA Platform Lab
WP_ADMIN_USER=admin
WP_ADMIN_PASSWORD=change-me-before-sharing
WP_ADMIN_EMAIL=lab@seoulmna.local
WP_DB_NAME=seoulmna_lab
WP_DB_USER=seoulmna
WP_DB_PASSWORD=change-me-db-password
WP_DB_ROOT_PASSWORD=change-me-root-password
"""
    env_local = """WP_HTTP_PORT=18080
WP_SITE_URL=http://127.0.0.1:18080
WP_PHP_FALLBACK_PORT=18081
WP_PHP_FALLBACK_SITE_URL=http://127.0.0.1:18081
WP_ACTIVE_RUNTIME=php_fallback
WP_SITE_TITLE=SeoulMNA Platform Lab
WP_ADMIN_USER=admin
WP_ADMIN_PASSWORD=change-me-before-sharing
WP_ADMIN_EMAIL=lab@seoulmna.local
WP_DB_NAME=seoulmna_lab
WP_DB_USER=seoulmna
WP_DB_PASSWORD=change-me-db-password
WP_DB_ROOT_PASSWORD=change-me-root-password
"""
    compose = """services:
  db:
    image: mariadb:11.4
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    environment:
      MARIADB_DATABASE: ${WP_DB_NAME}
      MARIADB_USER: ${WP_DB_USER}
      MARIADB_PASSWORD: ${WP_DB_PASSWORD}
      MARIADB_ROOT_PASSWORD: ${WP_DB_ROOT_PASSWORD}
    volumes:
      - ./data/db:/var/lib/mysql
    healthcheck:
      test: [\"CMD\", \"healthcheck.sh\", \"--connect\", \"--innodb_initialized\"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s

  wordpress:
    image: wordpress:php8.3-apache
    depends_on:
      db:
        condition: service_healthy
    ports:
      - \"127.0.0.1:${WP_HTTP_PORT}:80\"
    environment:
      WORDPRESS_DB_HOST: db:3306
      WORDPRESS_DB_NAME: ${WP_DB_NAME}
      WORDPRESS_DB_USER: ${WP_DB_USER}
      WORDPRESS_DB_PASSWORD: ${WP_DB_PASSWORD}
      WORDPRESS_CONFIG_EXTRA: |
        define('WP_HOME', '${WP_SITE_URL}');
        define('WP_SITEURL', '${WP_SITE_URL}');
        define('WP_DEBUG', true);
        define('WP_DEBUG_LOG', true);
        define('DISALLOW_FILE_EDIT', true);
        define('AUTOMATIC_UPDATER_DISABLED', true);
    volumes:
      - ../staging/wordpress:/var/www/html
      - ../staging/wp-content:/var/www/html/wp-content
      - ./data/logs:/var/www/html/wp-content/debug
    healthcheck:
      test: [\"CMD-SHELL\", \"php -r \\\"exit((int)!@file_get_contents('http://127.0.0.1/wp-login.php'));\\\"\"]
      interval: 15s
      timeout: 5s
      retries: 20
      start_period: 30s

  wpcli:
    image: wordpress:cli-php8.3
    profiles: [\"tools\"]
    depends_on:
      db:
        condition: service_healthy
      wordpress:
        condition: service_started
    environment:
      WORDPRESS_DB_HOST: db:3306
      WORDPRESS_DB_NAME: ${WP_DB_NAME}
      WORDPRESS_DB_USER: ${WP_DB_USER}
      WORDPRESS_DB_PASSWORD: ${WP_DB_PASSWORD}
    volumes:
      - ../staging/wordpress:/var/www/html
      - ../staging/wp-content:/var/www/html/wp-content
    working_dir: /var/www/html
    entrypoint: [\"wp\", \"--path=/var/www/html\"]
"""
    readme = """# WordPress Surface Lab Runtime

- Purpose: run the isolated Astra/WordPress lab locally without sending public traffic to `seoulmna.kr`.
- Exposure policy: the lab binds only to `127.0.0.1`, so it is not reachable from the public internet.
- Runtime target: validate the `seoulmna-platform-child` theme, `seoulmna-platform-bridge` plugin, Gutenberg blueprints, and the `/_calc/*` lazy-gate behavior before any live change.

## Files
- `docker-compose.yml`: local-only runtime with WordPress, MariaDB, and WP-CLI.
- `.env.local`: safe default local values for internal testing.
- `.env.example`: template for resetting the lab.

## Runtime Modes
1. Docker runtime
   - `http://127.0.0.1:18080`
2. PHP fallback runtime
   - `http://127.0.0.1:18081`

## Start
1. Install Docker Desktop.
2. From this directory, run:
   - `docker compose --env-file .env.local up -d`
3. Open:
   - `http://127.0.0.1:18080/wp-admin/`

## PHP Fallback
- The PHP fallback path is the active local verification lane when Docker is unavailable.
- Start it with the generated PowerShell script under `php_fallback/`.
- Use `http://127.0.0.1:18081/wp-admin/`.

## Bootstrap
Run the following commands after the containers are healthy:
- `docker compose --env-file .env.local run --rm wpcli core install --url=\"$WP_SITE_URL\" --title=\"$WP_SITE_TITLE\" --admin_user=\"$WP_ADMIN_USER\" --admin_password=\"$WP_ADMIN_PASSWORD\" --admin_email=\"$WP_ADMIN_EMAIL\" --skip-email`
- `docker compose --env-file .env.local run --rm wpcli theme activate seoulmna-platform-child`
- `docker compose --env-file .env.local run --rm wpcli plugin activate seoulmna-platform-bridge`

## Verify
- Homepage `/` renders CTA-only without creating calculator iframes on first load.
- `/yangdo` and `/permit` render lazy calculator gates and create iframes only after explicit click.
- `/knowledge` remains CTA-only.
- `/mna-market` routes to the listing site instead of embedding calculators.
"""

    gitignore = """data/db/*
data/logs/*
!data/db/.gitkeep
!data/logs/.gitkeep
"""

    _write_text(runtime_root / ".env.example", env_example)
    _write_text(runtime_root / ".env.local", env_local)
    _write_text(runtime_root / "docker-compose.yml", compose)
    _write_text(runtime_root / "README.md", readme)
    _write_text(runtime_root / ".gitignore", gitignore)

    docker_available = shutil.which("docker") is not None
    wp_summary = wp_lab.get("summary") if isinstance(wp_lab.get("summary"), dict) else {}
    plugin = wp_assets.get("plugin") if isinstance(wp_assets.get("plugin"), dict) else {}
    theme = wp_assets.get("theme") if isinstance(wp_assets.get("theme"), dict) else {}

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runtime_root": str(runtime_root),
        "paths": {
            "compose": str((runtime_root / "docker-compose.yml").resolve()),
            "env_example": str((runtime_root / ".env.example").resolve()),
            "env_local": str((runtime_root / ".env.local").resolve()),
            "readme": str((runtime_root / "README.md").resolve()),
        },
        "policy": {
            "bind_host": "127.0.0.1",
            "localhost_url": "http://127.0.0.1:18080",
            "docker_localhost_url": "http://127.0.0.1:18080",
            "php_fallback_localhost_url": "http://127.0.0.1:18081",
            "active_runtime_hint": "php_fallback",
            "public_traffic_policy": "internal_lab_only",
            "theme_slug": str(theme.get("slug") or ""),
            "plugin_slug": str(plugin.get("slug") or ""),
            "public_mount_base": str(plugin.get("public_mount_base") or "https://seoulmna.kr/_calc"),
        },
        "commands": {
            "start": "docker compose --env-file .env.local up -d",
            "stop": "docker compose --env-file .env.local down",
            "bootstrap_core": "docker compose --env-file .env.local run --rm wpcli core install --url=\"$WP_SITE_URL\" --title=\"$WP_SITE_TITLE\" --admin_user=\"$WP_ADMIN_USER\" --admin_password=\"$WP_ADMIN_PASSWORD\" --admin_email=\"$WP_ADMIN_EMAIL\" --skip-email",
            "activate_theme": "docker compose --env-file .env.local run --rm wpcli theme activate seoulmna-platform-child",
            "activate_bridge_plugin": "docker compose --env-file .env.local run --rm wpcli plugin activate seoulmna-platform-bridge",
        },
        "runtime_probe": {
            "docker_available": docker_available,
            "source_packages_ready": bool(wp_summary.get("staging_ready_count")),
            "runtime_scaffold_ready": True,
        },
        "summary": {
            "runtime_scaffold_ready": True,
            "docker_available": docker_available,
            "local_bind_only": True,
            "bind_host": "127.0.0.1",
            "command_count": 5,
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
    commands = payload.get("commands") if isinstance(payload.get("commands"), dict) else {}
    lines = [
        "# WordPress Surface Lab Runtime",
        "",
        f"- runtime_root: {payload.get('runtime_root') or '(none)'}",
        f"- runtime_scaffold_ready: {summary.get('runtime_scaffold_ready')}",
        f"- docker_available: {summary.get('docker_available')}",
        f"- local_bind_only: {summary.get('local_bind_only')}",
        f"- bind_host: {summary.get('bind_host')}",
        f"- localhost_url: {policy.get('localhost_url') or '(none)'}",
        f"- public_mount_base: {policy.get('public_mount_base') or '(none)'}",
        "",
        "## Commands",
    ]
    for key, value in commands.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a local-only Docker runtime for the WordPress surface lab.")
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT)
    parser.add_argument("--wp-lab", type=Path, default=DEFAULT_WP_LAB)
    parser.add_argument("--wp-assets", type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_runtime_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_runtime_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab_runtime(
        lab_root=args.lab_root,
        wp_lab_path=args.wp_lab,
        wp_assets_path=args.wp_assets,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
