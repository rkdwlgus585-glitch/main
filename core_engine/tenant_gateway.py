from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from core_engine.host_utils import host_from_origin, normalize_host, to_bool

__all__ = [
    "TenantProfile",
    "TenantResolution",
    "TenantGateway",
    "tenant_from_json_entry",
    "load_tenant_gateway_from_file",
]


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
    tenant: TenantProfile | None
    matched_host: str = ""
    source: str = ""


class TenantGateway:
    """Route requests to tenant profiles by host or origin, enforcing feature/system ACLs."""

    def __init__(
        self,
        tenants: Iterable[TenantProfile],
        *,
        strict: bool = False,
        default_tenant_id: str = "",
    ) -> None:
        self.strict = bool(strict)
        self.default_tenant_id = str(default_tenant_id or "").strip().lower()
        self._tenants: dict[str, TenantProfile] = {}
        self._by_host: dict[str, TenantProfile] = {}
        for tenant in tenants:
            tid = str(tenant.tenant_id or "").strip().lower()
            if not tid:
                continue
            self._tenants[tid] = tenant
            for host in tenant.hosts:
                h = normalize_host(host)
                if h:
                    self._by_host[h] = tenant

    @property
    def tenant_count(self) -> int:
        return len(self._tenants)

    def resolve(self, host: str = "", origin: str = "") -> TenantResolution:
        """Resolve *host* or *origin* to a ``TenantResolution``."""
        candidates: list[tuple[str, str]] = []
        h = normalize_host(host)
        if h:
            candidates.append((h, "host"))
        oh = host_from_origin(origin)
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
        """Return True if *feature* is allowed for the resolved tenant."""
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
        """Return True if *system* is exposed for the resolved tenant."""
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
        """Return True if *token* appears in the tenant's blocked-token set."""
        tenant = resolution.tenant
        if tenant is None:
            return False
        value = str(token or "").strip()
        if not value:
            return False
        return value in set(tenant.blocked_api_tokens or set())



def tenant_from_json_entry(
    entry: dict[str, Any],
    plan_feature_defaults: dict[str, set[str]] | None = None,
) -> TenantProfile | None:
    """Parse a raw JSON dict into a ``TenantProfile``; return None on invalid input."""
    if not isinstance(entry, dict):
        return None
    tenant_id = str(entry.get("tenant_id") or "").strip()
    if not tenant_id:
        return None
    display_name = str(entry.get("display_name") or tenant_id).strip() or tenant_id

    hosts_raw = entry.get("hosts") or []
    hosts: list[str] = []
    if isinstance(hosts_raw, list):
        for h in hosts_raw:
            nh = normalize_host(str(h))
            if nh:
                hosts.append(nh)

    plan = str(entry.get("plan") or "standard").strip().lower() or "standard"
    enabled = to_bool(entry.get("enabled"), True)

    features_raw = entry.get("allowed_features") or []
    features: set[str] = set()
    if isinstance(features_raw, list):
        for f in features_raw:
            key = str(f or "").strip().lower()
            if key:
                features.add(key)

    if (not features) and isinstance(plan_feature_defaults, dict):
        defaults = plan_feature_defaults.get(plan) or set()
        features = set(defaults)

    systems_raw = entry.get("allowed_systems") or []
    systems: set[str] = set()
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
    blocked_tokens: set[str] = set()
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
    """Load a ``TenantGateway`` from a JSON tenant-profiles file."""
    src = str(path or "").strip()
    if not src:
        return TenantGateway([], strict=strict, default_tenant_id=default_tenant_id)

    with open(src, encoding="utf-8-sig") as fp:
        data = json.load(fp)

    tenants_raw = data.get("tenants") if isinstance(data, dict) else []
    plan_defaults_raw = data.get("plan_feature_defaults") if isinstance(data, dict) else {}

    plan_feature_defaults: dict[str, set[str]] = {}
    if isinstance(plan_defaults_raw, dict):
        for plan, raw_features in plan_defaults_raw.items():
            plan_key = str(plan or "").strip().lower()
            if not plan_key:
                continue
            fs: set[str] = set()
            if isinstance(raw_features, list):
                for f in raw_features:
                    key = str(f or "").strip().lower()
                    if key:
                        fs.add(key)
            if fs:
                plan_feature_defaults[plan_key] = fs

    tenants: list[TenantProfile] = []
    if isinstance(tenants_raw, list):
        for raw in tenants_raw:
            profile = tenant_from_json_entry(raw, plan_feature_defaults=plan_feature_defaults)
            if profile is not None:
                tenants.append(profile)

    file_default = str(data.get("default_tenant_id") or "").strip() if isinstance(data, dict) else ""
    default_id = str(default_tenant_id or "").strip() or file_default
    return TenantGateway(tenants, strict=strict, default_tenant_id=default_id)
