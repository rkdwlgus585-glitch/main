#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / "logs" / "wp_surface_lab_runtime_latest.json"
DEFAULT_WP_LAB = ROOT / "logs" / "wp_surface_lab_latest.json"
DEFAULT_WP_ASSETS = ROOT / "logs" / "wp_platform_assets_latest.json"
DEFAULT_PHP_RUNTIME = ROOT / "logs" / "wp_surface_lab_php_runtime_latest.json"
DEFAULT_PHP_FALLBACK = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _path_from_value(value: Any) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    return path


def _docker_compose_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    completed = subprocess.run(
        [docker, "compose", "version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.returncode == 0


def _http_probe(url: str) -> Dict[str, Any]:
    import urllib.error
    import urllib.request

    last_result: Dict[str, Any] = {"ok": False, "status": 0}
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return {
                    "ok": True,
                    "status": int(getattr(response, "status", 200) or 200),
                }
        except urllib.error.HTTPError as exc:
            last_result = {"ok": False, "status": int(exc.code)}
            if exc.code < 500 or attempt == 3:
                return last_result
        except Exception as exc:
            last_result = {"ok": False, "status": 0, "error": str(exc)}
            if attempt == 3:
                return last_result
        time.sleep(0.8 * (attempt + 1))
    return last_result


def build_wp_surface_lab_runtime_validation(
    *,
    runtime_path: Path,
    wp_lab_path: Path,
    wp_assets_path: Path,
    php_runtime_path: Path,
    php_fallback_path: Path,
) -> Dict[str, Any]:
    runtime = _load_json(runtime_path)
    wp_lab = _load_json(wp_lab_path)
    wp_assets = _load_json(wp_assets_path)
    php_runtime = _load_json(php_runtime_path)
    php_fallback = _load_json(php_fallback_path)

    paths = runtime.get("paths") if isinstance(runtime.get("paths"), dict) else {}
    compose_path = _path_from_value(paths.get("compose"))
    env_example_path = _path_from_value(paths.get("env_example"))
    env_local_path = _path_from_value(paths.get("env_local"))
    readme_path = _path_from_value(paths.get("readme"))

    files = {
        "compose_exists": bool(compose_path and compose_path.is_file()),
        "env_example_exists": bool(env_example_path and env_example_path.is_file()),
        "env_local_exists": bool(env_local_path and env_local_path.is_file()),
        "readme_exists": bool(readme_path and readme_path.is_file()),
    }
    compose_text = compose_path.read_text(encoding="utf-8") if files["compose_exists"] and compose_path else ""
    local_bind_only = '127.0.0.1:${WP_HTTP_PORT}:80' in compose_text
    mount_core = "../staging/wordpress:/var/www/html" in compose_text
    mount_wp_content = "../staging/wp-content:/var/www/html/wp-content" in compose_text
    has_wpcli = "\n  wpcli:\n" in compose_text

    docker_available = shutil.which("docker") is not None
    docker_compose_available = _docker_compose_available()
    php_runtime_summary = php_runtime.get("summary") if isinstance(php_runtime.get("summary"), dict) else {}
    php_runtime_runtime = php_runtime.get("runtime") if isinstance(php_runtime.get("runtime"), dict) else {}
    php_fallback_summary = php_fallback.get("summary") if isinstance(php_fallback.get("summary"), dict) else {}
    php_runtime_ready = bool(php_runtime_summary.get("runtime_ready"))
    php_bootstrap_ready = bool(php_fallback_summary.get("bootstrap_ready"))
    php_localhost_url = str(php_runtime_runtime.get("localhost_url") or php_fallback.get("site_url") or "http://127.0.0.1:18081")

    wp_summary = wp_lab.get("summary") if isinstance(wp_lab.get("summary"), dict) else {}
    theme = wp_assets.get("theme") if isinstance(wp_assets.get("theme"), dict) else {}
    plugin = wp_assets.get("plugin") if isinstance(wp_assets.get("plugin"), dict) else {}

    blockers: List[str] = []
    if not files["compose_exists"]:
        blockers.append("compose_missing")
    if not files["env_example_exists"]:
        blockers.append("env_example_missing")
    if not files["env_local_exists"]:
        blockers.append("env_local_missing")
    if not local_bind_only:
        blockers.append("local_bind_not_enforced")
    if not mount_core:
        blockers.append("core_mount_missing")
    if not mount_wp_content:
        blockers.append("wp_content_mount_missing")
    if not has_wpcli:
        blockers.append("wpcli_service_missing")
    if not docker_available and not php_bootstrap_ready:
        blockers.append("docker_missing")
    elif docker_available and not docker_compose_available and not php_bootstrap_ready:
        blockers.append("docker_compose_missing")
    if not bool(wp_summary.get("staging_ready_count")):
        blockers.append("staging_assets_missing")
    if not bool(theme.get("ready")):
        blockers.append("platform_theme_missing")
    if not bool(plugin.get("ready")):
        blockers.append("platform_bridge_missing")

    docker_scaffold_ready = not any(
        key in blockers
        for key in (
            "compose_missing",
            "env_example_missing",
            "env_local_missing",
            "local_bind_not_enforced",
            "core_mount_missing",
            "wp_content_mount_missing",
            "wpcli_service_missing",
            "staging_assets_missing",
            "platform_theme_missing",
            "platform_bridge_missing",
        )
    )
    runtime_scaffold_ready = docker_scaffold_ready or php_bootstrap_ready
    docker_runtime_ready = docker_scaffold_ready and docker_available and docker_compose_available
    runtime_ready = docker_runtime_ready or php_bootstrap_ready
    runtime_mode = "docker" if docker_runtime_ready else ("php_fallback" if php_bootstrap_ready else "none")
    localhost_url = str((runtime.get("policy") or {}).get("localhost_url") or "http://127.0.0.1:18080") if runtime_mode == "docker" else php_localhost_url
    live_probe = _http_probe(localhost_url) if runtime_mode != "none" else {"ok": False, "status": 0, "error": "runtime_not_launch_ready"}
    runtime_running = bool(live_probe.get("ok"))

    next_actions: List[str] = []
    if "docker_missing" in blockers:
        next_actions.append("Install Docker Desktop to run the internal WordPress surface lab.")
    elif "docker_compose_missing" in blockers:
        next_actions.append("Repair Docker Compose support so the internal WordPress lab can start.")
    if not php_runtime_ready:
        next_actions.append("Download and verify the official Windows PHP runtime for the Docker-free fallback path.")
    elif not php_bootstrap_ready:
        next_actions.append("Bootstrap the PHP fallback WordPress site root before starting the local server.")
    if "local_bind_not_enforced" in blockers:
        next_actions.append("Keep the lab bound to 127.0.0.1 only to avoid public traffic leakage.")
    if "platform_theme_missing" in blockers or "platform_bridge_missing" in blockers:
        next_actions.append("Refresh the WordPress platform asset scaffold before running the lab.")
    if runtime_mode == "php_fallback" and not runtime_running:
        next_actions.append("Start the Windows PHP fallback server and rerun page verification.")
    elif runtime_mode == "docker" and not runtime_running:
        next_actions.append("Start the Docker runtime and rerun page verification.")
    elif runtime_mode != "none" and not runtime_running:
        next_actions.append("Start the selected local runtime and rerun page verification.")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runtime_root": str(compose_path.parent if compose_path else ""),
        "files": files,
        "checks": {
            "local_bind_only": local_bind_only,
            "mount_core": mount_core,
            "mount_wp_content": mount_wp_content,
            "has_wpcli": has_wpcli,
            "docker_available": docker_available,
            "docker_compose_available": docker_compose_available,
            "php_runtime_ready": php_runtime_ready,
            "php_bootstrap_ready": php_bootstrap_ready,
            "platform_theme_ready": bool(theme.get("ready")),
            "platform_bridge_ready": bool(plugin.get("ready")),
        },
        "handoff": {
            "runtime_scaffold_ready": runtime_scaffold_ready,
            "runtime_ready": runtime_ready,
            "runtime_mode": runtime_mode,
            "runtime_running": runtime_running,
            "localhost_url": localhost_url,
            "next_actions": next_actions,
        },
        "summary": {
            "runtime_scaffold_ready": runtime_scaffold_ready,
            "runtime_ready": runtime_ready,
            "runtime_running": runtime_running,
            "runtime_mode": runtime_mode,
            "blocker_count": len(blockers),
            "blockers": blockers,
        },
        "live_probe": live_probe,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    handoff = payload.get("handoff") if isinstance(payload.get("handoff"), dict) else {}
    lines = [
        "# WordPress Surface Lab Runtime Validation",
        "",
        f"- runtime_scaffold_ready: {summary.get('runtime_scaffold_ready')}",
        f"- runtime_ready: {summary.get('runtime_ready')}",
        f"- runtime_running: {summary.get('runtime_running')}",
        f"- runtime_mode: {summary.get('runtime_mode')}",
        f"- blocker_count: {summary.get('blocker_count')}",
        f"- blockers: {', '.join(summary.get('blockers') or []) or '(none)'}",
        f"- localhost_url: {handoff.get('localhost_url') or '(none)'}",
        "",
        "## Next Actions",
    ]
    for item in handoff.get("next_actions") or []:
        lines.append(f"- {item}")
    if not (handoff.get("next_actions") or []):
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the local-only Docker runtime scaffold for the WordPress surface lab.")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--wp-lab", type=Path, default=DEFAULT_WP_LAB)
    parser.add_argument("--wp-assets", type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument("--php-runtime", type=Path, default=DEFAULT_PHP_RUNTIME)
    parser.add_argument("--php-fallback", type=Path, default=DEFAULT_PHP_FALLBACK)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_runtime_validation_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_runtime_validation_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab_runtime_validation(
        runtime_path=args.runtime,
        wp_lab_path=args.wp_lab,
        wp_assets_path=args.wp_assets,
        php_runtime_path=args.php_runtime,
        php_fallback_path=args.php_fallback,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("runtime_scaffold_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
