#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_widget_snippet import build_widget_payload
from scripts.plan_channel_embed import DEFAULT_CHANNELS, DEFAULT_ENV, DEFAULT_REGISTRY
from scripts.validate_tenant_onboarding import _load_json
from scripts.widget_health_contract import load_widget_health_contract

DEFAULT_OUTPUT_DIR = ROOT / "output" / "widget" / "bundles"


def _channel_row(channels_path: str, channel_id: str) -> dict:
    rows = _load_json(Path(str(channels_path or DEFAULT_CHANNELS)).resolve()).get("channels") or []
    wanted = str(channel_id or "").strip().lower()
    for row in rows:
        if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _preferred_host(row: dict) -> str:
    explicit = str(row.get("canonical_public_host") or "").strip()
    if explicit:
        return explicit.split(":", 1)[0].lower()
    branding = row.get("branding") if isinstance(row.get("branding"), dict) else {}
    site_url = str(branding.get("site_url") or "").strip()
    if site_url:
        try:
            parsed = urlparse(site_url)
        except Exception:
            parsed = None
        candidate = str(parsed.netloc if parsed else "").strip().lower()
        if candidate:
            return candidate.split(":", 1)[0]
    hosts = row.get("channel_hosts") if isinstance(row.get("channel_hosts"), list) else []
    return str(hosts[0] or "").strip() if hosts else ""


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())


def build_widget_bundle(
    *,
    channel_id: str,
    tenant_id: str = "",
    widgets: list[str] | None = None,
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
    output_dir: str = "",
    allow_disabled: bool = False,
) -> dict:
    channels_file = str(channels_path or DEFAULT_CHANNELS)
    row = _channel_row(channels_file, channel_id)
    if not row:
        return {"ok": False, "error": "channel_not_found", "channel_id": channel_id}

    channel_id = str(row.get("channel_id") or channel_id).strip().lower()
    host = _preferred_host(row)
    exposed = [str(x or "").strip().lower() for x in (row.get("exposed_systems") or []) if str(x or "").strip()]
    requested_widgets = [str(x or "").strip().lower() for x in (widgets or exposed) if str(x or "").strip()]
    requested_widgets = [x for x in requested_widgets if x in {"yangdo", "permit"}]
    if not requested_widgets:
        return {"ok": False, "error": "no_widgets_requested", "channel_id": channel_id}

    bundle_dir = Path(str(output_dir or DEFAULT_OUTPUT_DIR)).resolve() / channel_id
    manifest = {
        "ok": True,
        "channel_id": channel_id,
        "tenant_id": str(tenant_id or row.get("default_tenant_id") or "").strip(),
        "host": host,
        "canonical_public_host": str(row.get("canonical_public_host") or host).strip(),
        "public_host_policy": str(row.get("public_host_policy") or "dual_host").strip().lower() or "dual_host",
        "widgets": [],
        "activation_blockers": [],
        "output_dir": str(bundle_dir),
        "health_contract": load_widget_health_contract(),
    }

    for widget in requested_widgets:
        iframe_payload = build_widget_payload(
            host=host,
            channel_id=channel_id,
            tenant_id=tenant_id,
            widget=widget,
            mode="iframe",
            registry_path=registry_path or str(DEFAULT_REGISTRY),
            channels_path=channels_file,
            env_path=env_path or str(DEFAULT_ENV),
        )
        launcher_payload = build_widget_payload(
            host=host,
            channel_id=channel_id,
            tenant_id=tenant_id,
            widget=widget,
            mode="launcher",
            registry_path=registry_path or str(DEFAULT_REGISTRY),
            channels_path=channels_file,
            env_path=env_path or str(DEFAULT_ENV),
        )
        blockers = sorted({str(x) for x in iframe_payload.get("activation_blockers") or []})
        widget_ok = bool(iframe_payload.get("ok")) and bool(launcher_payload.get("ok"))
        if blockers:
            manifest["activation_blockers"].extend(blockers)
        if not widget_ok and not allow_disabled:
            manifest["ok"] = False
        iframe_path = bundle_dir / f"{widget}.iframe.html"
        launcher_path = bundle_dir / f"{widget}.launcher.html"
        widget_entry = {
            "widget": widget,
            "ok": widget_ok,
            "widget_url": str(iframe_payload.get("widget_url") or ""),
            "activation_blockers": blockers,
            "iframe_path": _write_text(iframe_path, str(iframe_payload.get("snippet") or "")),
            "launcher_path": _write_text(launcher_path, str(launcher_payload.get("snippet") or "")),
        }
        manifest["widgets"].append(widget_entry)

    manifest["activation_blockers"] = sorted({str(x) for x in manifest["activation_blockers"] if str(x).strip()})
    manifest_path = bundle_dir / "manifest.json"
    manifest["manifest_path"] = _write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    if manifest["activation_blockers"] and not allow_disabled:
        manifest["note"] = "bundle generated with blocked widgets; activate channel/tenant before embedding"
    else:
        manifest["note"] = "bundle ready"
    Path(manifest["manifest_path"]).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish iframe/launcher widget bundle for a channel")
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--tenant-id", default="")
    parser.add_argument("--widget", action="append", default=[])
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-disabled", action="store_true", default=False)
    args = parser.parse_args()

    manifest = build_widget_bundle(
        channel_id=args.channel_id,
        tenant_id=args.tenant_id,
        widgets=args.widget,
        registry_path=args.registry,
        channels_path=args.channels,
        env_path=args.env_file,
        output_dir=args.output_dir,
        allow_disabled=bool(args.allow_disabled),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
