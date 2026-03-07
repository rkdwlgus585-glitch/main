import json
import tempfile
import unittest
from pathlib import Path

from core_engine.channel_profiles import (
    ChannelProfile,
    ChannelRouter,
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


if __name__ == "__main__":
    unittest.main()
