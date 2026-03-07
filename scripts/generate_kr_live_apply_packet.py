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
DEFAULT_WP_ASSETS = ROOT / "logs" / "wp_platform_assets_latest.json"
DEFAULT_WP_APPLY = ROOT / "logs" / "wp_surface_lab_apply_latest.json"
DEFAULT_WP_CYCLE = ROOT / "logs" / "wp_surface_lab_apply_verify_cycle_latest.json"
DEFAULT_CUTOVER = ROOT / "logs" / "kr_reverse_proxy_cutover_latest.json"
DEFAULT_PROXY_MATRIX = ROOT / "logs" / "kr_proxy_server_matrix_latest.json"
DEFAULT_BRIDGE_POLICY = ROOT / "logs" / "listing_platform_bridge_policy_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _looks_mojibake(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    return value.count("?") >= 2 or "\ufffd" in value


def _safe_menu_name(value: str) -> str:
    text = str(value or "").strip()
    if not text or _looks_mojibake(text):
        return "서울건설정보 플랫폼"
    return text


def build_kr_live_apply_packet(*, ia_path: Path, blueprints_path: Path, wp_assets_path: Path, wp_apply_path: Path, wp_cycle_path: Path, cutover_path: Path, proxy_matrix_path: Path, bridge_policy_path: Path) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    blueprints = _load_json(blueprints_path)
    assets = _load_json(wp_assets_path)
    wp_apply = _load_json(wp_apply_path)
    cycle = _load_json(wp_cycle_path)
    cutover = _load_json(cutover_path)
    proxy_matrix = _load_json(proxy_matrix_path)
    bridge_policy = _load_json(bridge_policy_path)

    pages = list(ia.get("pages") or [])
    manifest = wp_apply.get("manifest") if isinstance(wp_apply.get("manifest"), dict) else {}
    menu = manifest.get("menu") if isinstance(manifest.get("menu"), dict) else {}
    ctas = bridge_policy.get("ctas") if isinstance(bridge_policy.get("ctas"), list) else []

    wordpress_steps: List[Dict[str, Any]] = [
        {
            "step": 1,
            "area": "backup",
            "action": "Back up the current WordPress database, uploads, and Astra customization snapshot.",
            "rollback": "Restore the DB/files backup and reactivate the previous theme state.",
        },
        {
            "step": 2,
            "area": "theme",
            "action": f"Activate the child theme {assets.get('theme', {}).get('slug') or 'seoulmna-platform-child'} on staging first, then production.",
            "rollback": "Reactivate the previous Astra-based theme/customizer export.",
        },
        {
            "step": 3,
            "area": "plugin",
            "action": f"Activate the bridge plugin {assets.get('plugin', {}).get('slug') or 'seoulmna-platform-bridge'} and keep it as the only calculator mount plugin.",
            "rollback": "Deactivate the bridge plugin immediately if service pages create iframe traffic before click.",
        },
        {
            "step": 4,
            "area": "pages",
            "action": "Import or upsert the six platform pages from the generated blueprints using the apply bundle.",
            "details": [f"{row.get('wordpress_page_slug')} <- {row.get('blueprint_file')}" for row in blueprints.get('pages', [])],
            "rollback": "Restore the previous page revisions or import the pre-cutover page export.",
        },
        {
            "step": 5,
            "area": "front_page",
            "action": f"Set the WordPress front page to {manifest.get('front_page_slug') or ia.get('summary', {}).get('front_page_slug') or 'home'} and attach the primary menu {_safe_menu_name(menu.get('name') or '')}.",
            "rollback": "Restore the previous front page and menu location assignments.",
        },
        {
            "step": 6,
            "area": "cache",
            "action": "Exclude /_calc/* from any page cache layer and confirm homepage/knowledge pages remain CTA-only.",
            "rollback": "Restore the previous cache profile and remove the new bypass rule if service mounts are disabled.",
        },
    ]

    server_steps = [
        {
            "stack": "nginx",
            "action": "Install the /_calc reverse proxy block on the .kr server.",
            "snippet": str(proxy_matrix.get('nginx', {}).get('snippet') or '').strip(),
        },
        {
            "stack": "apache",
            "action": "If Apache fronts the site, use the equivalent ProxyPass/ProxyPassReverse mount.",
            "snippet": str(proxy_matrix.get('apache', {}).get('snippet') or '').strip(),
        },
        {
            "stack": "cloudflare",
            "action": "Bypass cache for /_calc/* and keep WAF/bot rules on the public .kr host only.",
            "details": list(proxy_matrix.get('cloudflare', {}).get('cache_rules') or []),
        },
    ]

    publish_validation = [
        "Open / and confirm no iframe exists before click.",
        "Open /yangdo and /permit and confirm the calculator iframe is created only after button click.",
        "Confirm the iframe src starts with https://seoulmna.kr/_calc/ and never exposes the raw upstream origin.",
        "Confirm /mna-market points users to seoulmna.co.kr and back to .kr/yangdo with tracked links.",
    ]

    bridge_handoff = [
        {
            "placement": row.get("placement"),
            "target_url": row.get("target_url"),
            "copy": row.get("copy"),
        }
        for row in ctas
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "apply_packet_ready": bool(cycle.get("summary", {}).get("ok")) and bool(cutover.get("summary", {}).get("cutover_ready")),
            "page_count": len(pages),
            "service_page_count": len([row for row in pages if row.get("calculator_policy") == "lazy_gate_shortcode"]),
            "front_page_slug": manifest.get("front_page_slug") or ia.get("summary", {}).get("front_page_slug") or "home",
            "menu_name": _safe_menu_name(menu.get("name") or ""),
            "bridge_cta_count": len(bridge_handoff),
        },
        "wordpress_steps": wordpress_steps,
        "server_steps": server_steps,
        "publish_validation": publish_validation,
        "bridge_handoff": bridge_handoff,
        "rollback_map": {
            "theme": "Revert to the previous Astra customization snapshot or prior active theme.",
            "plugin": "Deactivate seoulmna-platform-bridge.",
            "pages": "Restore WordPress page revisions/export taken before cutover.",
            "server": "Restore the previous server config backup and reload the web server.",
        },
        "operator_inputs": [
            "confirm_live_yes",
        ],
        "next_actions": [
            "Apply the child theme and bridge plugin in staging, then run the generated apply bundle.",
            "Install the /_calc reverse proxy before publishing the service pages.",
            "Use the bridge CTA set on .co.kr so listing demand always returns to .kr service pages.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# KR Live Apply Packet",
        "",
        f"- apply_packet_ready: {payload.get('summary', {}).get('apply_packet_ready')}",
        f"- front_page_slug: {payload.get('summary', {}).get('front_page_slug')}",
        f"- menu_name: {payload.get('summary', {}).get('menu_name')}",
        "",
        "## WordPress Steps",
    ]
    for row in payload.get("wordpress_steps", []):
        lines.append(f"- [{row.get('step')}] {row.get('area')}: {row.get('action')}")
    lines.extend(["", "## Server Steps"])
    for row in payload.get("server_steps", []):
        lines.append(f"- {row.get('stack')}: {row.get('action')}")
    lines.extend(["", "## Publish Validation"])
    for row in payload.get("publish_validation", []):
        lines.append(f"- {row}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the live apply packet for the WordPress/Astra .kr platform.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--blueprints", type=Path, default=DEFAULT_BLUEPRINTS)
    parser.add_argument("--wp-assets", type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument("--wp-apply", type=Path, default=DEFAULT_WP_APPLY)
    parser.add_argument("--wp-cycle", type=Path, default=DEFAULT_WP_CYCLE)
    parser.add_argument("--cutover", type=Path, default=DEFAULT_CUTOVER)
    parser.add_argument("--proxy-matrix", type=Path, default=DEFAULT_PROXY_MATRIX)
    parser.add_argument("--bridge-policy", type=Path, default=DEFAULT_BRIDGE_POLICY)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "kr_live_apply_packet_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "kr_live_apply_packet_latest.md")
    args = parser.parse_args()

    payload = build_kr_live_apply_packet(
        ia_path=args.ia,
        blueprints_path=args.blueprints,
        wp_assets_path=args.wp_assets,
        wp_apply_path=args.wp_apply,
        wp_cycle_path=args.wp_cycle,
        cutover_path=args.cutover,
        proxy_matrix_path=args.proxy_matrix,
        bridge_policy_path=args.bridge_policy,
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
