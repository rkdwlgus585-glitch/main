import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_widget_snippet import build_widget_payload
from scripts.plan_channel_embed import plan_embed


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
                "tenant_id": "yangdo_only",
                "display_name": "Yangdo Only",
                "enabled": True,
                "plan": "standard",
                "hosts": ["partner-yangdo.example.com"],
                "origins": ["https://partner-yangdo.example.com"],
                "allowed_systems": ["yangdo"],
                "allowed_features": ["estimate", "usage"],
                "data_sources": [
                    {
                        "source_id": "partner_contract",
                        "source_name": "Partner Contract",
                        "access_mode": "partner_contract",
                        "status": "approved",
                        "allows_commercial_use": True,
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
                "enabled": True,
                "channel_hosts": ["partner-yangdo.example.com"],
                "engine_origin": "https://calc.seoulmna.co.kr",
                "embed_base_url": "https://calc.seoulmna.co.kr/widgets",
                "default_tenant_id": "yangdo_only",
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


class GenerateWidgetSnippetTests(unittest.TestCase):
    def _write_files(self, td: str) -> tuple[Path, Path, Path]:
        registry_path = Path(td) / "tenant_registry.json"
        channels_path = Path(td) / "channel_profiles.json"
        env_path = Path(td) / ".env"
        registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        channels_path.write_text(json.dumps(_channels_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        env_path.write_text(
            "TENANT_API_KEY_SEOUL_MAIN=test_seoul_key_1234567890\n"
            "TENANT_API_KEY_YANGDO_ONLY=test_partner_key_1234567890\n",
            encoding="utf-8",
        )
        return registry_path, channels_path, env_path

    def test_plan_embed_returns_widget_url_for_ready_channel(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            out = plan_embed(
                host="seoulmna.kr",
                widget="yangdo",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertTrue(out["ok"])
            self.assertEqual(out["requested_system"], "yangdo")
            self.assertIn("/widgets/yangdo?tenant_id=seoul_main", out["widget_url"])

    def test_plan_embed_blocks_system_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            out = plan_embed(
                host="partner-yangdo.example.com",
                widget="permit",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertFalse(out["ok"])
            self.assertEqual(out["requested_system"], "permit")
            self.assertFalse(out["requested_system_allowed"])

    def test_build_widget_payload_launcher_uses_branding_and_widget_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            payload = build_widget_payload(
                channel_id="seoul_web",
                widget="permit",
                mode="launcher",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["brand_name"], "서울건설정보")
            self.assertIn("AI 인허가 사전검토", payload["snippet"])
            self.assertIn("사전검토 시작", payload["snippet"])
            self.assertIn("tenant_id=seoul_main", payload["snippet"])
            self.assertEqual(payload["plan"]["host"], "seoulmna.kr")

    def test_plan_embed_iframe_uses_hardened_sandbox(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            out = plan_embed(
                host="seoulmna.kr",
                widget="permit",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertIn('sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"', out["embed_snippet"])
            self.assertNotIn("allow-same-origin", out["embed_snippet"])


if __name__ == "__main__":
    unittest.main()
