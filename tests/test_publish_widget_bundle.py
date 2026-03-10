import json
import tempfile
import unittest
from pathlib import Path

from scripts.publish_widget_bundle import build_widget_bundle


def _registry_payload() -> dict:
    return {
        "default_tenant_id": "seoul_main",
        "plan_feature_defaults": {
            "standard": ["estimate", "permit_precheck", "usage"],
        },
        "tenants": [
            {
                "tenant_id": "seoul_main",
                "display_name": "Seoul Main",
                "enabled": True,
                "plan": "standard",
                "hosts": ["seoulmna.kr"],
                "origins": ["https://seoulmna.kr"],
                "api_key_envs": ["TENANT_API_KEY_SEOUL_MAIN"],
                "allowed_systems": ["yangdo", "permit"],
                "data_sources": [
                    {
                        "source_id": "first_party",
                        "source_name": "First Party",
                        "access_mode": "first_party_internal",
                        "status": "approved",
                        "allows_commercial_use": True,
                        "contains_personal_data": False,
                        "transforms": ["aggregation"],
                    }
                ],
            },
            {
                "tenant_id": "partner_yangdo_standard",
                "display_name": "Partner Yangdo",
                "enabled": False,
                "plan": "standard",
                "hosts": ["partner-yangdo.example.com"],
                "origins": ["https://partner-yangdo.example.com"],
                "api_key_envs": ["TENANT_API_KEY_PARTNER_YANGDO_STANDARD"],
                "allowed_systems": ["yangdo"],
                "allowed_features": ["estimate", "usage"],
                "data_sources": [
                    {
                        "source_id": "partner_contract_source",
                        "source_name": "Partner Contract",
                        "access_mode": "partner_contract",
                        "status": "pending",
                        "allows_commercial_use": False,
                        "contains_personal_data": False,
                        "transforms": ["aggregation"],
                    }
                ],
            },
        ],
    }


def _channels_payload() -> dict:
    return {
        "default_channel_id": "seoul_web",
        "channels": [
            {
                "channel_id": "seoul_web",
                "display_name": "Seoul Web",
                "enabled": True,
                "channel_role": "platform_front",
                "channel_hosts": ["seoulmna.kr"],
                "engine_origin": "https://calc.seoulmna.co.kr",
                "embed_base_url": "https://calc.seoulmna.co.kr/widgets",
                "default_tenant_id": "seoul_main",
                "exposed_systems": ["yangdo", "permit"],
                "canonical_public_host": "seoulmna.kr",
                "public_host_policy": "kr_main_platform",
                "platform_front_host": "seoulmna.kr",
                "legacy_content_host": "seoulmna.co.kr",
                "branding": {
                    "brand_name": "서울건설정보",
                    "brand_label": "서울건설정보 · SEOUL CONSTRUCTION INFO",
                    "site_url": "https://seoulmna.kr",
                    "notice_url": "https://seoulmna.co.kr/notice",
                    "contact_phone": "1668-3548",
                    "contact_email": "hello@seoulmna.kr",
                    "source_tag_prefix": "seoulmna_test",
                },
            },
            {
                "channel_id": "partner_yangdo_template",
                "display_name": "Partner Yangdo",
                "enabled": False,
                "channel_hosts": ["partner-yangdo.example.com"],
                "engine_origin": "https://calc.seoulmna.co.kr",
                "embed_base_url": "https://calc.seoulmna.co.kr/widgets",
                "default_tenant_id": "partner_yangdo_standard",
                "exposed_systems": ["yangdo"],
                "branding": {
                    "brand_name": "Partner Yangdo",
                    "brand_label": "PARTNER YANGDO",
                    "site_url": "https://partner-yangdo.example.com",
                    "notice_url": "https://partner-yangdo.example.com/notice",
                    "contact_phone": "010-0000-0000",
                    "contact_email": "partner-yangdo@example.com",
                    "source_tag_prefix": "partner_yangdo_test",
                },
            },
        ],
    }


class PublishWidgetBundleTests(unittest.TestCase):
    def _write_files(self, td: str) -> tuple[Path, Path, Path, Path]:
        base = Path(td)
        registry_path = base / "tenant_registry.json"
        channels_path = base / "channel_profiles.json"
        env_path = base / ".env"
        out_dir = base / "bundle_out"
        registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        channels_path.write_text(json.dumps(_channels_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        env_path.write_text("TENANT_API_KEY_SEOUL_MAIN=test_seoul_key_1234567890\n", encoding="utf-8")
        return registry_path, channels_path, env_path, out_dir

    def test_publish_ready_channel_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path, out_dir = self._write_files(td)
            manifest = build_widget_bundle(
                channel_id="seoul_web",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
                output_dir=str(out_dir),
            )
            self.assertTrue(manifest["ok"])
            self.assertEqual(len(manifest["widgets"]), 2)
            self.assertEqual(manifest["host"], "seoulmna.kr")
            self.assertTrue(Path(manifest["manifest_path"]).exists())
            self.assertTrue(Path(manifest["widgets"][0]["iframe_path"]).exists())
            self.assertTrue(Path(manifest["widgets"][0]["launcher_path"]).exists())

    def test_publish_disabled_channel_requires_allow_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path, out_dir = self._write_files(td)
            manifest = build_widget_bundle(
                channel_id="partner_yangdo_template",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
                output_dir=str(out_dir),
            )
            self.assertFalse(manifest["ok"])
            self.assertIn("default_tenant_not_ready:partner_yangdo_standard", manifest["activation_blockers"])


if __name__ == "__main__":
    unittest.main()
