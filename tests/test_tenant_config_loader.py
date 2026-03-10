"""Tests for tenant_config.loader — config bootstrap with 3-tier path resolution."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core_engine.channel_profiles import ChannelRouter
from core_engine.tenant_gateway import TenantGateway
from tenant_config.loader import load_channel_router, load_gateway


# ── Helpers ───────────────────────────────────────────────────


def _tenant_found(resolution) -> bool:
    """True if resolution contains a resolved tenant (not None)."""
    return resolution is not None and getattr(resolution, "tenant", None) is not None


def _channel_found(resolution) -> bool:
    """True if resolution contains a resolved channel profile (not None)."""
    return resolution is not None and getattr(resolution, "profile", None) is not None


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture()
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove loader-related env vars before each test."""
    monkeypatch.delenv("TENANT_GATEWAY_CONFIG", raising=False)
    monkeypatch.delenv("CHANNEL_PROFILES_CONFIG", raising=False)


@pytest.fixture()
def tenant_json(tmp_path: Path) -> Path:
    """Write a minimal valid tenant_registry.json and return the path."""
    data = {
        "default_tenant_id": "test_main",
        "tenants": [
            {
                "tenant_id": "test_main",
                "display_name": "Test",
                "enabled": True,
                "plan": "standard",
                "hosts": ["test.example.com"],
                "origins": ["https://test.example.com"],
                "api_key_envs": [],
                "blocked_api_tokens": [],
                "data_sources": [],
                "allowed_systems": ["yangdo"],
            }
        ],
    }
    p = tmp_path / "tenant_registry.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture()
