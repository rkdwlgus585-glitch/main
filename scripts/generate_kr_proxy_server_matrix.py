#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROXY_SPEC = ROOT / "logs" / "private_engine_proxy_spec_latest.json"
DEFAULT_TRAFFIC = ROOT / "logs" / "kr_traffic_gate_audit_latest.json"
DEFAULT_CUTOVER = ROOT / "logs" / "kr_reverse_proxy_cutover_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_kr_proxy_server_matrix(*, proxy_spec_path: Path, traffic_path: Path, cutover_path: Path) -> Dict[str, Any]:
    proxy = _load_json(proxy_spec_path)
    traffic = _load_json(traffic_path)
    cutover = _load_json(cutover_path)

    topo = proxy.get("topology", {}) if isinstance(proxy.get("topology"), dict) else {}
    public_mount = str(topo.get("public_mount_path") or "/_calc")
    upstream = str(topo.get("private_engine_origin") or "https://calc.seoulmna.co.kr")
    traffic_ok = bool(traffic.get("decision", {}).get("traffic_leak_blocked"))
    cutover_ready = bool(cutover.get("summary", {}).get("cutover_ready"))

    nginx = "\n".join([
        f"location {public_mount}/ {{",
        f"    proxy_pass {upstream}/widgets/;",
        "    proxy_http_version 1.1;",
        "    proxy_set_header Host $host;",
        "    proxy_set_header X-Real-IP $remote_addr;",
        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "    proxy_set_header X-Forwarded-Proto $scheme;",
        "    proxy_set_header X-Forwarded-Host $host;",
        f"    proxy_set_header X-Forwarded-Prefix {public_mount};",
        "    proxy_set_header X-SeoulMNA-Private-Engine 1;",
        "    proxy_buffering on;",
        "    proxy_read_timeout 90s;",
        '    add_header Cache-Control "private, no-store" always;',
        "}",
    ])

    apache = "\n".join([
        f'ProxyPass "{public_mount}/" "{upstream}/widgets/"',
        f'ProxyPassReverse "{public_mount}/" "{upstream}/widgets/"',
        f'RequestHeader set X-Forwarded-Prefix "{public_mount}"',
        'RequestHeader set X-SeoulMNA-Private-Engine "1"',
        'Header always set Cache-Control "private, no-store"',
    ])

    cloudflare = {
        "cache_rules": [
            {"match": f"*seoulmna.kr{public_mount}*", "action": "bypass_cache"},
            {"match": "*seoulmna.kr/yangdo*", "action": "respect_origin_no_initial_iframe"},
            {"match": "*seoulmna.kr/permit*", "action": "respect_origin_no_initial_iframe"},
        ],
        "security_notes": [
            "Do not expose the raw engine origin in DNS records advertised to users.",
            "Keep WAF/bot rules on the public .kr host and forward only the mounted path upstream.",
        ],
    }

    wordpress_cache = {
        "bypass_paths": [f"{public_mount}/*"],
        "notes": [
            "Exclude /_calc/* from page caching plugins and full-page cache layers.",
            "Service pages may be cached as HTML, but the calculator iframe must still be lazy-inserted after click.",
        ],
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "traffic_gate_ok": traffic_ok,
            "cutover_ready": cutover_ready,
            "public_mount_path": public_mount,
            "upstream_origin": upstream,
            "matrix_ready": True,
        },
        "nginx": {"snippet": nginx},
        "apache": {"snippet": apache},
        "cloudflare": cloudflare,
        "wordpress_cache": wordpress_cache,
        "verification": [
            "Confirm /_calc/* responses are never cached as WordPress HTML.",
            "Confirm homepage and knowledge pages still contain no iframe before click.",
            "Confirm the iframe src resolves to the mounted /_calc path, not the raw upstream origin.",
        ],
        "rollback": [
            "Remove the /_calc reverse proxy block from the web server config.",
            "Restore the previous server config backup and reload the web server.",
            "Disable the bridge plugin if service pages start creating traffic before click.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# KR Proxy Server Matrix",
        "",
        f"- public_mount_path: {payload.get('summary', {}).get('public_mount_path')}",
        f"- upstream_origin: {payload.get('summary', {}).get('upstream_origin')}",
        f"- traffic_gate_ok: {payload.get('summary', {}).get('traffic_gate_ok')}",
        f"- cutover_ready: {payload.get('summary', {}).get('cutover_ready')}",
        "",
        "## Nginx",
        "```nginx",
        str(payload.get('nginx', {}).get('snippet') or '').rstrip(),
        "```",
        "",
        "## Apache",
        "```apache",
        str(payload.get('apache', {}).get('snippet') or '').rstrip(),
        "```",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate server config variants for the .kr /_calc reverse proxy.")
    parser.add_argument("--proxy-spec", type=Path, default=DEFAULT_PROXY_SPEC)
    parser.add_argument("--traffic", type=Path, default=DEFAULT_TRAFFIC)
    parser.add_argument("--cutover", type=Path, default=DEFAULT_CUTOVER)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "kr_proxy_server_matrix_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "kr_proxy_server_matrix_latest.md")
    args = parser.parse_args()

    payload = build_kr_proxy_server_matrix(
        proxy_spec_path=args.proxy_spec,
        traffic_path=args.traffic,
        cutover_path=args.cutover,
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
