from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class ChannelProfile:
    channel_id: str
    display_name: str
    channel_hosts: tuple[str, ...]
    engine_origin: str
    embed_base_url: str
    public_calculator_mount_base: str = ""
    private_engine_visibility: str = "hidden_origin"
    channel_role: str = "widget_consumer"
    canonical_public_host: str = ""
    public_host_policy: str = "dual_host"
    platform_front_host: str = ""
    legacy_content_host: str = ""
    internal_widget_channel_id: str = ""
    default_tenant_id: str = ""
    exposed_systems: frozenset[str] = frozenset()
    rollout_stage: str = "phased"
    enabled: bool = True


@dataclass(frozen=True)
class ChannelResolution:
    profile: Optional[ChannelProfile]
    matched_host: str = ""
    source: str = ""


class ChannelRouter:
    def __init__(
        self,
        profiles: Iterable[ChannelProfile],
        *,
        strict: bool = False,
        default_channel_id: str = "",
    ) -> None:
        self.strict = bool(strict)
        self.default_channel_id = str(default_channel_id or "").strip().lower()
        self._profiles: Dict[str, ChannelProfile] = {}
        self._by_host: Dict[str, ChannelProfile] = {}

        for profile in profiles:
            channel_id = str(profile.channel_id or "").strip().lower()
            if not channel_id:
                continue
            self._profiles[channel_id] = profile
            for host in profile.channel_hosts:
                norm = _normalize_host(host)
                if norm:
                    self._by_host[norm] = profile

    @property
    def profile_count(self) -> int:
        return len(self._profiles)

    def resolve(self, host: str = "", origin: str = "") -> ChannelResolution:
        candidates: List[tuple[str, str]] = []
        host_norm = _normalize_host(host)
        if host_norm:
            candidates.append((host_norm, "host"))
        origin_host = _host_from_origin(origin)
        if origin_host:
            candidates.append((origin_host, "origin"))

        for candidate, source in candidates:
            profile = self._by_host.get(candidate)
            if profile is not None:
                return ChannelResolution(profile=profile, matched_host=candidate, source=source)

        if self.default_channel_id:
            profile = self._profiles.get(self.default_channel_id)
            if profile is not None:
                return ChannelResolution(profile=profile, matched_host="", source="default")

        return ChannelResolution(profile=None, matched_host="", source="")

    def check_system(self, resolution: ChannelResolution, system: str) -> bool:
        profile = resolution.profile
        if profile is None:
            return not self.strict
        if not bool(profile.enabled):
            return False
        exposed = set(profile.exposed_systems or set())
        if not exposed:
            return True
        return str(system or "").strip().lower() in exposed


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


def _host_from_origin(origin: str) -> str:
    src = str(origin or "").strip()
    if not src:
        return ""
    try:
        parsed = urlparse(src)
    except (ValueError, AttributeError):
        return ""
    return _normalize_host(parsed.netloc)


def _to_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def channel_profile_from_json_entry(entry: dict) -> Optional[ChannelProfile]:
    if not isinstance(entry, dict):
        return None
    channel_id = str(entry.get("channel_id") or "").strip()
    if not channel_id:
        return None
    display_name = str(entry.get("display_name") or channel_id).strip() or channel_id
    engine_origin = str(entry.get("engine_origin") or "").strip().rstrip("/")
    embed_base_url = str(entry.get("embed_base_url") or engine_origin).strip().rstrip("/")
    if not engine_origin:
        return None
    public_calculator_mount_base = str(entry.get("public_calculator_mount_base") or "").strip().rstrip("/")
    hosts_raw = entry.get("channel_hosts") or []
    hosts: List[str] = []
    if isinstance(hosts_raw, list):
        for host in hosts_raw:
            norm = _normalize_host(str(host))
            if norm:
                hosts.append(norm)
    branding = entry.get("branding") if isinstance(entry.get("branding"), dict) else {}
    canonical_public_host = _normalize_host(str(entry.get("canonical_public_host") or ""))
    if not canonical_public_host:
        canonical_public_host = _normalize_host(str(branding.get("site_url") or ""))
    if not canonical_public_host and hosts:
        canonical_public_host = hosts[0]
    platform_front_host = _normalize_host(str(entry.get("platform_front_host") or ""))
    legacy_content_host = _normalize_host(str(entry.get("legacy_content_host") or ""))
    exposed_systems_raw = entry.get("exposed_systems") or []
    exposed_systems = set()
    if isinstance(exposed_systems_raw, list):
        for item in exposed_systems_raw:
            key = str(item or "").strip().lower()
            if key:
                exposed_systems.add(key)
    return ChannelProfile(
        channel_id=channel_id,
        display_name=display_name,
        channel_hosts=tuple(hosts),
        engine_origin=engine_origin,
        embed_base_url=embed_base_url,
        public_calculator_mount_base=public_calculator_mount_base,
        private_engine_visibility=str(entry.get("private_engine_visibility") or "hidden_origin").strip().lower() or "hidden_origin",
        channel_role=str(entry.get("channel_role") or "widget_consumer").strip().lower() or "widget_consumer",
        canonical_public_host=canonical_public_host,
        public_host_policy=str(entry.get("public_host_policy") or "dual_host").strip().lower() or "dual_host",
        platform_front_host=platform_front_host,
        legacy_content_host=legacy_content_host,
        internal_widget_channel_id=str(entry.get("internal_widget_channel_id") or "").strip().lower(),
        default_tenant_id=str(entry.get("default_tenant_id") or "").strip().lower(),
        exposed_systems=frozenset(exposed_systems),
        rollout_stage=str(entry.get("rollout_stage") or "phased").strip().lower() or "phased",
        enabled=_to_bool(entry.get("enabled"), True),
    )


def load_channel_router_from_file(
    path: str,
    *,
    strict: bool = False,
    default_channel_id: str = "",
) -> ChannelRouter:
    src = str(path or "").strip()
    if not src:
        return ChannelRouter([], strict=strict, default_channel_id=default_channel_id)

    with open(src, "r", encoding="utf-8-sig") as fp:
        data = json.load(fp)

    default_id = str(default_channel_id or "").strip().lower()
    profiles_raw = []
    if isinstance(data, dict):
        profiles_raw = data.get("channels") or []
        if not default_id:
            default_id = str(data.get("default_channel_id") or "").strip().lower()
    profiles: List[ChannelProfile] = []
    if isinstance(profiles_raw, list):
        for row in profiles_raw:
            profile = channel_profile_from_json_entry(row)
            if profile is None:
                continue
            profiles.append(profile)
    return ChannelRouter(profiles, strict=strict, default_channel_id=default_id)
