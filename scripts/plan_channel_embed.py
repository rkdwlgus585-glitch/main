#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tenant_config.loader import load_channel_router, load_gateway
from scripts.validate_tenant_onboarding import _load_env_file, _load_json, validate_registry

DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_CHANNELS = ROOT / "tenant_config" / "channel_profiles.json"
DEFAULT_ENV = ROOT / ".env"


def _pick_tenant(host: str, preferred_tenant: str, *, registry_path: str = "") -> str:
    gw = load_gateway(strict=False, config_path=registry_path)
    if preferred_tenant:
        return preferred_tenant
    resolution = gw.resolve(host=host, origin="")
    if resolution.tenant is not None:
        return str(resolution.tenant.tenant_id or "").strip()
    return ""


def _build_embed(embed_base_url: str, tenant_id: str, widget: str) -> str:
    endpoint = f"{embed_base_url.rstrip('/')}/{widget.strip('/')}"
    return (
        f'<iframe src="{endpoint}?tenant_id={tenant_id}" title="SMNA calculator widget" '
        'style="width:100%;min-height:1200px;border:0" '
        'sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox" '
        'allow="clipboard-write" '
        'loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe>'
    )


def _preferred_public_host(profile) -> str:
    host = str(getattr(profile, "canonical_public_host", "") or "").strip().lower()
    if host:
        return host
    hosts = list(getattr(profile, "channel_hosts", ()) or ())
    return str(hosts[0] or "").strip().lower() if hosts else ""


def _find_row(rows, key: str, value: str) -> dict:
    wanted = str(value or "").strip().lower()
    for row in rows or []:
        if str((row or {}).get(key) or "").strip().lower() == wanted:
            return dict(row)
    return {}


