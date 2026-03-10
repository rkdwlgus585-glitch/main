"""Tests for core_engine.channel_profiles.

Covers: ChannelProfile dataclass, ChannelRouter host resolution,
check_system permission, channel_profile_from_json_entry parsing,
load_channel_router_from_file, strict mode, default fallback.
"""

from __future__ import annotations

import json

import pytest

from core_engine.channel_profiles import (
    ChannelProfile,
    ChannelResolution,
    ChannelRouter,
    channel_profile_from_json_entry,
    load_channel_router_from_file,
)


# ── fixtures ─────────────────────────────────────────────────────

def _profile(
    channel_id: str = "ch1",
    display_name: str = "Test Channel",
    channel_hosts: tuple[str, ...] = ("example.com",),
    engine_origin: str = "https://engine.example.com",
    embed_base_url: str = "https://embed.example.com",
    exposed_systems: frozenset[str] = frozenset(),
    enabled: bool = True,
    **kwargs: object,
) -> ChannelProfile:
    return ChannelProfile(
        channel_id=channel_id,
        display_name=display_name,
        channel_hosts=channel_hosts,
        engine_origin=engine_origin,
        embed_base_url=embed_base_url,
        exposed_systems=exposed_systems,
        enabled=enabled,
        **kwargs,
    )


# ── ChannelProfile dataclass ────────────────────────────────────

class TestChannelProfile:

    def test_frozen_immutability(self) -> None:
        p = _profile()
        with pytest.raises(AttributeError):
            p.channel_id = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        p = _profile()
        assert p.private_engine_visibility == "hidden_origin"
        assert p.channel_role == "widget_consumer"
        assert p.rollout_stage == "phased"
        assert p.enabled is True
        assert p.exposed_systems == frozenset()


# ── ChannelResolution dataclass ─────────────────────────────────

class TestChannelResolution:

    def test_empty_resolution(self) -> None:
        r = ChannelResolution(profile=None)
        assert r.profile is None
        assert r.matched_host == ""
        assert r.source == ""

    def test_resolution_with_profile(self) -> None:
        p = _profile()
        r = ChannelResolution(profile=p, matched_host="example.com", source="host")
        assert r.profile is p
        assert r.matched_host == "example.com"
        assert r.source == "host"


# ── ChannelRouter init ──────────────────────────────────────────

class TestChannelRouterInit:

    def test_empty_profiles(self) -> None:
        router = ChannelRouter([])
        assert router.profile_count == 0

    def test_single_profile(self) -> None:
        router = ChannelRouter([_profile()])
        assert router.profile_count == 1

    def test_multiple_profiles(self) -> None:
        p1 = _profile(channel_id="ch1", channel_hosts=("a.com",))
        p2 = _profile(channel_id="ch2", channel_hosts=("b.com",))
        router = ChannelRouter([p1, p2])
        assert router.profile_count == 2

    def test_empty_channel_id_skipped(self) -> None:
        p = _profile(channel_id="")
        router = ChannelRouter([p])
        assert router.profile_count == 0

    def test_whitespace_channel_id_skipped(self) -> None:
        p = _profile(channel_id="   ")
        router = ChannelRouter([p])
        assert router.profile_count == 0

    def test_duplicate_channel_id_last_wins(self) -> None:
        p1 = _profile(channel_id="ch1", display_name="First")
        p2 = _profile(channel_id="ch1", display_name="Second")
        router = ChannelRouter([p1, p2])
        assert router.profile_count == 1
        r = router.resolve(host="example.com")
        assert r.profile is not None
        assert r.profile.display_name == "Second"


# ── ChannelRouter.resolve ───────────────────────────────────────

