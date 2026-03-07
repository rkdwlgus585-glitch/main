#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_BLUEPRINTS = ROOT / "logs" / "wp_platform_blueprints_latest.json"
DEFAULT_RUNTIME = ROOT / "logs" / "wp_surface_lab_runtime_latest.json"
DEFAULT_RUNTIME_VALIDATION = ROOT / "logs" / "wp_surface_lab_runtime_validation_latest.json"
DEFAULT_PHP_RUNTIME = ROOT / "logs" / "wp_surface_lab_php_runtime_latest.json"
DEFAULT_PHP_FALLBACK = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json"
DEFAULT_WP_ASSETS = ROOT / "logs" / "wp_platform_assets_latest.json"
DEFAULT_CUTOVER = ROOT / "logs" / "kr_reverse_proxy_cutover_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _quote_php(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _http_probe(url: str) -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return int(getattr(response, "status", 200) or 200) < 500
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def _page_slug(page: Dict[str, Any]) -> str:
    explicit = str(page.get("wordpress_page_slug") or "").strip().strip("/")
    if explicit:
        return explicit
    return str(page.get("slug") or "/").strip("/").replace("/", "-") or "home"


def _relative_theme_path(theme_slug: str, blueprint_file: str | Path) -> str:
    path = Path(str(blueprint_file))
    return f"blueprints/{path.name}"


def _build_manifest(
    *,
    ia: Dict[str, Any],
    blueprints: Dict[str, Any],
    theme_slug: str,
    plugin_slug: str,
) -> Dict[str, Any]:
    blueprint_rows = {
        str(row.get("page_id") or ""): row
        for row in blueprints.get("pages", [])
        if isinstance(row, dict)
    }
    pages: List[Dict[str, Any]] = []
    for row in ia.get("pages", []):
        if not isinstance(row, dict):
            continue
        page_id = str(row.get("page_id") or "").strip()
        blueprint = blueprint_rows.get(page_id, {})
        public_slug = str(row.get("slug") or "/").strip() or "/"
        wordpress_slug = _page_slug(row)
        pages.append(
            {
                "page_id": page_id,
                "public_slug": public_slug,
                "wordpress_page_slug": wordpress_slug,
                "title": str(row.get("title") or ""),
                "calculator_policy": str(row.get("calculator_policy") or ""),
                "blueprint_relative_path": _relative_theme_path(theme_slug, blueprint.get("blueprint_file") or f"{wordpress_slug}.html"),
                "is_front_page": page_id == str((ia.get("summary") or {}).get("front_page_id") or "home"),
            }
        )

    menu_items = list((ia.get("navigation") or {}).get("primary") or [])
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "theme_slug": theme_slug,
        "plugin_slug": plugin_slug,
        "front_page_slug": str((ia.get("summary") or {}).get("front_page_slug") or "home"),
        "front_page_public_slug": "/",
        "menu": {
            "name": "서울건설정보 플랫폼",
            "location_candidates": ["primary", "menu-1", "main-menu"],
            "items": menu_items,
        },
        "pages": pages,
    }