def plan_embed(
    *,
    host: str,
    origin: str = "",
    tenant_id: str = "",
    widget: str = "yangdo",
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
) -> dict:
    host = str(host or "").strip()
    origin = str(origin or "").strip()
    tenant_id = str(tenant_id or "").strip()
    widget = str(widget or "yangdo").strip().lower()
    registry_file = Path(str(registry_path or DEFAULT_REGISTRY)).resolve()
    channels_file = Path(str(channels_path or DEFAULT_CHANNELS)).resolve()
    env_file = Path(str(env_path or DEFAULT_ENV)).resolve()

    router = load_channel_router(strict=False, config_path=str(channels_file))
    resolution = router.resolve(host=host, origin=origin)
    profile = resolution.profile

    out = {
        "ok": False,
        "host": host,
        "origin": origin,
        "channel_id": "",
        "channel_role": "",
        "canonical_public_host": "",
        "public_host_policy": "",
        "platform_front_host": "",
        "legacy_content_host": "",
        "channel_enabled": False,
        "channel_exposed_systems": [],
        "engine_origin": "",
        "embed_base_url": "",
        "widget_url": "",
        "tenant_id": "",
        "tenant_allowed_systems": [],
        "widget": widget,
        "requested_system": "",
        "requested_system_allowed": None,
        "rollout_stage": "",
        "tenant_activation_ready": None,
        "channel_activation_ready": None,
        "activation_blockers": [],
        "embed_mode": "iframe",
        "embed_snippet": "",
        "note": "",
    }

    if profile is None:
        out["note"] = "channel profile not found; register host in tenant_config/channel_profiles.json"
        return out

    if not tenant_id:
        tenant_id = _pick_tenant(host=host, preferred_tenant="", registry_path=str(registry_file))
    if not tenant_id:
        tenant_id = str(profile.default_tenant_id or "").strip()

    out["ok"] = bool(tenant_id)
    out["channel_id"] = str(profile.channel_id or "")
    out["channel_role"] = str(getattr(profile, "channel_role", "") or "").strip().lower()
    out["canonical_public_host"] = _preferred_public_host(profile)
    out["public_host_policy"] = str(getattr(profile, "public_host_policy", "") or "").strip().lower()
    out["platform_front_host"] = str(getattr(profile, "platform_front_host", "") or "").strip().lower()
    out["legacy_content_host"] = str(getattr(profile, "legacy_content_host", "") or "").strip().lower()
    out["channel_enabled"] = bool(getattr(profile, "enabled", True))
    out["channel_exposed_systems"] = sorted(
        {str(x or "").strip().lower() for x in getattr(profile, "exposed_systems", set()) if str(x or "").strip()}
    )
    out["engine_origin"] = str(profile.engine_origin or "")
    out["embed_base_url"] = str(profile.embed_base_url or "")
    out["rollout_stage"] = str(profile.rollout_stage or "")
    out["tenant_id"] = tenant_id
    if tenant_id:
        out["widget_url"] = f"{str(profile.embed_base_url or '').rstrip('/')}/{widget}?tenant_id={tenant_id}"
        out["embed_snippet"] = _build_embed(str(profile.embed_base_url or ""), tenant_id, widget)

    registry = _load_json(registry_file)
    channels = _load_json(channels_file)
    env_values = _load_env_file(env_file)
    env_values.update({k: v for k, v in os.environ.items() if isinstance(v, str)})
    report = validate_registry(registry, env_values=env_values, channel_registry=channels)
    tenant_row = _find_row(report.get("tenants"), "tenant_id", tenant_id)
    channel_row = _find_row(report.get("channels"), "channel_id", out["channel_id"])
    blockers = list(tenant_row.get("activation_blockers") or [])
    blockers.extend(list(channel_row.get("activation_blockers") or []))
    out["tenant_allowed_systems"] = sorted(
        {str(x or "").strip().lower() for x in (tenant_row.get("allowed_systems") or []) if str(x or "").strip()}
    )
    out["tenant_activation_ready"] = tenant_row.get("activation_ready")
    out["channel_activation_ready"] = channel_row.get("activation_ready")
    out["activation_blockers"] = sorted({str(x) for x in blockers if str(x).strip()})
    widget_system = "permit" if widget == "permit" else "yangdo"
    out["requested_system"] = widget_system
    out["requested_system_allowed"] = (
        widget_system in set(out["channel_exposed_systems"]) and widget_system in set(out["tenant_allowed_systems"])
    )
    if out["channel_exposed_systems"] and widget_system not in set(out["channel_exposed_systems"]):
        out["ok"] = False
        out["note"] = "channel does not expose requested system"
        out["embed_snippet"] = ""
    elif out["tenant_allowed_systems"] and widget_system not in set(out["tenant_allowed_systems"]):
        out["ok"] = False
        out["note"] = "tenant does not allow requested system"
        out["embed_snippet"] = ""
    if not bool(getattr(profile, "enabled", True)):
        out["ok"] = False
        out["note"] = "channel disabled; onboarding not ready"
        out["embed_snippet"] = ""
    elif out["activation_blockers"]:
        out["ok"] = False
        out["note"] = "activation blockers remain"
        out["embed_snippet"] = ""
    else:
        out["note"] = (
            "channel-engine separated plan ready"
            if tenant_id
            else "tenant not resolved; pass --tenant-id or register tenant host in tenant registry"
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan channel->engine embed snippet for calculator rollout")
    parser.add_argument("--host", required=True, help="Channel host (e.g. seoulmna.kr)")
    parser.add_argument("--origin", default="", help="Optional channel origin URL")
    parser.add_argument("--tenant-id", default="", help="Optional explicit tenant id")
    parser.add_argument("--widget", default="yangdo", choices=["yangdo", "permit"], help="Widget id to embed")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    args = parser.parse_args()

    out = plan_embed(
        host=args.host,
        origin=args.origin,
        tenant_id=str(args.tenant_id or "").strip(),
        widget=args.widget,
        registry_path=args.registry,
        channels_path=args.channels,
        env_path=args.env_file,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
