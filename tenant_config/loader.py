from __future__ import annotations

import os
from pathlib import Path

from core_engine.channel_profiles import ChannelRouter, load_channel_router_from_file
from core_engine.tenant_gateway import TenantGateway, load_tenant_gateway_from_file


def load_gateway(*, strict: bool = False, default_tenant_id: str = "", config_path: str = "") -> TenantGateway:
    path = str(config_path or "").strip()
    if not path:
        path = str(os.getenv("TENANT_GATEWAY_CONFIG", "")).strip()
    if not path:
        path = "tenant_config/tenant_registry.json"
    abs_path = Path(path)
    if not abs_path.is_absolute():
        abs_path = Path.cwd() / abs_path
    if not abs_path.exists():
        return TenantGateway([], strict=strict, default_tenant_id=default_tenant_id)
    return load_tenant_gateway_from_file(str(abs_path), strict=strict, default_tenant_id=default_tenant_id)


def load_channel_router(
    *,
    strict: bool = False,
    default_channel_id: str = "",
    config_path: str = "",
) -> ChannelRouter:
    path = str(config_path or "").strip()
    if not path:
        path = str(os.getenv("CHANNEL_PROFILES_CONFIG", "")).strip()
    if not path:
        path = "tenant_config/channel_profiles.json"
    abs_path = Path(path)
    if not abs_path.is_absolute():
        abs_path = Path.cwd() / abs_path
    if not abs_path.exists():
        return ChannelRouter([], strict=strict, default_channel_id=default_channel_id)
    return load_channel_router_from_file(str(abs_path), strict=strict, default_channel_id=default_channel_id)