def _build_php_bundle(manifest: Dict[str, Any]) -> str:
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
    return f"""<?php
if (!defined('ABSPATH')) {{
    exit(1);
}}

if (!function_exists('wp_get_nav_menu_items')) {{
    require_once ABSPATH . 'wp-admin/includes/nav-menu.php';
}}

$manifest = json_decode(<<<'JSON'
{manifest_json}
JSON
, true);

if (!is_array($manifest)) {{
    fwrite(STDERR, "invalid manifest\\n");
    exit(1);
}}

$theme_dir = get_theme_root() . DIRECTORY_SEPARATOR . { _quote_php(manifest.get("theme_slug") or "seoulmna-platform-child") };
$results = [];
$page_ids = [];

foreach (($manifest['pages'] ?? []) as $page) {{
    $wordpress_slug = trim((string)($page['wordpress_page_slug'] ?? ''), '/');
    $public_slug = (string)($page['public_slug'] ?? '/');
    $blueprint_rel = ltrim((string)($page['blueprint_relative_path'] ?? ''), '/');
    $blueprint_path = $theme_dir . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $blueprint_rel);
    $content = is_file($blueprint_path) ? (string) file_get_contents($blueprint_path) : '';

    $existing = $wordpress_slug !== '' ? get_page_by_path($wordpress_slug, OBJECT, 'page') : null;
    $postarr = [
        'post_type' => 'page',
        'post_status' => 'publish',
        'post_title' => (string)($page['title'] ?? $wordpress_slug),
        'post_name' => $wordpress_slug,
        'post_content' => $content,
    ];

    if ($existing instanceof WP_Post) {{
        $postarr['ID'] = (int) $existing->ID;
        $post_id = wp_update_post(wp_slash($postarr), true);
        $action = 'updated';
    }} else {{
        $post_id = wp_insert_post(wp_slash($postarr), true);
        $action = 'created';
    }}

    if (is_wp_error($post_id)) {{
        $results[] = [
            'page_id' => $page['page_id'] ?? '',
            'public_slug' => $public_slug,
            'wordpress_page_slug' => $wordpress_slug,
            'ok' => false,
            'action' => 'error',
            'error' => $post_id->get_error_message(),
        ];
        continue;
    }}

    $post_id = (int) $post_id;
    $page_ids[(string)($page['page_id'] ?? $wordpress_slug)] = $post_id;
    $results[] = [
        'page_id' => $page['page_id'] ?? '',
        'public_slug' => $public_slug,
        'wordpress_page_slug' => $wordpress_slug,
        'post_id' => $post_id,
        'ok' => true,
        'action' => $action,
        'calculator_policy' => (string)($page['calculator_policy'] ?? ''),
    ];
}}

$front_page_key = (string)($manifest['front_page_slug'] ?? 'home');
$front_page_id = isset($page_ids[$front_page_key]) ? (int) $page_ids[$front_page_key] : 0;
if ($front_page_id > 0) {{
    update_option('show_on_front', 'page');
    update_option('page_on_front', $front_page_id);
}}
update_option('permalink_structure', '/%postname%/');
if (function_exists('flush_rewrite_rules')) {{
    flush_rewrite_rules();
}}

$menu_name = (string)(($manifest['menu'] ?? [])['name'] ?? '서울건설정보 플랫폼');
$menu_obj = wp_get_nav_menu_object($menu_name);
$menu_id = $menu_obj ? (int) $menu_obj->term_id : (int) wp_create_nav_menu($menu_name);
if (!is_wp_error($menu_id) && $menu_id > 0) {{
    $existing_items = wp_get_nav_menu_items($menu_id) ?: [];
    $front_page_lookup_slug = (string)($manifest['front_page_slug'] ?? 'home');
    foreach ($existing_items as $item) {{
        wp_delete_post((int) $item->ID, true);
    }}
    foreach ((($manifest['menu'] ?? [])['items'] ?? []) as $item) {{
        $href = (string)($item['href'] ?? '');
        $label = (string)($item['label'] ?? $href);
        if ($href === '') {{
            continue;
        }}
        if (str_starts_with($href, '/')) {{
            $slug = trim($href, '/');
            if ($slug === '') {{
                $slug = $front_page_lookup_slug;
            }}
            $page = $slug === '' ? null : get_page_by_path($slug, OBJECT, 'page');
            if ($page instanceof WP_Post) {{
                wp_update_nav_menu_item($menu_id, 0, [
                    'menu-item-title' => $label,
                    'menu-item-object-id' => (int) $page->ID,
                    'menu-item-object' => 'page',
                    'menu-item-type' => 'post_type',
                    'menu-item-status' => 'publish',
                ]);
                continue;
            }}
        }}
        wp_update_nav_menu_item($menu_id, 0, [
            'menu-item-title' => $label,
            'menu-item-url' => $href,
            'menu-item-status' => 'publish',
        ]);
    }}

    $registered = get_registered_nav_menus();
    $locations = get_theme_mod('nav_menu_locations', []);
    $assigned_location = null;
    foreach ((($manifest['menu'] ?? [])['location_candidates'] ?? []) as $candidate) {{
        if (isset($registered[$candidate])) {{
            $locations[$candidate] = $menu_id;
            $assigned_location = $candidate;
            break;
        }}
    }}
    set_theme_mod('nav_menu_locations', $locations);
}} else {{
    $assigned_location = null;
}}

echo wp_json_encode([
    'ok' => true,
    'page_results' => $results,
    'front_page_id' => $front_page_id,
    'menu_name' => $menu_name,
    'menu_location' => $assigned_location,
    'permalink_structure' => get_option('permalink_structure'),
], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
"""


