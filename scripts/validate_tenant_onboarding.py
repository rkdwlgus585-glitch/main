#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security_http import parse_key_values


DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_CHANNELS = ROOT / "tenant_config" / "channel_profiles.json"
DEFAULT_REPORT = ROOT / "logs" / "tenant_onboarding_validation_latest.json"

HOST_RE = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+$", re.IGNORECASE)
TENANT_ID_RE = re.compile(r"^[a-z0-9_]{3,40}$")
SOURCE_ID_RE = re.compile(r"^[a-z0-9_:\-]{3,80}$")
ALLOWED_SYSTEMS: Set[str] = {"yangdo", "permit"}

ALLOWED_ACCESS_MODES: Set[str] = {
    "first_party_internal",
    "official_api",
    "public_open_data",
    "partner_contract",
    "manual_entry",
}
DISALLOWED_ACCESS_MODES: Set[str] = {
    "unauthorized_crawling",
    "credential_sharing",
    "source_disguise",
}
DISALLOWED_TRANSFORMS: Set[str] = {
    "source_disguise",
    "origin_masking",
    "fake_data_camouflage",
    "fabrication_masking",
}
ACTIVATION_BLOCKING_WARNING_CODES: Set[str] = {
    "missing_source_proof_url_pending",
    "disabled_missing_api_key",
}


@dataclass
class ValidationMessage:
    level: str
    code: str
    message: str
    tenant_id: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "tenant_id": self.tenant_id,
            "message": self.message,
        }


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8-sig")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("registry_must_be_json_object")
    return data


def _load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip().lstrip("\ufeff")] = v.strip().strip('"').strip("'")
    return out


def _normalize_host(raw: str) -> str:
    src = str(raw or "").strip().lower()
    if not src:
        return ""
    if "://" in src:
        src = urlparse(src).netloc.lower()
    if "@" in src:
        src = src.split("@", 1)[1]
    if ":" in src:
        src = src.split(":", 1)[0]
    return src.strip()


def _origin_host(origin: str) -> str:
    src = str(origin or "").strip()
    if not src:
        return ""
    parsed = urlparse(src)
    if parsed.scheme.lower() not in {"http", "https"}:
        return ""
    return _normalize_host(parsed.netloc)


