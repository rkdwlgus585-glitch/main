import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate_live_release_ready import build_readiness


def _registry_payload() -> dict:
    return {
        "default_tenant_id": "seoul_main",
        "plan_feature_defaults": {"standard": ["estimate", "permit_precheck", "usage"]},
        "tenants": [
            {
                "tenant_id": "seoul_main",
                "display_name": "SeoulMNA",
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
            }
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
                "channel_hosts": ["seoulmna.kr"],
                "engine_origin": "https://calc.seoulmna.co.kr",
                "embed_base_url": "https://calc.seoulmna.co.kr/widgets",
                "default_tenant_id": "seoul_main",
                "exposed_systems": ["yangdo", "permit"],
                "branding": {
                    "brand_name": "서울건설정보",
                    "brand_label": "서울건설정보 · SEOUL CONSTRUCTION INFO",
                    "site_url": "https://seoulmna.kr",
                    "notice_url": "https://seoulmna.kr/notice",
                    "contact_phone": "1668-3548",
                    "contact_email": "hello@seoulmna.kr",
                    "source_tag_prefix": "seoulmna_kr",
                },
            }
        ],
    }


class ValidateLiveReleaseReadyTests(unittest.TestCase):
    def _write_files(self, td: str) -> tuple[Path, Path, Path]:
        base = Path(td)
        registry_path = base / "tenant_registry.json"
        channels_path = base / "channel_profiles.json"
        env_path = base / ".env"
        registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        channels_path.write_text(json.dumps(_channels_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        env_path.write_text(
            "TENANT_API_KEY_SEOUL_MAIN=test_seoul_key_1234567890\nADMIN_ID=admin\nADMIN_PW=pw\n",
            encoding="utf-8",
        )
        return registry_path, channels_path, env_path

    @patch("scripts.validate_live_release_ready._find_chrome_exe", return_value="C:/Program Files/Google/Chrome/Application/chrome.exe")
    def test_ready_when_channel_tenant_and_env_are_valid(self, _chrome):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            result = build_readiness(
                channel_id="seoul_web",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result["has_admin_credentials"])
            self.assertEqual(result["channel_id"], "seoul_web")
            self.assertEqual(result["scoped_summary"]["warning_count"], 0)
            self.assertTrue(result["handoff"]["release_ready"])
            self.assertIn("release orchestration 진행 가능", result["handoff"]["next_actions"])

    @patch("scripts.validate_live_release_ready._find_chrome_exe", return_value="")
    def test_blocked_without_chrome(self, _chrome):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            result = build_readiness(
                channel_id="seoul_web",
                registry_path=str(registry_path),
                channels_path=str(channels_path),
                env_path=str(env_path),
            )
            self.assertFalse(result["ok"])
            self.assertIn("chrome_not_found", result["blocking_issues"])
            self.assertIn("Chrome 실행 파일 경로 확인 또는 설치", result["handoff"]["next_actions"])


if __name__ == "__main__":
    unittest.main()