def _build_standalone_php_bundle(manifest: Dict[str, Any], *, site_root: str, theme_slug: str, plugin_slug: str) -> str:
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
    return f"""<?php
$siteRoot = { _quote_php(site_root) };
if (!defined('ABSPATH')) {{
    define('ABSPATH', $siteRoot . DIRECTORY_SEPARATOR);
}}
require_once $siteRoot . '/wp-load.php';

$manifest = json_decode(<<<'JSON'
{manifest_json}
JSON
, true);

if (!is_array($manifest)) {{
    fwrite(STDERR, "invalid manifest\\n");
    exit(1);
}}

if (!function_exists('wp_get_nav_menu_items')) {{
    require_once ABSPATH . 'wp-admin/includes/nav-menu.php';
}}
if (!function_exists('activate_plugin')) {{
    require_once ABSPATH . 'wp-admin/includes/plugin.php';
}}

$themeSlug = { _quote_php(theme_slug) };
$pluginSlug = { _quote_php(plugin_slug) };
if (function_exists('switch_theme')) {{
    switch_theme($themeSlug);
}}
$pluginMainFile = $pluginSlug . '/' . $pluginSlug . '.php';
if (function_exists('is_plugin_inactive') && is_plugin_inactive($pluginMainFile)) {{
    activate_plugin($pluginMainFile, '', false, true);
}}

$theme_dir = get_theme_root() . DIRECTORY_SEPARATOR . $themeSlug;
$results = [];
$page_ids = [];

foreach (($manifest['pages'] ?? []) as $page) {{
    $wordpress_slug = trim((string)($page['wordpress_page_slug'] ?? ''), '/');
    $public_slug = (string)($page['public_slug'] ?? '/');
    $blueprint_rel = ltrim((string)($page['blueprint_relative_path'] ?? ''), '/');
    $blueprint_path = $theme_dir . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $blueprint_rel);
    $content = is_file($blueprint_path) ? (string) file_get_contents($blueprint_path) : '';

    $existing = $wordpress_slug !== '' ? get_page_by_path($wordpress_slug, OBJECT, 'page') : null;
    $postarr = [
        'post_type' => 'page',
        'post_status' => 'publish',
        'post_title' => (string)($page['title'] ?? $wordpress_slug),
        'post_name' => $wordpress_slug,
        'post_content' => $content,
    ];

    if ($existing instanceof WP_Post) {{
        $postarr['ID'] = (int) $existing->ID;
        $post_id = wp_update_post(wp_slash($postarr), true);
        $action = 'updated';
    }} else {{
        $post_id = wp_insert_post(wp_slash($postarr), true);
        $action = 'created';
    }}

    if (is_wp_error($post_id)) {{
        $results[] = [
            'page_id' => $page['page_id'] ?? '',
            'public_slug' => $public_slug,
            'wordpress_page_slug' => $wordpress_slug,
            'ok' => false,
            'action' => 'error',
            'error' => $post_id->get_error_message(),
        ];
        continue;
    }}

    $post_id = (int) $post_id;
    $page_ids[(string)($page['page_id'] ?? $wordpress_slug)] = $post_id;
    $results[] = [
        'page_id' => $page['page_id'] ?? '',
        'public_slug' => $public_slug,
        'wordpress_page_slug' => $wordpress_slug,
        'post_id' => $post_id,
        'ok' => true,
        'action' => $action,
        'calculator_policy' => (string)($page['calculator_policy'] ?? ''),
    ];
}}

$front_page_key = (string)($manifest['front_page_slug'] ?? 'home');
$front_page_id = isset($page_ids[$front_page_key]) ? (int) $page_ids[$front_page_key] : 0;
if ($front_page_id > 0) {{
    update_option('show_on_front', 'page');
    update_option('page_on_front', $front_page_id);
}}
update_option('permalink_structure', '/%postname%/');
if (function_exists('flush_rewrite_rules')) {{
    flush_rewrite_rules();
}}

$menu_name = (string)(($manifest['menu'] ?? [])['name'] ?? '서울건설정보 플랫폼');
$menu_obj = wp_get_nav_menu_object($menu_name);
$menu_id = $menu_obj ? (int) $menu_obj->term_id : (int) wp_create_nav_menu($menu_name);
if (!is_wp_error($menu_id) && $menu_id > 0) {{
    $existing_items = wp_get_nav_menu_items($menu_id) ?: [];
    $front_page_lookup_slug = (string)($manifest['front_page_slug'] ?? 'home');
    foreach ($existing_items as $item) {{
        wp_delete_post((int) $item->ID, true);
    }}
    foreach ((($manifest['menu'] ?? [])['items'] ?? []) as $item) {{
        $href = (string)($item['href'] ?? '');
        $label = (string)($item['label'] ?? $href);
        if ($href === '') {{
            continue;
        }}
        if (str_starts_with($href, '/')) {{
            $slug = trim($href, '/');
            if ($slug === '') {{
                $slug = $front_page_lookup_slug;
            }}
            $page = $slug === '' ? null : get_page_by_path($slug, OBJECT, 'page');
            if ($page instanceof WP_Post) {{
                wp_update_nav_menu_item($menu_id, 0, [
                    'menu-item-title' => $label,
                    'menu-item-object-id' => (int) $page->ID,
                    'menu-item-object' => 'page',
                    'menu-item-type' => 'post_type',
                    'menu-item-status' => 'publish',
                ]);
                continue;
            }}
        }}
        wp_update_nav_menu_item($menu_id, 0, [
            'menu-item-title' => $label,
            'menu-item-url' => $href,
            'menu-item-status' => 'publish',
        ]);
    }}
    $registered = get_registered_nav_menus();
    $locations = get_theme_mod('nav_menu_locations', []);
    foreach ((($manifest['menu'] ?? [])['location_candidates'] ?? []) as $candidate) {{
        if (isset($registered[$candidate])) {{
            $locations[$candidate] = $menu_id;
            break;
        }}
    }}
    set_theme_mod('nav_menu_locations', $locations);
}}

echo wp_json_encode([
    'ok' => true,
    'page_results' => $results,
    'front_page_id' => $front_page_id,
    'menu_name' => $menu_name,
    'permalink_structure' => get_option('permalink_structure'),
], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
"""


