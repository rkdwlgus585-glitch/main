import json
import tempfile
import unittest
from pathlib import Path

from scripts.scaffold_partner_offering import build_partner_scaffold


def _registry_payload() -> dict:
    return {
        "default_tenant_id": "seoul_main",
        "plan_feature_defaults": {
            "standard": ["estimate", "permit_precheck", "usage"],
        },
        "tenants": [
            {
                "tenant_id": "seoul_main",
                "display_name": "SeoulMNA",
                "enabled": True,
                "plan": "pro_internal",
                "hosts": ["seoulmna.kr"],
                "origins": ["https://seoulmna.kr"],
                "api_key_envs": ["YANGDO_BLACKBOX_API_KEY"],
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
            }
        ],
        "offering_templates": [
            {
                "offering_id": "permit_standard",
                "display_name": "Permit Standard",
                "plan": "standard",
                "allowed_systems": ["permit"],
                "allowed_features": ["permit_precheck", "usage"],
            }
        ],
    }


def _channels_payload() -> dict:
    return {
        "default_channel_id": "seoul_web",
        "channels": [
            {
                "channel_id": "seoul_web",
                "display_name": "SeoulMNA Web Channel",
                "enabled": True,
                "channel_hosts": ["seoulmna.kr"],
                "engine_origin": "https://calc.seoulmna.co.kr",
                "embed_base_url": "https://calc.seoulmna.co.kr/widgets",
                "branding": {
                    "brand_name": "서울건설정보",
                    "brand_label": "서울건설정보 · SEOUL CONSTRUCTION INFO",
                    "site_url": "https://seoulmna.kr",
                    "notice_url": "https://seoulmna.kr/notice",
                    "contact_phone": "1668-3548",
                    "contact_email": "hello@seoulmna.kr",
                    "source_tag_prefix": "seoulmna_kr",
                },
                "default_tenant_id": "seoul_main",
                "rollout_stage": "channel_only",
                "exposed_systems": ["yangdo", "permit"],
            }
        ],
    }


class ScaffoldPartnerOfferingTests(unittest.TestCase):
    def _write_files(self, td: str) -> tuple[Path, Path, Path]:
        base = Path(td)
        registry_path = base / "tenant_registry.json"
        channels_path = base / "channel_profiles.json"
        env_path = base / ".env"
        registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        channels_path.write_text(json.dumps(_channels_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        env_path.write_text("", encoding="utf-8")
        return registry_path, channels_path, env_path

    def test_scaffold_from_offering_derives_systems_and_features(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            result = build_partner_scaffold(
                offering_id="permit_standard",
                tenant_id="partner_permit_alpha",
                channel_id="partner_permit_alpha_channel",
                host="permit-alpha.example.com",
                brand_name="Permit Alpha",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["tenant"]["allowed_systems"], ["permit"])
            self.assertEqual(result["tenant"]["allowed_features"], ["permit_precheck", "usage"])
            self.assertEqual(result["channel"]["exposed_systems"], ["permit"])
            self.assertEqual(result["api_key_env"], "TENANT_API_KEY_PARTNER_PERMIT_ALPHA")
            self.assertIn("missing_source_proof_url_pending", result["activation_blockers"])
            self.assertIn("disabled_missing_api_key", result["activation_blockers"])

    def test_scaffold_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            result = build_partner_scaffold(
                offering_id="permit_standard",
                tenant_id="seoul_main",
                channel_id="partner_permit_alpha_channel",
                host="permit-alpha.example.com",
                brand_name="Permit Alpha",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "tenant_exists")


if __name__ == "__main__":
    unittest.main()
