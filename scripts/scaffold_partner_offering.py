#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_tenant_onboarding import _load_json, _load_env_file, validate_registry

DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_CHANNELS = ROOT / "tenant_config" / "channel_profiles.json"
DEFAULT_ENV = ROOT / ".env"


def _slugify(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "_", str(text or "").strip().lower()).strip("_")


def _find_offering(registry: dict, offering_id: str) -> dict:
    rows = registry.get("offering_templates") if isinstance(registry, dict) else []
    wanted = str(offering_id or "").strip().lower()
    for row in rows or []:
        if isinstance(row, dict) and str(row.get("offering_id") or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _find_default_channel(channel_registry: dict) -> dict:
    wanted = str((channel_registry or {}).get("default_channel_id") or "").strip().lower()
    for row in (channel_registry.get("channels") or []):
        if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _find_existing(rows: list[dict], key: str, value: str) -> dict:
    wanted = str(value or "").strip().lower()
    for row in rows or []:
        if isinstance(row, dict) and str(row.get(key) or "").strip().lower() == wanted:
            return dict(row)
    return {}


def build_partner_scaffold(
    *,
    offering_id: str,
    tenant_id: str,
    channel_id: str,
    host: str,
    brand_name: str,
    brand_label: str = "",
    contact_email: str = "",
    contact_phone: str = "010-0000-0000",
    site_url: str = "",
    notice_url: str = "",
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
) -> dict:
    registry_file = Path(str(registry_path or DEFAULT_REGISTRY)).resolve()
    channels_file = Path(str(channels_path or DEFAULT_CHANNELS)).resolve()
    env_file = Path(str(env_path or DEFAULT_ENV)).resolve()
    registry = _load_json(registry_file)
    channel_registry = _load_json(channels_file)
    offering = _find_offering(registry, offering_id)
    if not offering:
        return {"ok": False, "error": "offering_not_found", "offering_id": offering_id}

    tenants = registry.get("tenants") if isinstance(registry, dict) else []
    channels = channel_registry.get("channels") if isinstance(channel_registry, dict) else []
    if _find_existing(tenants, "tenant_id", tenant_id):
        return {"ok": False, "error": "tenant_exists", "tenant_id": tenant_id}
    if _find_existing(channels, "channel_id", channel_id):
        return {"ok": False, "error": "channel_exists", "channel_id": channel_id}

    default_channel = _find_default_channel(channel_registry)
    engine_origin = str(default_channel.get("engine_origin") or "https://calc.seoulmna.co.kr").rstrip("/")
    embed_base_url = str(default_channel.get("embed_base_url") or f"{engine_origin}/widgets").rstrip("/")
    allowed_systems = [str(x or "").strip().lower() for x in (offering.get("allowed_systems") or []) if str(x or "").strip()]
    allowed_features = [str(x or "").strip().lower() for x in (offering.get("allowed_features") or []) if str(x or "").strip()]
    site_url = str(site_url or f"https://{host}").strip()
    notice_url = str(notice_url or site_url).strip()
    contact_email = str(contact_email or f"admin@{host}").strip()
    brand_label = str(brand_label or brand_name).strip()
    slug = _slugify(channel_id or tenant_id or host)
    api_key_env = f"TENANT_API_KEY_{_slugify(tenant_id).upper()}"
    source_id = f"{slug}_source_placeholder"

    tenant = {
        "tenant_id": tenant_id,
        "display_name": brand_name,
        "enabled": False,
        "plan": str(offering.get("plan") or "standard").strip().lower(),
        "hosts": [host],
        "origins": [site_url],
        "api_key_envs": [api_key_env],
        "blocked_api_tokens": [],
        "allowed_systems": allowed_systems,
        "allowed_features": allowed_features,
        "data_sources": [
            {
                "source_id": source_id,
                "source_name": f"{brand_name} onboarding placeholder",
                "access_mode": "partner_contract",
                "status": "pending",
                "allows_commercial_use": False,
                "contains_personal_data": False,
                "transforms": ["aggregation"],
                "proof_url": "",
            }
        ],
    }
    channel = {
        "channel_id": channel_id,
        "display_name": f"{brand_name} Channel",
        "enabled": False,
        "channel_hosts": [host],
        "engine_origin": engine_origin,
        "embed_base_url": embed_base_url,
        "branding": {
            "brand_name": brand_name,
            "brand_label": brand_label,
            "site_url": site_url,
            "notice_url": notice_url,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "openchat_url": "",
            "source_tag_prefix": slug,
        },
        "default_tenant_id": tenant_id,
        "rollout_stage": "phased",
        "exposed_systems": allowed_systems,
    }

    prospective_registry = json.loads(json.dumps(registry, ensure_ascii=False))
    prospective_registry.setdefault("tenants", []).append(tenant)
    prospective_channels = json.loads(json.dumps(channel_registry, ensure_ascii=False))
    prospective_channels.setdefault("channels", []).append(channel)

    env_values = _load_env_file(env_file)
    report = validate_registry(prospective_registry, env_values=env_values, channel_registry=prospective_channels)
    tenant_row = _find_existing(report.get("tenants") or [], "tenant_id", tenant_id)
    channel_row = _find_existing(report.get("channels") or [], "channel_id", channel_id)

    return {
        "ok": True,
        "offering_id": offering_id,
        "tenant": tenant,
        "channel": channel,
        "api_key_env": api_key_env,
        "activation_ready": False,
        "activation_blockers": sorted({
            *[str(x) for x in (tenant_row.get("activation_blockers") or []) if str(x).strip()],
            *[str(x) for x in (channel_row.get("activation_blockers") or []) if str(x).strip()],
        }),
        "apply_targets": {
            "registry": str(registry_file),
            "channels": str(channels_file),
        },
        "prospective_registry": prospective_registry,
        "prospective_channels": prospective_channels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold disabled tenant/channel pair from offering template")
    parser.add_argument("--offering-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--brand-label", default="")
    parser.add_argument("--contact-email", default="")
    parser.add_argument("--contact-phone", default="010-0000-0000")
    parser.add_argument("--site-url", default="")
    parser.add_argument("--notice-url", default="")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--apply", action="store_true", default=False)
    args = parser.parse_args()

    result = build_partner_scaffold(
        offering_id=args.offering_id,
        tenant_id=args.tenant_id,
        channel_id=args.channel_id,
        host=args.host,
        brand_name=args.brand_name,
        brand_label=args.brand_label,
        contact_email=args.contact_email,
        contact_phone=args.contact_phone,
        site_url=args.site_url,
        notice_url=args.notice_url,
        registry_path=args.registry,
        channels_path=args.channels,
        env_path=args.env_file,
    )
    if not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if args.apply:
        registry_path = Path(str(args.registry)).resolve()
        channels_path = Path(str(args.channels)).resolve()
        registry_path.write_text(json.dumps(result["prospective_registry"], ensure_ascii=False, indent=2), encoding="utf-8")
        channels_path.write_text(json.dumps(result["prospective_channels"], ensure_ascii=False, indent=2), encoding="utf-8")

    output = dict(result)
    output.pop("prospective_registry", None)
    output.pop("prospective_channels", None)
    output["applied"] = bool(args.apply)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