def _run_command(command: str, *, cwd: Path) -> Tuple[bool, str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    return completed.returncode == 0, completed.stdout.strip(), completed.stderr.strip()


def build_wp_surface_lab_apply_bundle(
    *,
    ia_path: Path,
    blueprints_path: Path,
    runtime_path: Path,
    runtime_validation_path: Path,
    php_runtime_path: Path,
    php_fallback_path: Path,
    wp_assets_path: Path,
    cutover_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    blueprints = _load_json(blueprints_path)
    runtime = _load_json(runtime_path)
    runtime_validation = _load_json(runtime_validation_path)
    php_runtime = _load_json(php_runtime_path)
    php_fallback = _load_json(php_fallback_path)
    wp_assets = _load_json(wp_assets_path)
    cutover = _load_json(cutover_path)

    theme_slug = str((wp_assets.get("theme") or {}).get("slug") or "seoulmna-platform-child")
    plugin_slug = str((wp_assets.get("plugin") or {}).get("slug") or "seoulmna-platform-bridge")
    runtime_root = Path(str(runtime.get("runtime_root") or ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab" / "runtime"))
    env_file = runtime_root / ".env.local"
    env = _load_env_file(env_file)
    php_paths = php_runtime.get("paths") if isinstance(php_runtime.get("paths"), dict) else {}
    php_fallback_paths = php_fallback.get("paths") if isinstance(php_fallback.get("paths"), dict) else {}
    theme_tools_root = runtime_root.parent / "staging" / "wp-content" / "themes" / theme_slug / "tools"
    theme_tools_root.mkdir(parents=True, exist_ok=True)

    manifest = _build_manifest(ia=ia, blueprints=blueprints, theme_slug=theme_slug, plugin_slug=plugin_slug)
    manifest_path = theme_tools_root / "apply-blueprints-manifest.json"
    php_bundle_path = theme_tools_root / "apply-platform-blueprints.php"
    standalone_php_bundle_path = theme_tools_root / "apply-platform-blueprints-standalone.php"
    _write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    _write(php_bundle_path, _build_php_bundle(manifest))
    _write(
        standalone_php_bundle_path,
        _build_standalone_php_bundle(
            manifest,
            site_root=str(php_fallback_paths.get("site_root") or ""),
            theme_slug=theme_slug,
            plugin_slug=plugin_slug,
        ),
    )

    site_url = env.get("WP_SITE_URL", "http://127.0.0.1:18080")
    site_title = env.get("WP_SITE_TITLE", "SeoulMNA Platform Lab")
    admin_user = env.get("WP_ADMIN_USER", "admin")
    admin_password = env.get("WP_ADMIN_PASSWORD", "change-me-before-sharing")
    admin_email = env.get("WP_ADMIN_EMAIL", "lab@seoulmna.local")
    runtime_ready = bool((runtime_validation.get("summary") or {}).get("runtime_ready"))
    runtime_scaffold_ready = bool((runtime_validation.get("summary") or {}).get("runtime_scaffold_ready"))
    runtime_mode = str((runtime_validation.get("summary") or {}).get("runtime_mode") or "none")
    docker_available = bool((runtime.get("runtime_probe") or {}).get("docker_available"))
    php_binary_ready = bool((php_runtime.get("summary") or {}).get("php_binary_ready"))
    php_fallback_ready = bool((php_fallback.get("summary") or {}).get("bootstrap_ready"))
    cutover_ready = bool((cutover.get("summary") or {}).get("cutover_ready"))

    bootstrap_core = (
        "docker compose --env-file .env.local run --rm --entrypoint sh wpcli "
        f"-lc \"wp core is-installed || wp core install --url='{site_url}' --title='{site_title}' "
        f"--admin_user='{admin_user}' --admin_password='{admin_password}' --admin_email='{admin_email}' --skip-email\""
    )
    apply_eval = (
        "docker compose --env-file .env.local run --rm --entrypoint sh wpcli "
        f"-lc \"wp eval-file /var/www/html/wp-content/themes/{theme_slug}/tools/apply-platform-blueprints.php\""
    )
    php_apply = (
        f"\"{php_paths.get('php_executable') or ''}\" -c \"{php_paths.get('php_ini') or ''}\" "
        f"\"{standalone_php_bundle_path}\""
    ).strip()
    dry_run = f"{Path(sys.executable).name or 'py'} {Path(__file__).name}"
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "artifacts": {
            "manifest_file": str(manifest_path),
            "php_bundle_file": str(php_bundle_path),
            "standalone_php_bundle_file": str(standalone_php_bundle_path),
            "runtime_root": str(runtime_root),
            "env_file": str(env_file),
            "php_site_root": str(php_fallback_paths.get("site_root") or ""),
        },
        "summary": {
            "bundle_ready": True,
            "page_count": len(manifest.get("pages") or []),
            "service_page_count": len([row for row in manifest.get("pages", []) if row.get("calculator_policy") == "lazy_gate_shortcode"]),
            "runtime_scaffold_ready": runtime_scaffold_ready,
            "runtime_ready": runtime_ready,
            "runtime_mode": runtime_mode,
            "docker_available": docker_available,
            "php_binary_ready": php_binary_ready,
            "php_fallback_ready": php_fallback_ready,
            "cutover_ready": cutover_ready,
            "front_page_slug": str(manifest.get("front_page_slug") or "home"),
        },
        "commands": {
            "start_runtime": str((runtime.get("commands") or {}).get("start") or ""),
            "start_php_fallback": str((php_fallback.get("commands") or {}).get("start_server") or ""),
            "bootstrap_core": bootstrap_core,
            "activate_theme": str((runtime.get("commands") or {}).get("activate_theme") or ""),
            "activate_bridge_plugin": str((runtime.get("commands") or {}).get("activate_bridge_plugin") or ""),
            "apply": apply_eval,
            "apply_php_fallback": php_apply,
            "dry_run": (
                "py -3 scripts/apply_wp_surface_lab_blueprints.py "
                f"--ia {ia_path} --blueprints {blueprints_path} --runtime {runtime_path} "
                f"--runtime-validation {runtime_validation_path} --php-runtime {php_runtime_path} "
                f"--php-fallback {php_fallback_path} --wp-assets {wp_assets_path} --cutover {cutover_path}"
            ),
        },
        "manifest": manifest,
        "next_actions": [
            "Start the local-only Docker runtime or the PHP fallback runtime before running apply mode.",
            "Run the generated WP-CLI eval-file bundle or the standalone PHP apply bundle after theme and bridge plugin activation.",
            "Verify the homepage stays CTA-only and the service pages create calculator iframes only after click.",
        ],
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    commands = payload.get("commands") if isinstance(payload.get("commands"), dict) else {}
    lines = [
        "# WordPress Surface Lab Apply Bundle",
        "",
        f"- bundle_ready: {summary.get('bundle_ready')}",
        f"- page_count: {summary.get('page_count')}",
        f"- service_page_count: {summary.get('service_page_count')}",
        f"- runtime_scaffold_ready: {summary.get('runtime_scaffold_ready')}",
        f"- runtime_ready: {summary.get('runtime_ready')}",
        f"- runtime_mode: {summary.get('runtime_mode')}",
        f"- docker_available: {summary.get('docker_available')}",
        f"- php_binary_ready: {summary.get('php_binary_ready')}",
        f"- php_fallback_ready: {summary.get('php_fallback_ready')}",
        f"- cutover_ready: {summary.get('cutover_ready')}",
        f"- front_page_slug: {summary.get('front_page_slug')}",
        "",
        "## Artifacts",
        f"- manifest_file: {artifacts.get('manifest_file') or '(none)'}",
        f"- php_bundle_file: {artifacts.get('php_bundle_file') or '(none)'}",
        f"- standalone_php_bundle_file: {artifacts.get('standalone_php_bundle_file') or '(none)'}",
        f"- env_file: {artifacts.get('env_file') or '(none)'}",
        "",
        "## Commands",
    ]
    for key, value in commands.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Page Map")
    for row in (payload.get("manifest") or {}).get("pages", []):
        lines.append(
            f"- {row.get('public_slug')} -> wp:{row.get('wordpress_page_slug')} [{row.get('calculator_policy')}]"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and optionally apply the WordPress page blueprint bundle in the local surface lab.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--blueprints", type=Path, default=DEFAULT_BLUEPRINTS)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--runtime-validation", type=Path, default=DEFAULT_RUNTIME_VALIDATION)
    parser.add_argument("--php-runtime", type=Path, default=DEFAULT_PHP_RUNTIME)
    parser.add_argument("--php-fallback", type=Path, default=DEFAULT_PHP_FALLBACK)
    parser.add_argument("--wp-assets", type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument("--cutover", type=Path, default=DEFAULT_CUTOVER)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_apply_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_apply_latest.md")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    payload = build_wp_surface_lab_apply_bundle(
        ia_path=args.ia,
        blueprints_path=args.blueprints,
        runtime_path=args.runtime,
        runtime_validation_path=args.runtime_validation,
        php_runtime_path=args.php_runtime,
        php_fallback_path=args.php_fallback,
        wp_assets_path=args.wp_assets,
        cutover_path=args.cutover,
    )

    apply_result: Dict[str, Any] = {"attempted": False, "ok": False, "blockers": []}
    if args.apply:
        apply_result["attempted"] = True
        php_runtime = _load_json(args.php_runtime)
        php_fallback = _load_json(args.php_fallback)
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        blockers: List[str] = []
        if not summary.get("runtime_scaffold_ready"):
            blockers.append("runtime_scaffold_not_ready")
        if not summary.get("docker_available") and not summary.get("php_fallback_ready"):
            blockers.append("runtime_mode_missing")
        if not summary.get("cutover_ready"):
            blockers.append("cutover_not_ready")
        if blockers:
            apply_result["blockers"] = blockers
        else:
            runtime_root = Path((payload.get("artifacts") or {}).get("runtime_root") or "")
            php_site_root = Path((payload.get("artifacts") or {}).get("php_site_root") or runtime_root)
            commands = payload.get("commands") if isinstance(payload.get("commands"), dict) else {}
            execution_log: List[Dict[str, Any]] = []
            apply_sequence = (
                ["start_runtime", "bootstrap_core", "activate_theme", "activate_bridge_plugin", "apply"]
                if summary.get("docker_available")
                else ["start_php_fallback", "apply_php_fallback"]
            )
            localhost_url = str((php_runtime.get("runtime") or {}).get("localhost_url") or (php_fallback.get("site_url") or "http://127.0.0.1:18081"))
            if not summary.get("docker_available") and _http_probe(localhost_url):
                apply_sequence = [step for step in apply_sequence if step != "start_php_fallback"]
            for key in apply_sequence:
                command = str(commands.get(key) or "").strip()
                if not command:
                    continue
                ok, stdout, stderr = _run_command(command, cwd=runtime_root if summary.get("docker_available") else php_site_root)
                execution_log.append({"step": key, "ok": ok, "stdout": stdout, "stderr": stderr})
                if ok and key == "start_php_fallback":
                    time.sleep(2.0)
                if not ok:
                    apply_result["blockers"] = [f"{key}_failed"]
                    break
            apply_result["execution_log"] = execution_log
            apply_result["ok"] = not apply_result["blockers"]

    payload["apply_result"] = apply_result
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if (not args.apply or payload["apply_result"].get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