def channel_json(tmp_path: Path) -> Path:
    """Write a minimal valid channel_profiles.json and return the path."""
    data = {
        "default_channel_id": "test_web",
        "channels": [
            {
                "channel_id": "test_web",
                "display_name": "Test Channel",
                "enabled": True,
                "channel_role": "platform_front",
                "channel_hosts": ["test.example.com"],
                "engine_origin": "https://calc.test.example.com",
                "branding": {
                    "brand_name": "Test",
                    "brand_label": "TEST",
                    "site_url": "https://test.example.com",
                    "notice_url": "https://test.example.com",
                    "contact_phone": "000-0000",
                    "contact_email": "t@test.com",
                    "openchat_url": "",
                    "source_tag_prefix": "test",
                },
            }
        ],
    }
    p = tmp_path / "channel_profiles.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── load_gateway: explicit config_path ────────────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadGatewayExplicitPath:
    """config_path= argument takes top priority."""

    def test_loads_from_explicit_path(self, tenant_json: Path) -> None:
        gw = load_gateway(config_path=str(tenant_json))
        assert isinstance(gw, TenantGateway)
        r = gw.resolve("test_main")
        assert _tenant_found(r)
        assert r.tenant.tenant_id == "test_main"

    def test_explicit_path_overrides_env(
        self, tenant_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_GATEWAY_CONFIG", "/nonexistent/path.json")
        gw = load_gateway(config_path=str(tenant_json))
        assert _tenant_found(gw.resolve("test_main"))

    def test_strict_kwarg_forwarded(self, tenant_json: Path) -> None:
        gw = load_gateway(config_path=str(tenant_json), strict=True)
        assert isinstance(gw, TenantGateway)

    def test_default_tenant_id_kwarg_forwarded(self, tenant_json: Path) -> None:
        gw = load_gateway(config_path=str(tenant_json), default_tenant_id="custom")
        assert isinstance(gw, TenantGateway)


# ── load_gateway: env var fallback ─────────────────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadGatewayEnvVar:
    """TENANT_GATEWAY_CONFIG env var is second priority."""

    def test_loads_from_env_var(
        self, tenant_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_GATEWAY_CONFIG", str(tenant_json))
        gw = load_gateway()
        assert _tenant_found(gw.resolve("test_main"))

    def test_env_var_whitespace_trimmed(
        self, tenant_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_GATEWAY_CONFIG", f"  {tenant_json}  ")
        gw = load_gateway()
        assert _tenant_found(gw.resolve("test_main"))


# ── load_gateway: missing file fallback ────────────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadGatewayMissing:
    """When no config file exists, returns empty gateway."""

    def test_nonexistent_explicit_path(self) -> None:
        gw = load_gateway(config_path="/nonexistent/does_not_exist.json")
        assert isinstance(gw, TenantGateway)
        # Empty gateway → resolution has tenant=None
        assert not _tenant_found(gw.resolve("anything"))

    def test_nonexistent_env_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TENANT_GATEWAY_CONFIG", "/nonexistent.json")
        gw = load_gateway()
        assert isinstance(gw, TenantGateway)

    def test_empty_config_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string config_path falls through to env then default."""
        monkeypatch.setenv("TENANT_GATEWAY_CONFIG", "")
        gw = load_gateway(config_path="")
        assert isinstance(gw, TenantGateway)

    def test_whitespace_only_config_path(self) -> None:
        gw = load_gateway(config_path="   ")
        assert isinstance(gw, TenantGateway)


# ── load_gateway: relative path resolution ─────────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadGatewayRelativePath:
    """Relative paths are resolved from cwd."""

    def test_relative_path_resolved_from_cwd(
        self, tmp_path: Path, tenant_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        gw = load_gateway(config_path="tenant_registry.json")
        assert _tenant_found(gw.resolve("test_main"))

    def test_absolute_path_not_re_resolved(self, tenant_json: Path) -> None:
        gw = load_gateway(config_path=str(tenant_json))
        assert _tenant_found(gw.resolve("test_main"))


# ── load_channel_router: explicit config_path ──────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadChannelRouterExplicitPath:
    """config_path= argument takes top priority."""

    def test_loads_from_explicit_path(self, channel_json: Path) -> None:
        cr = load_channel_router(config_path=str(channel_json))
        assert isinstance(cr, ChannelRouter)
        r = cr.resolve("test_web")
        assert _channel_found(r)
        assert r.profile.channel_id == "test_web"

    def test_explicit_path_overrides_env(
        self, channel_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHANNEL_PROFILES_CONFIG", "/nonexistent/path.json")
        cr = load_channel_router(config_path=str(channel_json))
        assert _channel_found(cr.resolve("test_web"))

    def test_strict_kwarg_forwarded(self, channel_json: Path) -> None:
        cr = load_channel_router(config_path=str(channel_json), strict=True)
        assert isinstance(cr, ChannelRouter)

    def test_default_channel_id_kwarg_forwarded(self, channel_json: Path) -> None:
        cr = load_channel_router(
            config_path=str(channel_json), default_channel_id="custom"
        )
        assert isinstance(cr, ChannelRouter)


# ── load_channel_router: env var fallback ──────────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadChannelRouterEnvVar:
    """CHANNEL_PROFILES_CONFIG env var is second priority."""

    def test_loads_from_env_var(
        self, channel_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHANNEL_PROFILES_CONFIG", str(channel_json))
        cr = load_channel_router()
        assert _channel_found(cr.resolve("test_web"))

    def test_env_var_whitespace_trimmed(
        self, channel_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CHANNEL_PROFILES_CONFIG", f"  {channel_json}  ")
        cr = load_channel_router()
        assert _channel_found(cr.resolve("test_web"))


# ── load_channel_router: missing file fallback ─────────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadChannelRouterMissing:
    """When no config file exists, returns empty router."""

    def test_nonexistent_explicit_path(self) -> None:
        cr = load_channel_router(config_path="/nonexistent/does_not_exist.json")
        assert isinstance(cr, ChannelRouter)
        assert not _channel_found(cr.resolve("anything"))

    def test_nonexistent_env_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHANNEL_PROFILES_CONFIG", "/nonexistent.json")
        cr = load_channel_router()
        assert isinstance(cr, ChannelRouter)

    def test_empty_config_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHANNEL_PROFILES_CONFIG", "")
        cr = load_channel_router(config_path="")
        assert isinstance(cr, ChannelRouter)

    def test_whitespace_only_config_path(self) -> None:
        cr = load_channel_router(config_path="   ")
        assert isinstance(cr, ChannelRouter)


# ── load_channel_router: relative path resolution ──────────────


@pytest.mark.usefixtures("_clean_env")
class TestLoadChannelRouterRelativePath:
    """Relative paths are resolved from cwd."""

    def test_relative_path_resolved_from_cwd(
        self, tmp_path: Path, channel_json: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cr = load_channel_router(config_path="channel_profiles.json")
        assert _channel_found(cr.resolve("test_web"))


# ── Integration: real config files ─────────────────────────────


class TestIntegrationRealConfigs:
    """Load actual tenant_config/*.json files to verify end-to-end."""

    _config_dir = Path(__file__).resolve().parent.parent / "tenant_config"

    def test_real_tenant_registry(self) -> None:
        p = self._config_dir / "tenant_registry.json"
        if not p.exists():
            pytest.skip("tenant_registry.json not found")
        gw = load_gateway(config_path=str(p))
        r = gw.resolve("seoul_main")
        assert _tenant_found(r)
        assert r.tenant.tenant_id == "seoul_main"
        assert r.tenant.enabled is True

    def test_real_channel_profiles(self) -> None:
        p = self._config_dir / "channel_profiles.json"
        if not p.exists():
            pytest.skip("channel_profiles.json not found")
        cr = load_channel_router(config_path=str(p))
        r = cr.resolve("seoul_web")
        assert _channel_found(r)
        assert r.profile.channel_id == "seoul_web"
        assert r.profile.enabled is True

    def test_real_tenant_count(self) -> None:
        p = self._config_dir / "tenant_registry.json"
        if not p.exists():
            pytest.skip("tenant_registry.json not found")
        gw = load_gateway(config_path=str(p))
        for tid in ["seoul_main", "seoul_widget_unlimited", "partner_template_standard"]:
            assert _tenant_found(gw.resolve(tid)), f"Missing tenant: {tid}"

    def test_real_channel_count(self) -> None:
        p = self._config_dir / "channel_profiles.json"
        if not p.exists():
            pytest.skip("channel_profiles.json not found")
        cr = load_channel_router(config_path=str(p))
        for cid in ["seoul_web", "seoul_widget_internal", "partner_template"]:
            assert _channel_found(cr.resolve(cid)), f"Missing channel: {cid}"

    def test_seoul_main_has_both_systems(self) -> None:
        p = self._config_dir / "tenant_registry.json"
        if not p.exists():
            pytest.skip("tenant_registry.json not found")
        gw = load_gateway(config_path=str(p))
        r = gw.resolve("seoul_main")
        assert _tenant_found(r)
        raw = r.tenant._raw if hasattr(r.tenant, "_raw") else {}
        systems = raw.get("allowed_systems", [])
        if systems:
            assert "yangdo" in systems
            assert "permit" in systems
