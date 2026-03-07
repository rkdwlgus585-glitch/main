#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANNELS = ROOT / "tenant_config" / "channel_profiles.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _find_channel(payload: Dict[str, Any], channel_id: str) -> Dict[str, Any]:
    wanted = str(channel_id or "").strip().lower()
    for row in payload.get("channels") or []:
        if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == wanted:
            return row
    return {}


def _host(url: str, fallback: str = "") -> str:
    raw = str(url or "").strip()
    if not raw:
        return fallback
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return str(parsed.netloc or fallback).strip()


def build_private_engine_proxy_spec(*, channels_path: Path, channel_id: str) -> Dict[str, Any]:
    payload = _load_json(channels_path)
    channel = _find_channel(payload, channel_id)
    if not channel:
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "error": "channel_not_found",
            "channel_id": channel_id,
        }

    canonical_host = _host(str(channel.get("canonical_public_host") or ""), "seoulmna.kr")
    listing_host = _host(str(channel.get("legacy_content_host") or ""), "seoulmna.co.kr")
    private_origin = str(channel.get("engine_origin") or "").strip().rstrip("/")
    public_mount = str(channel.get("public_calculator_mount_base") or f"https://{canonical_host}/_calc").strip().rstrip("/")
    parsed_private = urlparse(private_origin if "://" in private_origin else f"https://{private_origin}")
    upstream_base = f"{parsed_private.scheme}://{parsed_private.netloc}".rstrip("/")
    upstream_widgets = str(channel.get("embed_base_url") or f"{upstream_base}/widgets").strip().rstrip("/")
    public_mount_path = urlparse(public_mount if "://" in public_mount else f"https://{public_mount}").path.rstrip("/") or "/_calc"

    nginx = "\n".join(
        [
            f"location {public_mount_path}/ {{",
            f"    proxy_pass {upstream_widgets}/;",
            "    proxy_http_version 1.1;",
            "    proxy_set_header Host $host;",
            "    proxy_set_header X-Real-IP $remote_addr;",
            "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "    proxy_set_header X-Forwarded-Proto $scheme;",
            "    proxy_set_header X-Forwarded-Host $host;",
            "    proxy_set_header X-Forwarded-Prefix /_calc;",
            "    proxy_set_header X-SeoulMNA-Private-Engine 1;",
            "    proxy_buffering on;",
            "    add_header Cache-Control \"private, no-store\" always;",
            "}",
        ]
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": True,
        "channel_id": str(channel.get("channel_id") or channel_id).strip().lower(),
        "topology": {
            "main_platform_host": canonical_host,
            "listing_market_host": listing_host,
            "public_mount_base": public_mount,
            "public_mount_path": public_mount_path,
            "private_engine_origin": private_origin,
            "private_engine_upstream_widgets": upstream_widgets,
        },
        "decision": {
            "public_contract": f"https://{canonical_host}{public_mount_path}/*",
            "listing_policy": f"https://{listing_host} remains listing-only and should link users back to https://{canonical_host}/yangdo or /permit.",
            "engine_visibility": "hidden_origin_only",
        },
        "nginx": {
            "location_block": nginx,
        },
        "next_actions": [
            "Apply the reverse proxy block on the .kr web server before exposing calculator traffic publicly.",
            "Keep WordPress service pages pointed at the .kr /_calc mount rather than the raw engine origin.",
            "Keep seoulmna.co.kr focused on listings and route calculator demand back to .kr service pages.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    if not payload.get("ok"):
        return "# Private Engine Proxy Spec\n\n- error: channel_not_found\n"
    topology = payload.get("topology") if isinstance(payload.get("topology"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    nginx = payload.get("nginx") if isinstance(payload.get("nginx"), dict) else {}
    lines = [
        "# Private Engine Proxy Spec",
        "",
        f"- main_platform_host: {topology.get('main_platform_host') or '(none)'}",
        f"- listing_market_host: {topology.get('listing_market_host') or '(none)'}",
        f"- public_mount_base: {topology.get('public_mount_base') or '(none)'}",
        f"- private_engine_origin: {topology.get('private_engine_origin') or '(none)'}",
        f"- private_engine_upstream_widgets: {topology.get('private_engine_upstream_widgets') or '(none)'}",
        f"- public_contract: {decision.get('public_contract') or '(none)'}",
        "",
        "## Nginx",
        "```nginx",
        str(nginx.get("location_block") or "").strip(),
        "```",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the private engine reverse proxy spec for SeoulMNA.")
    parser.add_argument("--channels", type=Path, default=DEFAULT_CHANNELS)
    parser.add_argument("--channel-id", default="seoul_web")
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "private_engine_proxy_spec_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "private_engine_proxy_spec_latest.md")
    args = parser.parse_args()

    payload = build_private_engine_proxy_spec(channels_path=args.channels, channel_id=args.channel_id)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
