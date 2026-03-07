#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROXY_SPEC = ROOT / "logs" / "private_engine_proxy_spec_latest.json"
DEFAULT_WP_ASSETS = ROOT / "logs" / "wp_platform_assets_latest.json"
DEFAULT_WP_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_TRAFFIC = ROOT / "logs" / "kr_traffic_gate_audit_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_kr_reverse_proxy_cutover(
    *,
    proxy_spec_path: Path,
    wp_assets_path: Path,
    wp_ia_path: Path,
    traffic_path: Path,
) -> Dict[str, Any]:
    proxy_spec = _load_json(proxy_spec_path)
    wp_assets = _load_json(wp_assets_path)
    wp_ia = _load_json(wp_ia_path)
    traffic = _load_json(traffic_path)

    topology = proxy_spec.get("topology", {}) if isinstance(proxy_spec.get("topology"), dict) else {}
    decision = proxy_spec.get("decision", {}) if isinstance(proxy_spec.get("decision"), dict) else {}
    nginx = proxy_spec.get("nginx", {}) if isinstance(proxy_spec.get("nginx"), dict) else {}
    pages = list(wp_ia.get("pages") or [])
    service_pages = [row for row in pages if row.get("calculator_policy") == "lazy_gate_shortcode"]
    cta_only_pages = [row for row in pages if row.get("calculator_policy") == "cta_only_no_iframe"]
    traffic_ok = bool(traffic.get("decision", {}).get("traffic_leak_blocked"))
    theme_ready = bool(wp_assets.get("summary", {}).get("theme_ready"))
    plugin_ready = bool(wp_assets.get("summary", {}).get("plugin_ready"))
    cutover_ready = bool(topology) and theme_ready and plugin_ready and traffic_ok and bool(service_pages)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "cutover_ready": cutover_ready,
            "service_page_count": len(service_pages),
            "cta_only_page_count": len(cta_only_pages),
            "traffic_gate_ok": traffic_ok,
            "theme_ready": theme_ready,
            "plugin_ready": plugin_ready,
        },
        "topology": {
            "platform_host": str(topology.get("main_platform_host") or "seoulmna.kr"),
            "listing_host": str(topology.get("listing_market_host") or "seoulmna.co.kr"),
            "public_mount_base": str(topology.get("public_mount_base") or "https://seoulmna.kr/_calc"),
            "private_engine_origin": str(topology.get("private_engine_origin") or ""),
            "public_contract": str(decision.get("public_contract") or ""),
        },
        "preflight": [
            "Back up the current WordPress database and uploads before changing the theme or plugin set.",
            "Apply the seoulmna-platform-child theme and seoulmna-platform-bridge plugin in staging first.",
            "Confirm homepage and knowledge pages remain CTA-only with no initial iframe markup.",
        ],
        "wordpress_changes": [
            f"Create or update {row.get('slug')} using the matching blueprint and calculator policy {row.get('calculator_policy')}."
            for row in pages
        ],
        "server_changes": [
            "Install the reverse proxy block for /_calc/ before exposing any calculator entry on public pages.",
            "Bypass page cache and full-page HTML caching for /_calc/* so engine responses are never cached as WordPress content.",
            "Keep the raw private engine origin non-public and route all public traffic through the .kr mount only.",
            str(nginx.get("location_block") or "").strip(),
        ],
        "verification": [
            "Open the homepage and confirm no iframe exists before any click.",
            "Open /yangdo and /permit and confirm the iframe is created only after button click.",
            "Confirm the iframe source resolves to seoulmna.kr/_calc/* rather than a raw engine hostname.",
            "Confirm seoulmna.co.kr listing pages link back to .kr service pages instead of embedding calculators inline.",
        ],
        "rollback": {
            "trigger": "If public calculator pages create iframe traffic before click, or if .co.kr starts acting like the calculator runtime.",
            "actions": [
                "Disable the seoulmna-platform-bridge plugin.",
                "Revert the child theme activation or restore the previous Astra customization snapshot.",
                "Remove the /_calc/ reverse proxy block and restore the previous web server config backup.",
            ],
        },
        "next_actions": [
            "Run the cutover in staging first with the generated WordPress blueprints.",
            "After staging validation, apply the same child theme/plugin and reverse proxy block in production.",
            "Keep .co.kr listing-focused and route all service demand back to .kr pages.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# KR Reverse Proxy Cutover",
        "",
        f"- cutover_ready: {payload.get('summary', {}).get('cutover_ready')}",
        f"- public_mount_base: {payload.get('topology', {}).get('public_mount_base')}",
        f"- private_engine_origin: {payload.get('topology', {}).get('private_engine_origin')}",
        "",
        "## Preflight",
    ]
    for item in payload.get("preflight", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Verification")
    for item in payload.get("verification", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the .kr reverse proxy cutover checklist.")
    parser.add_argument("--proxy-spec", type=Path, default=DEFAULT_PROXY_SPEC)
    parser.add_argument("--wp-assets", type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument("--wp-ia", type=Path, default=DEFAULT_WP_IA)
    parser.add_argument("--traffic", type=Path, default=DEFAULT_TRAFFIC)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "kr_reverse_proxy_cutover_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "kr_reverse_proxy_cutover_latest.md")
    args = parser.parse_args()

    payload = build_kr_reverse_proxy_cutover(
        proxy_spec_path=args.proxy_spec,
        wp_assets_path=args.wp_assets,
        wp_ia_path=args.wp_ia,
        traffic_path=args.traffic,
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