def _truthy(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _is_valid_host(host: str) -> bool:
    if not host:
        return False
    return bool(HOST_RE.match(host))


def _is_https_url(raw: str) -> bool:
    src = str(raw or "").strip()
    if not src:
        return False
    try:
        parsed = urlparse(src)
    except Exception:
        return False
    return parsed.scheme.lower() == "https" and bool(_normalize_host(parsed.netloc))


def _build_result(
    registry: Dict[str, object],
    messages: List[ValidationMessage],
    tenant_rows: List[Dict[str, object]],
    channel_rows: List[Dict[str, object]] | None = None,
) -> Dict[str, object]:
    errors = [m.as_dict() for m in messages if m.level == "error"]
    warnings = [m.as_dict() for m in messages if m.level == "warning"]
    return {
        "generated_at": _now(),
        "ok": len(errors) == 0,
        "summary": {
            "tenant_count": len(tenant_rows),
            "channel_count": len(channel_rows or []),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "default_tenant_id": str(registry.get("default_tenant_id") or "").strip(),
        "tenants": tenant_rows,
        "channels": channel_rows or [],
        "errors": errors,
        "warnings": warnings,
    }


def _validate_channels(
    channel_registry: Dict[str, object],
    *,
    tenant_ids: Set[str],
    tenant_hosts_by_id: Dict[str, Set[str]],
    tenant_enabled_by_id: Dict[str, bool],
    tenant_systems_by_id: Dict[str, Set[str]],
    messages: List[ValidationMessage],
) -> List[Dict[str, object]]:
    channel_rows: List[Dict[str, object]] = []
    default_channel_id = str(channel_registry.get("default_channel_id") or "").strip().lower()
    channels_raw = channel_registry.get("channels")
    if not isinstance(channels_raw, list) or not channels_raw:
        messages.append(ValidationMessage("error", "missing_channels", "channel_profiles의 channels 배열이 비어 있습니다."))
        return channel_rows

    seen_channel_ids: Set[str] = set()
    seen_channel_hosts: Dict[str, str] = {}

    for raw in channels_raw:
        if not isinstance(raw, dict):
            messages.append(ValidationMessage("error", "channel_row_type", "channel 항목은 객체여야 합니다."))
            continue

        channel_id = str(raw.get("channel_id") or "").strip().lower()
        if not channel_id or not TENANT_ID_RE.match(channel_id):
            messages.append(ValidationMessage("error", "invalid_channel_id", f"유효하지 않은 channel_id: {channel_id or '(empty)'}"))
            continue
        if channel_id in seen_channel_ids:
            messages.append(ValidationMessage("error", "duplicate_channel_id", f"중복 channel_id: {channel_id}"))
            continue
        seen_channel_ids.add(channel_id)

        enabled = _truthy(raw.get("enabled"), True)
        rollout_stage = str(raw.get("rollout_stage") or "phased").strip().lower() or "phased"
        default_tenant_id = str(raw.get("default_tenant_id") or "").strip().lower()
        engine_origin = str(raw.get("engine_origin") or "").strip()
        embed_base_url = str(raw.get("embed_base_url") or "").strip()

        channel_hosts_raw = raw.get("channel_hosts") or []
        channel_hosts: List[str] = []
        if isinstance(channel_hosts_raw, list):
            for host in channel_hosts_raw:
                nh = _normalize_host(str(host))
                if nh:
                    channel_hosts.append(nh)

        if not channel_hosts:
            messages.append(ValidationMessage("error", "missing_channel_hosts", "channel_hosts가 비어 있습니다.", tenant_id=channel_id))
        for host in channel_hosts:
            if not _is_valid_host(host):
                messages.append(ValidationMessage("error", "invalid_channel_host", f"유효하지 않은 channel_host: {host}", tenant_id=channel_id))
            owner = seen_channel_hosts.get(host)
            if owner and owner != channel_id:
                messages.append(ValidationMessage("error", "duplicate_channel_host", f"channel host 중복: {host} (owner={owner})", tenant_id=channel_id))
            else:
                seen_channel_hosts[host] = channel_id

        exposed_systems_raw = raw.get("exposed_systems") or []
        exposed_systems: Set[str] = set()
        if isinstance(exposed_systems_raw, list):
            for item in exposed_systems_raw:
                key = str(item or "").strip().lower()
                if not key:
                    continue
                if key not in ALLOWED_SYSTEMS:
                    messages.append(ValidationMessage("error", "invalid_channel_system", f"허용되지 않은 channel exposed_system: {key}", tenant_id=channel_id))
                    continue
                exposed_systems.add(key)

        if not _is_https_url(engine_origin):
            messages.append(ValidationMessage("error", "invalid_engine_origin", f"engine_origin이 유효한 https URL이 아닙니다: {engine_origin or '(empty)'}", tenant_id=channel_id))
        if not _is_https_url(embed_base_url):
            messages.append(ValidationMessage("error", "invalid_embed_base_url", f"embed_base_url이 유효한 https URL이 아닙니다: {embed_base_url or '(empty)'}", tenant_id=channel_id))

        if default_tenant_id:
            if default_tenant_id not in tenant_ids:
                messages.append(ValidationMessage("error", "channel_default_tenant_missing", f"default_tenant_id 미존재: {default_tenant_id}", tenant_id=channel_id))
            else:
                tenant_hosts = tenant_hosts_by_id.get(default_tenant_id) or set()
                overlap = sorted(set(channel_hosts).intersection(tenant_hosts))
                if not overlap:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "channel_tenant_host_mismatch",
                            f"channel_hosts와 default tenant hosts가 겹치지 않습니다: tenant={default_tenant_id}",
                            tenant_id=channel_id,
                        )
                    )
                tenant_systems = set(tenant_systems_by_id.get(default_tenant_id) or set())
                if exposed_systems and tenant_systems and not exposed_systems.issubset(tenant_systems):
                    messages.append(
                        ValidationMessage(
                            "error",
                            "channel_tenant_system_mismatch",
                            f"channel exposed_systems가 default tenant allowed_systems와 불일치합니다: tenant={default_tenant_id}",
                            tenant_id=channel_id,
                        )
                    )
                tenant_enabled = bool(tenant_enabled_by_id.get(default_tenant_id, False))
                if enabled and not tenant_enabled:
                    level = "error" if rollout_stage in {"live", "public", "active"} else "warning"
                    messages.append(
                        ValidationMessage(
                            level,
                            "channel_enabled_but_tenant_disabled",
                            f"enabled channel의 default tenant가 비활성입니다: {default_tenant_id}",
                            tenant_id=channel_id,
                        )
                    )
        else:
            messages.append(ValidationMessage("warning", "missing_channel_default_tenant", "default_tenant_id가 비어 있습니다.", tenant_id=channel_id))

        branding = raw.get("branding") if isinstance(raw.get("branding"), dict) else {}
        brand_name = str(branding.get("brand_name") or "").strip()
        brand_label = str(branding.get("brand_label") or "").strip()
        site_url = str(branding.get("site_url") or "").strip()
        notice_url = str(branding.get("notice_url") or "").strip()
        contact_phone = str(branding.get("contact_phone") or "").strip()
        contact_email = str(branding.get("contact_email") or "").strip()

        if enabled and not brand_name:
            messages.append(ValidationMessage("warning", "missing_brand_name", "enabled channel의 brand_name이 비어 있습니다.", tenant_id=channel_id))
        if enabled and not brand_label:
            messages.append(ValidationMessage("warning", "missing_brand_label", "enabled channel의 brand_label이 비어 있습니다.", tenant_id=channel_id))
        if site_url and not _is_https_url(site_url):
            messages.append(ValidationMessage("error", "invalid_brand_site_url", f"site_url이 유효한 https URL이 아닙니다: {site_url}", tenant_id=channel_id))
        if notice_url and not _is_https_url(notice_url):
            messages.append(ValidationMessage("error", "invalid_brand_notice_url", f"notice_url이 유효한 https URL이 아닙니다: {notice_url}", tenant_id=channel_id))
        if enabled and not contact_phone:
            messages.append(ValidationMessage("warning", "missing_contact_phone", "enabled channel의 contact_phone이 비어 있습니다.", tenant_id=channel_id))
        if enabled and ("@" not in contact_email):
            messages.append(ValidationMessage("warning", "invalid_contact_email", "enabled channel의 contact_email 형식이 올바르지 않습니다.", tenant_id=channel_id))

        channel_rows.append(
            {
                "channel_id": channel_id,
                "enabled": bool(enabled),
                "rollout_stage": rollout_stage,
                "default_tenant_id": default_tenant_id,
                "channel_host_count": len(channel_hosts),
                "exposed_systems": sorted(exposed_systems),
                "branding_ready": bool(brand_name and brand_label and contact_phone and ("@" in contact_email)),
            }
        )

    if default_channel_id and default_channel_id not in seen_channel_ids:
        messages.append(ValidationMessage("error", "default_channel_missing", f"default_channel_id 미존재: {default_channel_id}"))

    return channel_rows


