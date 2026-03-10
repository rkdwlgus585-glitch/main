import json
import tempfile
import unittest
from pathlib import Path

from core_engine.channel_profiles import (
    ChannelProfile,
    ChannelResolution,
    ChannelRouter,
    channel_profile_from_json_entry,
    load_channel_router_from_file,
)


class ChannelProfilesTest(unittest.TestCase):
    def test_resolve_by_host_and_origin(self):
        router = ChannelRouter(
            [
                ChannelProfile(
                    channel_id="seoul_web",
                    display_name="Seoul",
                    channel_hosts=("seoulmna.kr", "www.seoulmna.kr"),
                    engine_origin="https://calc.seoulmna.co.kr",
                    embed_base_url="https://calc.seoulmna.co.kr/widgets",
                    channel_role="platform_front",
                    canonical_public_host="seoulmna.kr",
                    public_host_policy="kr_main_platform",
                    platform_front_host="seoulmna.kr",
                    legacy_content_host="seoulmna.co.kr",
                    internal_widget_channel_id="seoul_widget_internal",
                    default_tenant_id="seoul_main",
                    exposed_systems=frozenset({"yangdo", "permit"}),
                )
            ],
            strict=True,
        )
        by_host = router.resolve(host="www.seoulmna.kr:443", origin="")
        self.assertIsNotNone(by_host.profile)
        self.assertEqual(by_host.source, "host")

        by_origin = router.resolve(host="", origin="https://seoulmna.kr/path")
        self.assertIsNotNone(by_origin.profile)
        self.assertEqual(by_origin.source, "origin")

    def test_default_channel_fallback(self):
        router = ChannelRouter(
            [
                ChannelProfile(
                    channel_id="seoul_web",
                    display_name="Seoul",
                    channel_hosts=("seoulmna.kr",),
                    engine_origin="https://calc.seoulmna.co.kr",
                    embed_base_url="https://calc.seoulmna.co.kr/widgets",
                    channel_role="platform_front",
                    canonical_public_host="seoulmna.kr",
                    public_host_policy="kr_main_platform",
                    platform_front_host="seoulmna.kr",
                    legacy_content_host="seoulmna.co.kr",
                    internal_widget_channel_id="seoul_widget_internal",
                    default_tenant_id="seoul_main",
                    exposed_systems=frozenset({"yangdo"}),
                )
            ],
            strict=True,
            default_channel_id="seoul_web",
        )
        resolution = router.resolve(host="unknown.example.com", origin="")
        self.assertIsNotNone(resolution.profile)
        self.assertEqual(resolution.source, "default")

    def test_load_from_json_file(self):
        data = {
            "default_channel_id": "alpha",
            "channels": [
                {
                    "channel_id": "alpha",
                    "display_name": "Alpha",
                    "channel_hosts": ["alpha.example.com"],
                    "engine_origin": "https://calc.example.com",
                    "embed_base_url": "https://calc.example.com/widgets",
                    "canonical_public_host": "app.example.com",
                    "public_host_policy": "single_host",
                    "platform_front_host": "app.example.com",
                    "legacy_content_host": "legacy.example.com",
                    "default_tenant_id": "tenant_alpha",
                    "exposed_systems": ["permit"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "channel_profiles.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            router = load_channel_router_from_file(str(path), strict=True)
            resolution = router.resolve(host="alpha.example.com", origin="")
            self.assertIsNotNone(resolution.profile)
            self.assertEqual(resolution.profile.channel_id, "alpha")
            self.assertEqual(resolution.profile.canonical_public_host, "app.example.com")
            self.assertEqual(resolution.profile.public_host_policy, "single_host")
            self.assertEqual(resolution.profile.platform_front_host, "app.example.com")
            self.assertEqual(resolution.profile.legacy_content_host, "legacy.example.com")
            self.assertEqual(router.profile_count, 1)
            self.assertTrue(router.check_system(resolution, "permit"))
            self.assertFalse(router.check_system(resolution, "yangdo"))


# ── channel_profile_from_json_entry ─────────────────────────────────


class ChannelProfileFromJsonTest(unittest.TestCase):
    """Direct tests for the JSON→ChannelProfile parser."""

    def _minimal_entry(self, **overrides):
        base = {
            "channel_id": "test_ch",
            "engine_origin": "https://engine.example.com",
        }
        base.update(overrides)
        return base

    def test_minimal_entry(self):
        profile = channel_profile_from_json_entry(self._minimal_entry())
        self.assertIsNotNone(profile)
        self.assertEqual(profile.channel_id, "test_ch")
        self.assertEqual(profile.display_name, "test_ch")
        self.assertEqual(profile.engine_origin, "https://engine.example.com")
        self.assertEqual(profile.embed_base_url, "https://engine.example.com")
        self.assertEqual(profile.channel_hosts, ())
        self.assertEqual(profile.channel_role, "widget_consumer")
        self.assertEqual(profile.private_engine_visibility, "hidden_origin")
        self.assertEqual(profile.public_host_policy, "dual_host")
        self.assertEqual(profile.rollout_stage, "phased")
        self.assertTrue(profile.enabled)

    def test_non_dict_returns_none(self):
        self.assertIsNone(channel_profile_from_json_entry("not a dict"))
        self.assertIsNone(channel_profile_from_json_entry(42))
        self.assertIsNone(channel_profile_from_json_entry([]))

    def test_missing_channel_id_returns_none(self):
        self.assertIsNone(channel_profile_from_json_entry(
            {"engine_origin": "https://e.com"}
        ))

    def test_blank_channel_id_returns_none(self):
        self.assertIsNone(channel_profile_from_json_entry(
            {"channel_id": "  ", "engine_origin": "https://e.com"}
        ))

    def test_missing_engine_origin_returns_none(self):
        self.assertIsNone(channel_profile_from_json_entry(
            {"channel_id": "ch1"}
        ))

    def test_empty_engine_origin_returns_none(self):
        self.assertIsNone(channel_profile_from_json_entry(
            {"channel_id": "ch1", "engine_origin": ""}
        ))

    def test_display_name_fallback_to_channel_id(self):
        profile = channel_profile_from_json_entry(self._minimal_entry())
        self.assertEqual(profile.display_name, "test_ch")

    def test_display_name_explicit(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(display_name="Custom Name")
        )
        self.assertEqual(profile.display_name, "Custom Name")

    def test_hosts_normalized(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(channel_hosts=["Example.COM:443", "sub.example.com"])
        )
        self.assertIn("example.com", profile.channel_hosts)
        self.assertIn("sub.example.com", profile.channel_hosts)

    def test_hosts_non_list_ignored(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(channel_hosts="not_a_list")
        )
        self.assertEqual(profile.channel_hosts, ())

    def test_hosts_empty_strings_filtered(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(channel_hosts=["", "  ", "valid.com"])
        )
        self.assertEqual(len(profile.channel_hosts), 1)
        self.assertEqual(profile.channel_hosts[0], "valid.com")

    def test_exposed_systems_normalized(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(exposed_systems=["Yangdo", " PERMIT ", ""])
        )
        self.assertEqual(profile.exposed_systems, frozenset({"yangdo", "permit"}))

    def test_exposed_systems_non_list_empty(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(exposed_systems="not_a_list")
        )
        self.assertEqual(profile.exposed_systems, frozenset())

    def test_canonical_host_from_branding_site_url(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(branding={"site_url": "https://Brand.Example.COM/path"})
        )
        self.assertEqual(profile.canonical_public_host, "brand.example.com")

    def test_canonical_host_from_first_channel_host(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(channel_hosts=["first.example.com", "second.example.com"])
        )
        self.assertEqual(profile.canonical_public_host, "first.example.com")

    def test_enabled_false(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(enabled=False)
        )
        self.assertFalse(profile.enabled)

    def test_enabled_string_false(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(enabled="false")
        )
        self.assertFalse(profile.enabled)

    def test_engine_origin_trailing_slash_stripped(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(engine_origin="https://engine.example.com/")
        )
        self.assertEqual(profile.engine_origin, "https://engine.example.com")

    def test_embed_base_url_defaults_to_engine_origin(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(engine_origin="https://engine.example.com")
        )
        self.assertEqual(profile.embed_base_url, "https://engine.example.com")

    def test_embed_base_url_explicit(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(embed_base_url="https://cdn.example.com/widgets/")
        )
        self.assertEqual(profile.embed_base_url, "https://cdn.example.com/widgets")

    def test_branding_non_dict_ignored(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(branding="not_a_dict")
        )
        # Should not crash, canonical_public_host falls back correctly
        self.assertIsNotNone(profile)

    def test_default_tenant_id_normalized(self):
        profile = channel_profile_from_json_entry(
            self._minimal_entry(default_tenant_id=" Tenant_ABC ")
        )
        self.assertEqual(profile.default_tenant_id, "tenant_abc")


# ── ChannelRouter edge cases ───────────────────────────────────────


class ChannelRouterEdgeCaseTest(unittest.TestCase):
    """Edge cases for ChannelRouter resolve/check_system."""

    def test_empty_router_resolve_returns_none_profile(self):
        router = ChannelRouter([])
        resolution = router.resolve(host="any.com", origin="")
        self.assertIsNone(resolution.profile)
        self.assertEqual(resolution.source, "")

    def test_empty_router_profile_count_zero(self):
        router = ChannelRouter([])
        self.assertEqual(router.profile_count, 0)

    def test_empty_channel_id_profile_skipped(self):
        """Profiles with blank channel_id are silently dropped."""
        profile = ChannelProfile(
            channel_id="",
            display_name="Ghost",
            channel_hosts=("ghost.com",),
            engine_origin="https://ghost.com",
            embed_base_url="https://ghost.com",
        )
        router = ChannelRouter([profile])
        self.assertEqual(router.profile_count, 0)

    def test_check_system_none_profile_non_strict(self):
        """With strict=False, None profile allows any system."""
        router = ChannelRouter([], strict=False)
        resolution = ChannelResolution(profile=None)
        self.assertTrue(router.check_system(resolution, "yangdo"))

    def test_check_system_none_profile_strict(self):
        """With strict=True, None profile denies any system."""
        router = ChannelRouter([], strict=True)
        resolution = ChannelResolution(profile=None)
        self.assertFalse(router.check_system(resolution, "yangdo"))

    def test_check_system_disabled_profile(self):
        """Disabled profile blocks all systems."""
        profile = ChannelProfile(
            channel_id="disabled_ch",
            display_name="Disabled",
            channel_hosts=("disabled.com",),
            engine_origin="https://disabled.com",
            embed_base_url="https://disabled.com",
            exposed_systems=frozenset({"yangdo"}),
            enabled=False,
        )
        router = ChannelRouter([profile])
        resolution = router.resolve(host="disabled.com")
        self.assertFalse(router.check_system(resolution, "yangdo"))

    def test_check_system_empty_exposed_allows_all(self):
        """Empty exposed_systems means all systems are allowed."""
        profile = ChannelProfile(
            channel_id="open_ch",
            display_name="Open",
            channel_hosts=("open.com",),
            engine_origin="https://open.com",
            embed_base_url="https://open.com",
            exposed_systems=frozenset(),
        )
        router = ChannelRouter([profile])
        resolution = router.resolve(host="open.com")
        self.assertTrue(router.check_system(resolution, "yangdo"))
        self.assertTrue(router.check_system(resolution, "permit"))
        self.assertTrue(router.check_system(resolution, "anything"))

    def test_check_system_case_insensitive(self):
        """System name matching is case-insensitive."""
        profile = ChannelProfile(
            channel_id="cs_ch",
            display_name="CS",
            channel_hosts=("cs.com",),
            engine_origin="https://cs.com",
            embed_base_url="https://cs.com",
            exposed_systems=frozenset({"yangdo"}),
        )
        router = ChannelRouter([profile])
        resolution = router.resolve(host="cs.com")
        self.assertTrue(router.check_system(resolution, "YANGDO"))
        self.assertTrue(router.check_system(resolution, "Yangdo"))

    def test_resolve_host_preferred_over_origin(self):
        """When both host and origin match different profiles, host wins."""
        p1 = ChannelProfile(
            channel_id="host_ch",
            display_name="Host",
            channel_hosts=("host.com",),
            engine_origin="https://host.com",
            embed_base_url="https://host.com",
        )
        p2 = ChannelProfile(
            channel_id="origin_ch",
            display_name="Origin",
            channel_hosts=("origin.com",),
            engine_origin="https://origin.com",
            embed_base_url="https://origin.com",
        )
        router = ChannelRouter([p1, p2])
        resolution = router.resolve(host="host.com", origin="https://origin.com")
        self.assertEqual(resolution.profile.channel_id, "host_ch")
        self.assertEqual(resolution.source, "host")

    def test_resolve_no_match_no_default_returns_empty(self):
        """No match and no default → empty resolution."""
        profile = ChannelProfile(
            channel_id="only",
            display_name="Only",
            channel_hosts=("only.com",),
            engine_origin="https://only.com",
            embed_base_url="https://only.com",
        )
        router = ChannelRouter([profile])
        resolution = router.resolve(host="other.com")
        self.assertIsNone(resolution.profile)
        self.assertEqual(resolution.matched_host, "")
        self.assertEqual(resolution.source, "")

    def test_default_channel_id_case_insensitive(self):
        """default_channel_id is normalized to lowercase."""
        profile = ChannelProfile(
            channel_id="Seoul_Web",
            display_name="Seoul",
            channel_hosts=("seoulmna.kr",),
            engine_origin="https://engine.seoulmna.kr",
            embed_base_url="https://engine.seoulmna.kr",
        )
        router = ChannelRouter([profile], default_channel_id="SEOUL_WEB")
        resolution = router.resolve(host="unknown.com")
        self.assertIsNotNone(resolution.profile)
        self.assertEqual(resolution.source, "default")


# ── load_channel_router_from_file edge cases ───────────────────────


class LoadChannelRouterEdgeCaseTest(unittest.TestCase):
    def test_empty_path_returns_empty_router(self):
        router = load_channel_router_from_file("")
        self.assertEqual(router.profile_count, 0)

    def test_none_path_returns_empty_router(self):
        router = load_channel_router_from_file(None)
        self.assertEqual(router.profile_count, 0)

    def test_non_dict_json_returns_empty_router(self):
        """If the JSON root is a list, no channels extracted."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            router = load_channel_router_from_file(str(path))
            self.assertEqual(router.profile_count, 0)

    def test_missing_channels_key_returns_empty_router(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "no_channels.json"
            path.write_text(json.dumps({"other_key": "value"}), encoding="utf-8")
            router = load_channel_router_from_file(str(path))
            self.assertEqual(router.profile_count, 0)

    def test_default_channel_from_json(self):
        """default_channel_id can come from the JSON data."""
        data = {
            "default_channel_id": "beta",
            "channels": [
                {
                    "channel_id": "beta",
                    "engine_origin": "https://beta.example.com",
                    "channel_hosts": ["beta.example.com"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "with_default.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            router = load_channel_router_from_file(str(path))
            resolution = router.resolve(host="unknown.com")
            self.assertIsNotNone(resolution.profile)
            self.assertEqual(resolution.profile.channel_id, "beta")

    def test_invalid_channel_entries_skipped(self):
        """Invalid entries (missing engine_origin) are silently skipped."""
        data = {
            "channels": [
                {"channel_id": "bad_entry"},
                {
                    "channel_id": "good_entry",
                    "engine_origin": "https://good.example.com",
                    "channel_hosts": ["good.example.com"],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mixed.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            router = load_channel_router_from_file(str(path))
            self.assertEqual(router.profile_count, 1)

    def test_channels_non_list_returns_empty(self):
        """If channels is not a list, no profiles extracted."""
        data = {"channels": "not_a_list"}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad_channels.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            router = load_channel_router_from_file(str(path))
            self.assertEqual(router.profile_count, 0)

    def test_strict_mode_forwarded(self):
        """strict=True from args propagates to the router."""
        data = {
            "channels": [
                {
                    "channel_id": "strict_ch",
                    "engine_origin": "https://strict.example.com",
                    "channel_hosts": ["strict.example.com"],
                    "exposed_systems": ["permit"],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "strict.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            router = load_channel_router_from_file(str(path), strict=True)
            # Unmatched host with strict mode + no default → None profile
            resolution = router.resolve(host="other.com")
            self.assertIsNone(resolution.profile)
            # check_system on None profile with strict → False
            self.assertFalse(router.check_system(resolution, "permit"))


if __name__ == "__main__":
    unittest.main()