class TestResolveByHost:

    def test_resolve_exact_host(self) -> None:
        router = ChannelRouter([_profile(channel_hosts=("app.kr",))])
        r = router.resolve(host="app.kr")
        assert r.profile is not None
        assert r.source == "host"
        assert r.matched_host == "app.kr"

    def test_resolve_host_case_insensitive(self) -> None:
        router = ChannelRouter([_profile(channel_hosts=("APP.KR",))])
        r = router.resolve(host="app.kr")
        assert r.profile is not None

    def test_resolve_no_match_returns_none(self) -> None:
        router = ChannelRouter([_profile(channel_hosts=("app.kr",))])
        r = router.resolve(host="other.com")
        assert r.profile is None
        assert r.source == ""

    def test_resolve_by_origin(self) -> None:
        router = ChannelRouter([_profile(channel_hosts=("app.kr",))])
        r = router.resolve(origin="https://app.kr")
        assert r.profile is not None
        assert r.source == "origin"

    def test_resolve_host_takes_priority_over_origin(self) -> None:
        p1 = _profile(channel_id="ch1", channel_hosts=("host.kr",))
        p2 = _profile(channel_id="ch2", channel_hosts=("origin.kr",))
        router = ChannelRouter([p1, p2])
        r = router.resolve(host="host.kr", origin="https://origin.kr")
        assert r.profile is not None
        assert r.profile.channel_id == "ch1"
        assert r.source == "host"

    def test_resolve_empty_host_and_origin(self) -> None:
        router = ChannelRouter([_profile()])
        r = router.resolve(host="", origin="")
        assert r.profile is None


class TestResolveDefault:

    def test_default_fallback(self) -> None:
        router = ChannelRouter(
            [_profile(channel_id="fallback")],
            default_channel_id="fallback",
        )
        r = router.resolve(host="unknown.com")
        assert r.profile is not None
        assert r.profile.channel_id == "fallback"
        assert r.source == "default"

    def test_default_channel_id_case_insensitive(self) -> None:
        router = ChannelRouter(
            [_profile(channel_id="FallBack")],
            default_channel_id="  FALLBACK  ",
        )
        r = router.resolve(host="unknown.com")
        assert r.profile is not None
        assert r.source == "default"

    def test_default_not_found(self) -> None:
        router = ChannelRouter(
            [_profile(channel_id="ch1")],
            default_channel_id="nonexistent",
        )
        r = router.resolve(host="unknown.com")
        assert r.profile is None

    def test_no_default_no_match(self) -> None:
        router = ChannelRouter([_profile()])
        r = router.resolve(host="unknown.com")
        assert r.profile is None


# ── ChannelRouter.check_system ──────────────────────────────────

class TestCheckSystem:

    def test_no_exposed_systems_allows_all(self) -> None:
        p = _profile(exposed_systems=frozenset())
        router = ChannelRouter([p])
        r = router.resolve(host="example.com")
        assert router.check_system(r, "yangdo") is True
        assert router.check_system(r, "permit") is True

    def test_exposed_systems_restricts(self) -> None:
        p = _profile(exposed_systems=frozenset({"yangdo"}))
        router = ChannelRouter([p])
        r = router.resolve(host="example.com")
        assert router.check_system(r, "yangdo") is True
        assert router.check_system(r, "permit") is False

    def test_system_check_case_insensitive(self) -> None:
        p = _profile(exposed_systems=frozenset({"yangdo"}))
        router = ChannelRouter([p])
        r = router.resolve(host="example.com")
        assert router.check_system(r, "YANGDO") is True

    def test_disabled_profile_denies(self) -> None:
        p = _profile(enabled=False)
        router = ChannelRouter([p])
        r = router.resolve(host="example.com")
        assert router.check_system(r, "yangdo") is False

    def test_none_profile_nonstrict_allows(self) -> None:
        router = ChannelRouter([], strict=False)
        r = ChannelResolution(profile=None)
        assert router.check_system(r, "yangdo") is True

    def test_none_profile_strict_denies(self) -> None:
        router = ChannelRouter([], strict=True)
        r = ChannelResolution(profile=None)
        assert router.check_system(r, "yangdo") is False

    def test_empty_system_string(self) -> None:
        p = _profile(exposed_systems=frozenset({"yangdo"}))
        router = ChannelRouter([p])
        r = router.resolve(host="example.com")
        assert router.check_system(r, "") is False

    def test_none_system(self) -> None:
        p = _profile(exposed_systems=frozenset({"yangdo"}))
        router = ChannelRouter([p])
        r = router.resolve(host="example.com")
        assert router.check_system(r, None) is False  # type: ignore[arg-type]


