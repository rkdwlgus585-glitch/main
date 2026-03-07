from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict


DEFAULT_BRANDING: Dict[str, str] = {
    "brand_name": "\uc11c\uc6b8\uac74\uc124\uc815\ubcf4",
    "brand_label": "\uc11c\uc6b8\uac74\uc124\uc815\ubcf4 \u00b7 SEOUL CONSTRUCTION INFO",
    "site_url": "https://seoulmna.co.kr",
    "canonical_public_host": "seoulmna.co.kr",
    "public_host_policy": "co_kr_canonical",
    "notice_url": "https://seoulmna.co.kr/notice",
    "contact_phone": "1668-3548",
    "contact_email": "seoulmna@gmail.com",
    "openchat_url": "",
    "source_tag_prefix": "seoulmna_kr",
}


def _digits_only(text: Any) -> str:
    return "".join(ch for ch in str(text or "") if ch.isdigit())


def _slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"[^0-9a-z가-힣]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def _config_path(config_path: str = "") -> Path:
    src = str(config_path or "").strip()
    if not src:
        src = str(os.getenv("CHANNEL_PROFILES_CONFIG", "")).strip()
    if not src:
        src = "tenant_config/channel_profiles.json"
    path = Path(src)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _load_raw_channel_config(config_path: str = "") -> Dict[str, Any]:
    path = _config_path(config_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def resolve_channel_branding(
    *,
    channel_id: str = "",
    config_path: str = "",
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, str]:
    data = _load_raw_channel_config(config_path)
    desired_channel_id = str(channel_id or os.getenv("CHANNEL_ID", "")).strip().lower()
    default_channel_id = str((data.get("default_channel_id") if isinstance(data, dict) else "") or "").strip().lower()
    channels = data.get("channels") if isinstance(data, dict) else []

    selected: Dict[str, Any] = {}
    if isinstance(channels, list):
        for item in channels:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("channel_id") or "").strip().lower()
            if desired_channel_id and cid == desired_channel_id:
                selected = item
                break
            if (not desired_channel_id) and default_channel_id and cid == default_channel_id:
                selected = item
    if not selected and isinstance(channels, list) and channels:
        for item in channels:
            if isinstance(item, dict):
                selected = item
                break

    branding = dict(DEFAULT_BRANDING)
    profile_branding = selected.get("branding") if isinstance(selected, dict) else {}
    if isinstance(profile_branding, dict):
        for key, value in profile_branding.items():
            if value is None:
                continue
            branding[str(key)] = str(value)
    explicit_canonical_host = str(selected.get("canonical_public_host") or "").strip()
    if explicit_canonical_host:
        branding["canonical_public_host"] = explicit_canonical_host
    explicit_host_policy = str(selected.get("public_host_policy") or "").strip()
    if explicit_host_policy:
        branding["public_host_policy"] = explicit_host_policy

    hosts = selected.get("channel_hosts") if isinstance(selected, dict) else []
    if not str(branding.get("site_url") or "").strip():
        if isinstance(hosts, list) and hosts:
            branding["site_url"] = f"https://{str(hosts[0]).strip()}"
    if not str(branding.get("canonical_public_host") or "").strip():
        if isinstance(hosts, list) and hosts:
            branding["canonical_public_host"] = str(hosts[0]).strip()
    if not str(branding.get("notice_url") or "").strip():
        site_url = str(branding.get("site_url") or "").rstrip("/")
        branding["notice_url"] = f"{site_url}/notice" if site_url else ""
    if not str(branding.get("brand_name") or "").strip():
        fallback_name = str(selected.get("display_name") or selected.get("channel_id") or "").strip()
        branding["brand_name"] = fallback_name or DEFAULT_BRANDING["brand_name"]
    if not str(branding.get("brand_label") or "").strip():
        branding["brand_label"] = branding["brand_name"]
    if not str(branding.get("source_tag_prefix") or "").strip():
        branding["source_tag_prefix"] = _slugify(selected.get("channel_id") or branding.get("brand_name")) or "channel"

    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if value is None:
                continue
            text = str(value).strip()
            if text:
                branding[str(key)] = text

    contact_phone = str(branding.get("contact_phone") or "").strip()
    branding["contact_phone"] = contact_phone or DEFAULT_BRANDING["contact_phone"]
    branding["contact_phone_digits"] = _digits_only(branding["contact_phone"])
    branding["channel_id"] = str(selected.get("channel_id") or desired_channel_id or default_channel_id or "").strip()
    return {str(k): str(v) for k, v in branding.items()}
