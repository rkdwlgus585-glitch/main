from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urlparse


@dataclass(frozen=True)
class TenantProfile:
    tenant_id: str
    display_name: str
    hosts: tuple[str, ...]
    enabled: bool = True
    plan: str = "standard"
    allowed_features: frozenset[str] = frozenset()
    allowed_systems: frozenset[str] = frozenset()
    blocked_api_tokens: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TenantResolution:
    tenant: Optional[TenantProfile]
    matched_host: str = ""
    source: str = ""


class TenantGateway:
    def __init__(
        self,
        tenants: Iterable[TenantProfile],
        *,
        strict: bool = False,
        default_tenant_id: str = "",
    ) -> None:
        self.strict = bool(strict)
        self.default_tenant_id = str(default_tenant_id or "").strip().lower()
        self._tenants: Dict[str, TenantProfile] = {}
        self._by_host: Dict[str, TenantProfile] = {}
        for tenant in tenants:
            tid = str(tenant.tenant_id or "").strip().lower()
            if not tid:
                continue
            self._tenants[tid] = tenant
            for host in tenant.hosts:
                h = _normalize_host(host)
                if h:
                    self._by_host[h] = tenant

    @property
    def tenant_count(self) -> int:
        return len(self._tenants)

    def resolve(self, host: str = "", origin: str = "") -> TenantResolution:
        candidates: List[tuple[str, str]] = []
        h = _normalize_host(host)
        if h:
            candidates.append((h, "host"))
        oh = _host_from_origin(origin)
        if oh:
            candidates.append((oh, "origin"))

        for candidate, source in candidates:
            tenant = self._by_host.get(candidate)
            if tenant is not None:
                return TenantResolution(tenant=tenant, matched_host=candidate, source=source)

        if self.default_tenant_id:
            tenant = self._tenants.get(self.default_tenant_id)
            if tenant is not None:
                return TenantResolution(tenant=tenant, matched_host="", source="default")

        return TenantResolution(tenant=None, matched_host="", source="")

    def check_feature(self, resolution: TenantResolution, feature: str) -> bool:
        feature_key = str(feature or "").strip().lower()
        tenant = resolution.tenant
        if tenant is None:
            return not self.strict
        if not bool(tenant.enabled):
            return False
        allowed = set(tenant.allowed_features or set())
        if not allowed:
            return True
        return feature_key in allowed

    def check_system(self, resolution: TenantResolution, system: str) -> bool:
        system_key = str(system or "").strip().lower()
        tenant = resolution.tenant
        if tenant is None:
            return not self.strict
        if not bool(tenant.enabled):
            return False
        allowed = set(tenant.allowed_systems or set())
        if not allowed:
            return True
        return system_key in allowed

    def is_token_blocked(self, resolution: TenantResolution, token: str) -> bool:
        tenant = resolution.tenant
        if tenant is None:
            return False
        value = str(token or "").strip()
        if not value:
            return False
        return value in set(tenant.blocked_api_tokens or set())


def _normalize_host(raw: str) -> str:
    src = str(raw or "").strip().lower()
    if not src:
        return ""
    if "//" in src:
        parsed = urlparse(src)
        src = parsed.netloc.lower()
    if "@" in src:
        src = src.split("@", 1)[1]
    if ":" in src:
        src = src.split(":", 1)[0]
    return src.strip()


def _host_from_origin(origin: str) -> str:
    src = str(origin or "").strip()
    if not src:
        return ""
    try:
        parsed = urlparse(src)
        return _normalize_host(parsed.netloc)
    except (ValueError, AttributeError):
        return ""


def _to_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    src = str(value).strip().lower()
    if src in {"1", "true", "yes", "on", "y"}:
        return True
    if src in {"0", "false", "no", "off", "n"}:
        return False
    return default


def tenant_from_json_entry(
    entry: dict,
    plan_feature_defaults: Optional[Dict[str, Set[str]]] = None,
) -> Optional[TenantProfile]:
    if not isinstance(entry, dict):
        return None
    tenant_id = str(entry.get("tenant_id") or "").strip()
    if not tenant_id:
        return None
    display_name = str(entry.get("display_name") or tenant_id).strip() or tenant_id

    hosts_raw = entry.get("hosts") or []
    hosts: List[str] = []
    if isinstance(hosts_raw, list):
        for h in hosts_raw:
            nh = _normalize_host(str(h))
            if nh:
                hosts.append(nh)

    plan = str(entry.get("plan") or "standard").strip().lower() or "standard"
    enabled = _to_bool(entry.get("enabled"), True)

    features_raw = entry.get("allowed_features") or []
    features: Set[str] = set()
    if isinstance(features_raw, list):
        for f in features_raw:
            key = str(f or "").strip().lower()
            if key:
                features.add(key)

    if (not features) and isinstance(plan_feature_defaults, dict):
        defaults = plan_feature_defaults.get(plan) or set()
        features = set(defaults)

    systems_raw = entry.get("allowed_systems") or []
    systems: Set[str] = set()
    if isinstance(systems_raw, list):
        for value in systems_raw:
            key = str(value or "").strip().lower()
            if key:
                systems.add(key)
    if not systems:
        if any(feature.startswith("permit_precheck") for feature in features):
            systems.add("permit")
        if any(feature.startswith("estimate") for feature in features):
            systems.add("yangdo")

    blocked_raw = entry.get("blocked_api_tokens") or []
    blocked_tokens: Set[str] = set()
    if isinstance(blocked_raw, list):
        for item in blocked_raw:
            token = str(item or "").strip()
            if not token:
                continue
            if ":" in token:
                token = token.split(":", 1)[1].strip()
            if token:
                blocked_tokens.add(token)

    return TenantProfile(
        tenant_id=tenant_id,
        display_name=display_name,
        hosts=tuple(hosts),
        enabled=bool(enabled),
        plan=plan,
        allowed_features=frozenset(features),
        allowed_systems=frozenset(systems),
        blocked_api_tokens=frozenset(blocked_tokens),
    )


def load_tenant_gateway_from_file(path: str, *, strict: bool = False, default_tenant_id: str = "") -> TenantGateway:
    src = str(path or "").strip()
    if not src:
        return TenantGateway([], strict=strict, default_tenant_id=default_tenant_id)

    with open(src, "r", encoding="utf-8-sig") as fp:
        data = json.load(fp)

    tenants_raw = data.get("tenants") if isinstance(data, dict) else []
    plan_defaults_raw = data.get("plan_feature_defaults") if isinstance(data, dict) else {}

    plan_feature_defaults: Dict[str, Set[str]] = {}
    if isinstance(plan_defaults_raw, dict):
        for plan, raw_features in plan_defaults_raw.items():
            plan_key = str(plan or "").strip().lower()
            if not plan_key:
                continue
            fs: Set[str] = set()
            if isinstance(raw_features, list):
                for f in raw_features:
                    key = str(f or "").strip().lower()
                    if key:
                        fs.add(key)
            if fs:
                plan_feature_defaults[plan_key] = fs

    tenants: List[TenantProfile] = []
    if isinstance(tenants_raw, list):
        for raw in tenants_raw:
            profile = tenant_from_json_entry(raw, plan_feature_defaults=plan_feature_defaults)
            if profile is not None:
                tenants.append(profile)

    default_id = str(default_tenant_id or "").strip() or str(data.get("default_tenant_id") or "").strip()
    return TenantGateway(tenants, strict=strict, default_tenant_id=default_id)