# ── channel_profile_from_json_entry ─────────────────────────────

class TestFromJsonEntry:

    def test_valid_entry(self) -> None:
        entry = {
            "channel_id": "seoulmna",
            "display_name": "서울MNA",
            "engine_origin": "https://engine.seoulmna.kr",
            "channel_hosts": ["seoulmna.kr", "www.seoulmna.kr"],
            "exposed_systems": ["yangdo", "permit"],
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.channel_id == "seoulmna"
        assert p.display_name == "서울MNA"
        assert len(p.channel_hosts) == 2
        assert p.exposed_systems == frozenset({"yangdo", "permit"})

    def test_missing_channel_id(self) -> None:
        assert channel_profile_from_json_entry({"engine_origin": "https://x.com"}) is None

    def test_empty_channel_id(self) -> None:
        assert channel_profile_from_json_entry({"channel_id": "", "engine_origin": "https://x.com"}) is None

    def test_missing_engine_origin(self) -> None:
        assert channel_profile_from_json_entry({"channel_id": "test"}) is None

    def test_non_dict_returns_none(self) -> None:
        assert channel_profile_from_json_entry("not a dict") is None  # type: ignore[arg-type]
        assert channel_profile_from_json_entry(None) is None  # type: ignore[arg-type]
        assert channel_profile_from_json_entry(42) is None  # type: ignore[arg-type]

    def test_defaults_applied(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.private_engine_visibility == "hidden_origin"
        assert p.channel_role == "widget_consumer"
        assert p.rollout_stage == "phased"
        assert p.enabled is True

    def test_canonical_host_from_branding(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
            "branding": {"site_url": "https://www.test.com"},
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.canonical_public_host == "www.test.com"

    def test_canonical_host_falls_to_first_host(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
            "channel_hosts": ["first.com", "second.com"],
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.canonical_public_host == "first.com"

    def test_embed_base_url_defaults_to_engine_origin(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.embed_base_url == "https://engine.test.com"

    def test_exposed_systems_empty_list(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
            "exposed_systems": [],
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.exposed_systems == frozenset()

    def test_exposed_systems_with_empty_strings(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
            "exposed_systems": ["yangdo", "", "  ", None],
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.exposed_systems == frozenset({"yangdo"})

    def test_enabled_false(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
            "enabled": False,
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.enabled is False

    def test_hosts_non_list_ignored(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com",
            "channel_hosts": "not-a-list",
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert p.channel_hosts == ()

    def test_trailing_slash_stripped(self) -> None:
        entry = {
            "channel_id": "test",
            "engine_origin": "https://engine.test.com/",
            "embed_base_url": "https://embed.test.com/",
        }
        p = channel_profile_from_json_entry(entry)
        assert p is not None
        assert not p.engine_origin.endswith("/")
        assert not p.embed_base_url.endswith("/")


# ── load_channel_router_from_file ───────────────────────────────

class TestLoadFromFile:

    def test_load_valid_file(self, tmp_path) -> None:
        data = {
            "default_channel_id": "ch1",
            "channels": [
                {
                    "channel_id": "ch1",
                    "display_name": "Channel One",
                    "engine_origin": "https://engine.ch1.com",
                    "channel_hosts": ["ch1.com"],
                },
            ],
        }
        file_path = tmp_path / "channels.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")
        router = load_channel_router_from_file(str(file_path))
        assert router.profile_count == 1
        assert router.default_channel_id == "ch1"

    def test_load_empty_path(self) -> None:
        router = load_channel_router_from_file("")
        assert router.profile_count == 0

    def test_load_none_path(self) -> None:
        router = load_channel_router_from_file(None)  # type: ignore[arg-type]
        assert router.profile_count == 0

    def test_load_override_default_channel(self, tmp_path) -> None:
        data = {
            "default_channel_id": "file_default",
            "channels": [
                {"channel_id": "override", "engine_origin": "https://engine.com"},
                {"channel_id": "file_default", "engine_origin": "https://engine2.com"},
            ],
        }
        file_path = tmp_path / "channels.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")
        router = load_channel_router_from_file(str(file_path), default_channel_id="override")
        assert router.default_channel_id == "override"

    def test_load_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_channel_router_from_file("/nonexistent/path.json")

    def test_load_invalid_json(self, tmp_path) -> None:
        file_path = tmp_path / "bad.json"
        file_path.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_channel_router_from_file(str(file_path))

    def test_load_non_dict_json(self, tmp_path) -> None:
        file_path = tmp_path / "list.json"
        file_path.write_text("[1, 2, 3]", encoding="utf-8")
        router = load_channel_router_from_file(str(file_path))
        assert router.profile_count == 0

    def test_load_strict_mode(self, tmp_path) -> None:
        data = {"channels": [{"channel_id": "ch1", "engine_origin": "https://x.com"}]}
        file_path = tmp_path / "channels.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")
        router = load_channel_router_from_file(str(file_path), strict=True)
        assert router.strict is True

    def test_load_channels_missing_key(self, tmp_path) -> None:
        file_path = tmp_path / "empty.json"
        file_path.write_text(json.dumps({}), encoding="utf-8")
        router = load_channel_router_from_file(str(file_path))
        assert router.profile_count == 0

    def test_load_with_invalid_entries_skipped(self, tmp_path) -> None:
        data = {
            "channels": [
                {"channel_id": "valid", "engine_origin": "https://engine.com"},
                {"channel_id": "", "engine_origin": "https://skip.com"},
                "not-a-dict",
                None,
            ],
        }
        file_path = tmp_path / "mixed.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")
        router = load_channel_router_from_file(str(file_path))
        assert router.profile_count == 1


# ── integration: multi-host routing ─────────────────────────────

class TestMultiHostRouting:

    def test_multi_host_profile(self) -> None:
        p = _profile(channel_hosts=("app.kr", "www.app.kr", "m.app.kr"))
        router = ChannelRouter([p])
        for host in ("app.kr", "www.app.kr", "m.app.kr"):
            r = router.resolve(host=host)
            assert r.profile is not None, f"Failed for host={host}"
            assert r.matched_host == host

    def test_two_channels_different_hosts(self) -> None:
        p1 = _profile(channel_id="seoulmna", channel_hosts=("seoulmna.kr",))
        p2 = _profile(channel_id="partner", channel_hosts=("partner.co.kr",))
        router = ChannelRouter([p1, p2])
        r1 = router.resolve(host="seoulmna.kr")
        r2 = router.resolve(host="partner.co.kr")
        assert r1.profile is not None and r1.profile.channel_id == "seoulmna"
        assert r2.profile is not None and r2.profile.channel_id == "partner"

    def test_system_gating_end_to_end(self) -> None:
        p = _profile(
            channel_id="limited",
            channel_hosts=("limited.co.kr",),
            exposed_systems=frozenset({"yangdo"}),
        )
        router = ChannelRouter([p], strict=True)
        r = router.resolve(host="limited.co.kr")
        assert router.check_system(r, "yangdo") is True
        assert router.check_system(r, "permit") is False
        # Unknown host in strict mode
        r_unknown = router.resolve(host="unknown.com")
        assert router.check_system(r_unknown, "yangdo") is False