def validate_registry(
    registry: Dict[str, object],
    *,
    env_values: Dict[str, str],
    channel_registry: Dict[str, object] | None = None,
) -> Dict[str, object]:
    messages: List[ValidationMessage] = []

    plan_defaults_raw = registry.get("plan_feature_defaults")
    plan_defaults: Dict[str, Set[str]] = {}
    if isinstance(plan_defaults_raw, dict):
        for plan, features in plan_defaults_raw.items():
            plan_key = str(plan or "").strip().lower()
            if not plan_key:
                continue
            feature_set: Set[str] = set()
            if isinstance(features, list):
                for feature in features:
                    key = str(feature or "").strip().lower()
                    if key:
                        feature_set.add(key)
            if feature_set:
                plan_defaults[plan_key] = feature_set

    if not plan_defaults:
        messages.append(ValidationMessage("error", "missing_plan_defaults", "plan_feature_defaults가 비어 있습니다."))

    tenants_raw = registry.get("tenants")
    if not isinstance(tenants_raw, list) or not tenants_raw:
        messages.append(ValidationMessage("error", "missing_tenants", "tenants 배열이 비어 있습니다."))
        return _build_result(registry, messages, [])

    seen_tenant: Set[str] = set()
    seen_host: Dict[str, str] = {}
    tenant_hosts_by_id: Dict[str, Set[str]] = {}
    tenant_enabled_by_id: Dict[str, bool] = {}
    tenant_systems_by_id: Dict[str, Set[str]] = {}
    key_owner: Dict[str, str] = {}
    tenant_rows: List[Dict[str, object]] = []

    for raw in tenants_raw:
        if not isinstance(raw, dict):
            messages.append(ValidationMessage("error", "tenant_row_type", "tenant 항목은 객체여야 합니다."))
            continue

        tenant_id = str(raw.get("tenant_id") or "").strip().lower()
        display = str(raw.get("display_name") or tenant_id).strip() or tenant_id
        enabled = _truthy(raw.get("enabled"), True)
        plan = str(raw.get("plan") or "standard").strip().lower() or "standard"

        if not tenant_id or not TENANT_ID_RE.match(tenant_id):
            messages.append(ValidationMessage("error", "invalid_tenant_id", "tenant_id 형식이 올바르지 않습니다.", tenant_id=tenant_id))
            continue
        if tenant_id in seen_tenant:
            messages.append(ValidationMessage("error", "duplicate_tenant_id", f"중복 tenant_id: {tenant_id}", tenant_id=tenant_id))
            continue
        seen_tenant.add(tenant_id)

        if plan not in plan_defaults:
            messages.append(ValidationMessage("error", "unknown_plan", f"정의되지 않은 plan: {plan}", tenant_id=tenant_id))

        hosts_raw = raw.get("hosts") or []
        hosts: List[str] = []
        if isinstance(hosts_raw, list):
            for host in hosts_raw:
                nh = _normalize_host(str(host))
                if nh:
                    hosts.append(nh)

        if not hosts:
            messages.append(ValidationMessage("error", "missing_hosts", "hosts가 비어 있습니다.", tenant_id=tenant_id))
        tenant_hosts_by_id[tenant_id] = set(hosts)
        tenant_enabled_by_id[tenant_id] = bool(enabled)

        for host in hosts:
            if not _is_valid_host(host):
                messages.append(ValidationMessage("error", "invalid_host", f"유효하지 않은 host: {host}", tenant_id=tenant_id))
            owner = seen_host.get(host)
            if owner and owner != tenant_id:
                messages.append(ValidationMessage("error", "duplicate_host", f"host 중복: {host} (owner={owner})", tenant_id=tenant_id))
            else:
                seen_host[host] = tenant_id

        origins_raw = raw.get("origins") or []
        origins: List[str] = []
        if isinstance(origins_raw, list):
            for origin in origins_raw:
                o = str(origin or "").strip()
                if o:
                    origins.append(o)

        for origin in origins:
            host = _origin_host(origin)
            if not host:
                messages.append(ValidationMessage("error", "invalid_origin", f"유효하지 않은 origin: {origin}", tenant_id=tenant_id))
                continue
            if host not in hosts:
                messages.append(ValidationMessage("error", "origin_host_mismatch", f"origin host {host}가 hosts에 없습니다.", tenant_id=tenant_id))

        explicit_features_raw = raw.get("allowed_features") or []
        explicit_features: Set[str] = set()
        if isinstance(explicit_features_raw, list):
            for feature in explicit_features_raw:
                key = str(feature or "").strip().lower()
                if key:
                    explicit_features.add(key)

        effective_features = set(explicit_features)
        if not effective_features and plan in plan_defaults:
            effective_features = set(plan_defaults[plan])

        allowed_systems_raw = raw.get("allowed_systems") or []
        allowed_systems: Set[str] = set()
        if isinstance(allowed_systems_raw, list):
            for item in allowed_systems_raw:
                key = str(item or "").strip().lower()
                if not key:
                    continue
                if key not in ALLOWED_SYSTEMS:
                    messages.append(ValidationMessage("error", "invalid_tenant_system", f"허용되지 않은 allowed_system: {key}", tenant_id=tenant_id))
                    continue
                allowed_systems.add(key)
        if not allowed_systems:
            if any(feature.startswith("permit_precheck") for feature in effective_features):
                allowed_systems.add("permit")
            if any(feature.startswith("estimate") for feature in effective_features):
                allowed_systems.add("yangdo")
        tenant_systems_by_id[tenant_id] = set(allowed_systems)

        if not effective_features:
            messages.append(ValidationMessage("warning", "empty_features", "유효 기능셋이 비어 있습니다.", tenant_id=tenant_id))

        key_envs_raw = raw.get("api_key_envs") or []
        key_envs: List[str] = []
        if isinstance(key_envs_raw, list):
            for name in key_envs_raw:
                env_name = str(name or "").strip()
                if env_name:
                    key_envs.append(env_name)

        blocked_raw = raw.get("blocked_api_tokens") or []
        blocked_tokens: Set[str] = set()
        if isinstance(blocked_raw, list):
            for token in blocked_raw:
                value = str(token or "").strip()
                if not value:
                    continue
                if ":" in value:
                    value = value.split(":", 1)[1].strip()
                if value:
                    blocked_tokens.add(value)

        data_sources_raw = raw.get("data_sources") or []
        data_source_rows: List[Dict[str, object]] = []
        approved_data_source_count = 0
        if data_sources_raw and not isinstance(data_sources_raw, list):
            messages.append(
                ValidationMessage(
                    "error",
                    "invalid_data_sources_type",
                    "data_sources는 배열이어야 합니다.",
                    tenant_id=tenant_id,
                )
            )
            data_sources_raw = []

        seen_source_ids: Set[str] = set()
        if isinstance(data_sources_raw, list):
            for source_row in data_sources_raw:
                if not isinstance(source_row, dict):
                    messages.append(
                        ValidationMessage(
                            "error",
                            "invalid_data_source_row",
                            "data_sources 항목은 객체여야 합니다.",
                            tenant_id=tenant_id,
                        )
                    )
                    continue

                source_id = str(source_row.get("source_id") or "").strip().lower()
                source_name = str(source_row.get("source_name") or source_id).strip()
                access_mode = str(source_row.get("access_mode") or "").strip().lower()
                status = str(source_row.get("status") or "approved").strip().lower() or "approved"
                proof_url = str(source_row.get("proof_url") or "").strip()
                allows_commercial_use = _truthy(source_row.get("allows_commercial_use"), False)
                contains_personal_data = _truthy(source_row.get("contains_personal_data"), False)
                transforms_raw = source_row.get("transforms") or []
                transforms: Set[str] = set()
                if isinstance(transforms_raw, list):
                    for item in transforms_raw:
                        key = str(item or "").strip().lower()
                        if key:
                            transforms.add(key)

                if not source_id or not SOURCE_ID_RE.match(source_id):
                    messages.append(
                        ValidationMessage(
                            "error",
                            "invalid_source_id",
                            f"유효하지 않은 source_id: {source_id or '(empty)'}",
                            tenant_id=tenant_id,
                        )
                    )
                elif source_id in seen_source_ids:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "duplicate_source_id",
                            f"중복 source_id: {source_id}",
                            tenant_id=tenant_id,
                        )
                    )
                else:
                    seen_source_ids.add(source_id)

                if not source_name:
                    messages.append(
                        ValidationMessage(
                            "warning",
                            "missing_source_name",
                            "source_name이 비어 있습니다.",
                            tenant_id=tenant_id,
                        )
                    )

                if access_mode in DISALLOWED_ACCESS_MODES:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "disallowed_access_mode",
                            f"금지된 access_mode 사용: {access_mode}",
                            tenant_id=tenant_id,
                        )
                    )
                elif access_mode not in ALLOWED_ACCESS_MODES:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "unknown_access_mode",
                            f"허용 목록에 없는 access_mode: {access_mode or '(empty)'}",
                            tenant_id=tenant_id,
                        )
                    )

                if access_mode in {"official_api", "partner_contract"} and not proof_url:
                    if enabled and status == "approved":
                        messages.append(
                            ValidationMessage(
                                "error",
                                "missing_source_proof_url",
                                f"{access_mode} source에는 proof_url이 필요합니다.",
                                tenant_id=tenant_id,
                            )
                        )
                    else:
                        messages.append(
                            ValidationMessage(
                                "warning",
                                "missing_source_proof_url_pending",
                                f"{access_mode} source proof_url 미입력(비활성/준비 단계 허용).",
                                tenant_id=tenant_id,
                            )
                        )

                disallowed_transforms = sorted(DISALLOWED_TRANSFORMS.intersection(transforms))
                if disallowed_transforms:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "disallowed_transform",
                            f"금지된 transform 포함: {', '.join(disallowed_transforms)}",
                            tenant_id=tenant_id,
                        )
                    )

                if contains_personal_data and "pseudonymization" not in transforms:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "missing_pseudonymization",
                            "개인정보 포함 source는 pseudonymization transform이 필요합니다.",
                            tenant_id=tenant_id,
                        )
                    )

                if enabled and status != "approved":
                    messages.append(
                        ValidationMessage(
                            "error",
                            "non_approved_source_in_enabled_tenant",
                            f"enabled tenant에는 status=approved source만 허용됩니다: {source_id or '(empty)'}",
                            tenant_id=tenant_id,
                        )
                    )

                if enabled and not allows_commercial_use:
                    messages.append(
                        ValidationMessage(
                            "error",
                            "commercial_use_not_allowed",
                            f"enabled tenant source는 상업적 이용 허용이 필요합니다: {source_id or '(empty)'}",
                            tenant_id=tenant_id,
                        )
                    )

                if status == "approved":
                    approved_data_source_count += 1

                data_source_rows.append(
                    {
                        "source_id": source_id,
                        "source_name": source_name,
                        "access_mode": access_mode,
                        "status": status,
                        "allows_commercial_use": bool(allows_commercial_use),
                        "contains_personal_data": bool(contains_personal_data),
                        "transform_count": len(transforms),
                    }
                )

        if enabled and not data_source_rows:
            messages.append(
                ValidationMessage(
                    "error",
                    "missing_data_sources",
                    "enabled tenant에는 data_sources가 최소 1개 필요합니다.",
                    tenant_id=tenant_id,
                )
            )
        if enabled and approved_data_source_count == 0:
            messages.append(
                ValidationMessage(
                    "error",
                    "missing_approved_data_source",
                    "enabled tenant에는 status=approved data_source가 필요합니다.",
                    tenant_id=tenant_id,
                )
            )

        if enabled and not key_envs:
            messages.append(ValidationMessage("error", "missing_api_key_envs", "enabled tenant에 api_key_envs가 없습니다.", tenant_id=tenant_id))

        token_count = 0
        for env_name in key_envs:
            raw_value = str(env_values.get(env_name, "") or "").strip()
            if not raw_value:
                if enabled:
                    messages.append(ValidationMessage("error", "missing_api_key_value", f"env 값 누락: {env_name}", tenant_id=tenant_id))
                else:
                    messages.append(ValidationMessage("warning", "disabled_missing_api_key", f"disabled tenant env 누락: {env_name}", tenant_id=tenant_id))
                continue
            tokens = parse_key_values(raw_value)
            if not tokens:
                messages.append(ValidationMessage("error", "invalid_api_key_value", f"파싱 가능한 API key가 없음: {env_name}", tenant_id=tenant_id))
                continue
            for token in tokens:
                token_count += 1
                if len(token) < 16:
                    messages.append(ValidationMessage("warning", "short_api_key", f"키 길이 권장 미달({len(token)}): {env_name}", tenant_id=tenant_id))
                owner = key_owner.get(token)
                if owner and owner != tenant_id:
                    messages.append(ValidationMessage("error", "reused_api_key", f"API key 재사용 감지: {env_name} (owner={owner})", tenant_id=tenant_id))
                else:
                    key_owner[token] = tenant_id

        if blocked_tokens:
            for token in blocked_tokens:
                if len(token) < 16:
                    messages.append(ValidationMessage("warning", "short_blocked_token", f"차단 토큰 길이 권장 미달({len(token)})", tenant_id=tenant_id))
                if token in key_owner:
                    messages.append(ValidationMessage("warning", "blocked_token_matches_active_key", "차단 토큰이 현재 활성 키와 동일합니다.", tenant_id=tenant_id))

        tenant_rows.append(
            {
                "tenant_id": tenant_id,
                "display_name": display,
                "enabled": bool(enabled),
                "plan": plan,
                "host_count": len(hosts),
                "origin_count": len(origins),
                "effective_features": sorted(effective_features),
                "allowed_systems": sorted(allowed_systems),
                "api_key_env_count": len(key_envs),
                "api_token_count": token_count,
                "blocked_token_count": len(blocked_tokens),
                "data_source_count": len(data_source_rows),
                "approved_data_source_count": int(approved_data_source_count),
            }
        )

    default_tenant_id = str(registry.get("default_tenant_id") or "").strip().lower()
    if default_tenant_id and default_tenant_id not in seen_tenant:
        messages.append(ValidationMessage("error", "default_tenant_missing", f"default_tenant_id 미존재: {default_tenant_id}"))

    channel_rows: List[Dict[str, object]] = []
    if isinstance(channel_registry, dict) and channel_registry:
        channel_rows = _validate_channels(
            channel_registry,
            tenant_ids=seen_tenant,
            tenant_hosts_by_id=tenant_hosts_by_id,
            tenant_enabled_by_id=tenant_enabled_by_id,
            tenant_systems_by_id=tenant_systems_by_id,
            messages=messages,
        )

    by_tenant_messages: Dict[str, List[ValidationMessage]] = {}
    for message in messages:
        key = str(message.tenant_id or "").strip().lower()
        if not key:
            continue
        by_tenant_messages.setdefault(key, []).append(message)

    tenant_ready: Dict[str, bool] = {}
    for row in tenant_rows:
        tenant_id = str(row.get("tenant_id") or "").strip().lower()
        blockers = []
        for message in by_tenant_messages.get(tenant_id, []):
            if message.level == "error" or message.code in ACTIVATION_BLOCKING_WARNING_CODES:
                blockers.append(message.code)
        row["activation_blockers"] = sorted(set(blockers))
        row["activation_ready"] = len(row["activation_blockers"]) == 0
        tenant_ready[tenant_id] = bool(row["activation_ready"])

    for row in channel_rows:
        channel_id = str(row.get("channel_id") or "").strip().lower()
        blockers = []
        for message in by_tenant_messages.get(channel_id, []):
            if message.level == "error" or message.code in ACTIVATION_BLOCKING_WARNING_CODES:
                blockers.append(message.code)
        default_tenant_id = str(row.get("default_tenant_id") or "").strip().lower()
        if default_tenant_id and not tenant_ready.get(default_tenant_id, False):
            blockers.append(f"default_tenant_not_ready:{default_tenant_id}")
        if not bool(row.get("branding_ready")):
            blockers.append("branding_not_ready")
        row["activation_blockers"] = sorted(set(blockers))
        row["activation_ready"] = len(row["activation_blockers"]) == 0

    return _build_result(registry, messages, tenant_rows, channel_rows)


def run_validation(registry_path: Path, env_path: Path, report_path: Path, strict: bool, channels_path: Path) -> int:
    if not registry_path.exists():
        raise FileNotFoundError(f"registry not found: {registry_path}")

    registry = _load_json(registry_path)
    channel_registry = _load_json(channels_path) if channels_path.exists() else {}
    env_file_values = _load_env_file(env_path)
    merged_env = dict(env_file_values)
    merged_env.update({k: v for k, v in os.environ.items() if isinstance(v, str)})

    report = validate_registry(registry, env_values=merged_env, channel_registry=channel_registry)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": report.get("ok"), "report": str(report_path), "summary": report.get("summary")}, ensure_ascii=False))

    if strict and not bool(report.get("ok")):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tenant onboarding registry/keys")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--strict", action="store_true", default=False)
    args = parser.parse_args()

    return run_validation(
        registry_path=Path(str(args.registry)).resolve(),
        channels_path=Path(str(args.channels)).resolve(),
        env_path=Path(str(args.env_file)).resolve(),
        report_path=Path(str(args.report)).resolve(),
        strict=bool(args.strict),
    )


if __name__ == "__main__":
    raise SystemExit(main())
