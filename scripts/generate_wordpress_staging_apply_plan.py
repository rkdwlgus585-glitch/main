#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_BLUEPRINTS = ROOT / "logs" / "wp_platform_blueprints_latest.json"
DEFAULT_CUTOVER = ROOT / "logs" / "kr_reverse_proxy_cutover_latest.json"
DEFAULT_RUNTIME = ROOT / "logs" / "wp_surface_lab_runtime_latest.json"
DEFAULT_RUNTIME_VALIDATION = ROOT / "logs" / "wp_surface_lab_runtime_validation_latest.json"
DEFAULT_PHP_RUNTIME = ROOT / "logs" / "wp_surface_lab_php_runtime_latest.json"
DEFAULT_PHP_FALLBACK = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json"
DEFAULT_WP_APPLY = ROOT / "logs" / "wp_surface_lab_apply_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_wordpress_staging_apply_plan(
    *,
    ia_path: Path,
    blueprints_path: Path,
    cutover_path: Path,
    runtime_path: Path,
    runtime_validation_path: Path,
    php_runtime_path: Path,
    php_fallback_path: Path,
    wp_apply_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    blueprints = _load_json(blueprints_path)
    cutover = _load_json(cutover_path)
    runtime = _load_json(runtime_path)
    runtime_validation = _load_json(runtime_validation_path)
    php_runtime = _load_json(php_runtime_path)
    php_fallback = _load_json(php_fallback_path)
    wp_apply = _load_json(wp_apply_path)
    blueprint_rows = {str(row.get("page_id") or ""): row for row in blueprints.get("pages", []) if isinstance(row, dict)}
    page_steps: List[Dict[str, Any]] = []
    for row in ia.get("pages", []):
        if not isinstance(row, dict):
            continue
        page_id = str(row.get("page_id") or "")
        blueprint = blueprint_rows.get(page_id, {})
        page_steps.append(
            {
                "page_id": page_id,
                "slug": str(row.get("slug") or ""),
                "wordpress_page_slug": str(row.get("wordpress_page_slug") or ""),
                "title": str(row.get("title") or ""),
                "calculator_policy": str(row.get("calculator_policy") or ""),
                "blueprint_file": str(blueprint.get("blueprint_file") or ""),
                "required_step": (
                    "paste blueprint and verify no shortcode iframe on initial render"
                    if str(row.get("calculator_policy") or "") == "cta_only_no_iframe"
                    else "paste blueprint and verify lazy gate shortcode opens iframe only after click"
                    if str(row.get("calculator_policy") or "") == "lazy_gate_shortcode"
                    else "paste blueprint and verify consult-only layout"
                ),
            }
        )

    runtime_mode = str((runtime_validation.get("summary") or {}).get("runtime_mode") or "none")
    runtime_running = bool((runtime_validation.get("summary") or {}).get("runtime_running"))
    docker_commands = runtime.get("commands") if isinstance(runtime.get("commands"), dict) else {}
    php_commands = php_fallback.get("commands") if isinstance(php_fallback.get("commands"), dict) else {}
    php_runtime_commands = php_runtime.get("commands") if isinstance(php_runtime.get("commands"), dict) else {}
    wp_apply_commands = wp_apply.get("commands") if isinstance(wp_apply.get("commands"), dict) else {}
    wp_apply_artifacts = wp_apply.get("artifacts") if isinstance(wp_apply.get("artifacts"), dict) else {}
    if runtime_mode == "php_fallback":
        start_command = str(php_commands.get("start_server") or "")
        bootstrap_core_command = str(php_commands.get("install_url") or "")
        activate_theme_command = str(php_commands.get("admin_url") or "")
        activate_bridge_plugin_command = str(php_commands.get("admin_url") or "")
        apply_command = str(wp_apply_commands.get("apply_php_fallback") or "")
        activation_mode = "wp_admin_manual_activation"
    else:
        start_command = str(docker_commands.get("start") or php_commands.get("start_server") or "")
        bootstrap_core_command = str(docker_commands.get("bootstrap_core") or php_commands.get("install_url") or "")
        activate_theme_command = str(docker_commands.get("activate_theme") or "")
        activate_bridge_plugin_command = str(docker_commands.get("activate_bridge_plugin") or "")
        apply_command = str(wp_apply_commands.get("apply") or "")
        activation_mode = "wp_cli_activation" if runtime_mode == "docker" else "pending_runtime_selection"
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "page_step_count": len(page_steps),
            "cutover_ready": bool(cutover.get("summary", {}).get("cutover_ready")),
            "service_page_count": len([row for row in page_steps if row.get("calculator_policy") == "lazy_gate_shortcode"]),
            "runtime_scaffold_ready": bool(runtime_validation.get("summary", {}).get("runtime_scaffold_ready")),
        },
        "page_steps": page_steps,
        "global_steps": [
            "Start with either the local-only Docker runtime or the Windows PHP+SQLite fallback before touching the live WordPress instance.",
            "Activate seoulmna-platform-child in staging.",
            "Activate seoulmna-platform-bridge in staging.",
            "Create or update the six platform pages using the generated blueprints.",
            "Apply the /_calc reverse proxy block before exposing service-page calculator gates to public traffic.",
            "Run homepage, /yangdo, /permit, /knowledge click-path verification before live application.",
        ],
        "runtime_bootstrap": {
            "runtime_scaffold_ready": bool(runtime_validation.get("summary", {}).get("runtime_scaffold_ready")),
            "runtime_ready": bool(runtime_validation.get("summary", {}).get("runtime_ready")),
            "runtime_running": runtime_running,
            "runtime_mode": runtime_mode,
            "activation_mode": activation_mode,
            "localhost_url": str((runtime_validation.get("handoff") or {}).get("localhost_url") or ""),
            "start_command": start_command,
            "bootstrap_core_command": bootstrap_core_command,
            "activate_theme_command": activate_theme_command,
            "activate_bridge_plugin_command": activate_bridge_plugin_command,
            "next_actions": list((runtime_validation.get("handoff") or {}).get("next_actions") or []),
        },
        "wpcli_apply": {
            "bundle_ready": bool(wp_apply.get("summary", {}).get("bundle_ready")),
            "dry_run_command": str(wp_apply_commands.get("dry_run") or ""),
            "apply_command": apply_command,
            "apply_mode": runtime_mode,
            "php_bundle_file": str(wp_apply_artifacts.get("php_bundle_file") or ""),
            "standalone_php_bundle_file": str(wp_apply_artifacts.get("standalone_php_bundle_file") or ""),
            "manifest_file": str(wp_apply_artifacts.get("manifest_file") or ""),
            "next_actions": list((wp_apply.get("next_actions") or [])),
        },
        "verification": list(cutover.get("verification") or []),
        "rollback": cutover.get("rollback") if isinstance(cutover.get("rollback"), dict) else {},
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# WordPress Staging Apply Plan",
        "",
        f"- page_step_count: {payload.get('summary', {}).get('page_step_count')}",
        f"- cutover_ready: {payload.get('summary', {}).get('cutover_ready')}",
        f"- runtime_scaffold_ready: {payload.get('summary', {}).get('runtime_scaffold_ready')}",
        "",
        "## Global Steps",
    ]
    for item in payload.get("global_steps", []):
        lines.append(f"- {item}")
    lines.append("")
    runtime_bootstrap = payload.get("runtime_bootstrap") if isinstance(payload.get("runtime_bootstrap"), dict) else {}
    lines.append("## Runtime Bootstrap")
    lines.append(f"- runtime_scaffold_ready: {runtime_bootstrap.get('runtime_scaffold_ready')}")
    lines.append(f"- runtime_ready: {runtime_bootstrap.get('runtime_ready')}")
    lines.append(f"- runtime_running: {runtime_bootstrap.get('runtime_running')}")
    lines.append(f"- runtime_mode: {runtime_bootstrap.get('runtime_mode') or '(none)'}")
    lines.append(f"- activation_mode: {runtime_bootstrap.get('activation_mode') or '(none)'}")
    lines.append(f"- localhost_url: {runtime_bootstrap.get('localhost_url') or '(none)'}")
    if runtime_bootstrap.get("start_command"):
        lines.append(f"- start_command: {runtime_bootstrap.get('start_command')}")
    if runtime_bootstrap.get("bootstrap_core_command"):
        lines.append(f"- bootstrap_core_command: {runtime_bootstrap.get('bootstrap_core_command')}")
    if runtime_bootstrap.get("activate_theme_command"):
        lines.append(f"- activate_theme_command: {runtime_bootstrap.get('activate_theme_command')}")
    if runtime_bootstrap.get("activate_bridge_plugin_command"):
        lines.append(f"- activate_bridge_plugin_command: {runtime_bootstrap.get('activate_bridge_plugin_command')}")
    for item in runtime_bootstrap.get("next_actions") or []:
        lines.append(f"- runtime_next_action: {item}")
    lines.append("")
    wpcli_apply = payload.get("wpcli_apply") if isinstance(payload.get("wpcli_apply"), dict) else {}
    lines.append("## WP-CLI Apply")
    lines.append(f"- bundle_ready: {wpcli_apply.get('bundle_ready')}")
    lines.append(f"- apply_mode: {wpcli_apply.get('apply_mode') or '(none)'}")
    if wpcli_apply.get("manifest_file"):
        lines.append(f"- manifest_file: {wpcli_apply.get('manifest_file')}")
    if wpcli_apply.get("php_bundle_file"):
        lines.append(f"- php_bundle_file: {wpcli_apply.get('php_bundle_file')}")
    if wpcli_apply.get("standalone_php_bundle_file"):
        lines.append(f"- standalone_php_bundle_file: {wpcli_apply.get('standalone_php_bundle_file')}")
    if wpcli_apply.get("dry_run_command"):
        lines.append(f"- dry_run_command: {wpcli_apply.get('dry_run_command')}")
    if wpcli_apply.get("apply_command"):
        lines.append(f"- apply_command: {wpcli_apply.get('apply_command')}")
    for item in wpcli_apply.get("next_actions") or []:
        lines.append(f"- wpcli_next_action: {item}")
    lines.append("")
    lines.append("## Page Steps")
    for row in payload.get("page_steps", []):
        lines.append(f"- {row.get('slug')} [{row.get('calculator_policy')}]: {row.get('required_step')}")
        lines.append(f"  - wordpress_page_slug: {row.get('wordpress_page_slug') or '(none)'}")
        lines.append(f"  - blueprint: {row.get('blueprint_file') or '(none)'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the staging apply plan for the WordPress/Astra platform rollout.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--blueprints", type=Path, default=DEFAULT_BLUEPRINTS)
    parser.add_argument("--cutover", type=Path, default=DEFAULT_CUTOVER)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--runtime-validation", type=Path, default=DEFAULT_RUNTIME_VALIDATION)
    parser.add_argument("--php-runtime", type=Path, default=DEFAULT_PHP_RUNTIME)
    parser.add_argument("--php-fallback", type=Path, default=DEFAULT_PHP_FALLBACK)
    parser.add_argument("--wp-apply", type=Path, default=DEFAULT_WP_APPLY)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wordpress_staging_apply_plan_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wordpress_staging_apply_plan_latest.md")
    args = parser.parse_args()

    payload = build_wordpress_staging_apply_plan(
        ia_path=args.ia,
        blueprints_path=args.blueprints,
        cutover_path=args.cutover,
        runtime_path=args.runtime,
        runtime_validation_path=args.runtime_validation,
        php_runtime_path=args.php_runtime,
        php_fallback_path=args.php_fallback,
        wp_apply_path=args.wp_apply,
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
