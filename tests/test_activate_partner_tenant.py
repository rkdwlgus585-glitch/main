import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import activate_partner_tenant


def _registry_payload() -> dict:
    return {
        "default_tenant_id": "partner_template_standard",
        "plan_feature_defaults": {
            "standard": ["estimate", "permit_precheck", "consult", "usage"],
        },
        "offering_templates": [
            {
                "offering_id": "permit_standard",
                "display_name": "Permit Standard",
                "plan": "standard",
                "allowed_systems": ["permit"],
                "allowed_features": ["permit_precheck", "usage"],
            }
        ],
        "tenants": [
            {
                "tenant_id": "partner_template_standard",
                "display_name": "Partner Template",
                "enabled": False,
                "plan": "standard",
                "hosts": ["partner-template.example.com"],
                "origins": ["https://partner-template.example.com"],
                "api_key_envs": ["TENANT_API_KEY_PARTNER_TEMPLATE_STANDARD"],
                "allowed_systems": ["yangdo", "permit"],
                "data_sources": [
                    {
                        "source_id": "partner_contract_source",
                        "source_name": "Partner Contract Source",
                        "access_mode": "partner_contract",
                        "status": "pending",
                        "allows_commercial_use": False,
                        "contains_personal_data": False,
                        "transforms": ["aggregation"],
                    }
                ],
            }
        ],
    }


def _channel_payload() -> dict:
    return {
        "default_channel_id": "partner_template",
        "channels": [
            {
                "channel_id": "partner_template",
                "display_name": "Partner Template Channel",
                "enabled": False,
                "channel_hosts": ["partner-template.example.com"],
                "engine_origin": "https://calc.example.com",
                "embed_base_url": "https://calc.example.com/widgets",
                "default_tenant_id": "partner_template_standard",
                "exposed_systems": ["yangdo", "permit"],
                "branding": {
                    "brand_name": "Partner Calculator",
                    "brand_label": "PARTNER CALCULATOR",
                    "site_url": "https://partner-template.example.com",
                    "notice_url": "https://partner-template.example.com/notice",
                    "contact_phone": "010-0000-0000",
                    "contact_email": "partner@example.com",
                },
            }
        ],
    }


class ActivatePartnerTenantTests(unittest.TestCase):
    def _write_files(self, td: str) -> tuple[Path, Path, Path]:
        registry_path = Path(td) / "tenant_registry.json"
        channels_path = Path(td) / "channel_profiles.json"
        env_path = Path(td) / ".env"
        registry_path.write_text(json.dumps(_registry_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        channels_path.write_text(json.dumps(_channel_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        env_path.write_text("", encoding="utf-8")
        return registry_path, channels_path, env_path

    def test_apply_uses_engine_origin_and_rolls_back_when_smoke_fails(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            argv = [
                "activate_partner_tenant.py",
                "--tenant-id",
                "partner_template_standard",
                "--registry",
                str(registry_path),
                "--channels",
                str(channels_path),
                "--env-file",
                str(env_path),
                "--proof-url",
                "https://partner.example.com/contract-proof",
                "--approve-source",
                "--api-key-value",
                "test_partner_key_1234567890",
                "--apply",
            ]
            stdout = io.StringIO()
            with patch("scripts.activate_partner_tenant.run_smoke", return_value={"ok": False, "results": []}) as smoke_mock:
                with patch("sys.argv", argv):
                    with patch("sys.stdout", stdout):
                        exit_code = activate_partner_tenant.main()

            self.assertEqual(exit_code, 3)
            smoke_mock.assert_called_once()
            self.assertEqual(smoke_mock.call_args.kwargs["base_url"], "https://calc.example.com")
            self.assertEqual(smoke_mock.call_args.kwargs["channel_id"], "partner_template")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            channels = json.loads(channels_path.read_text(encoding="utf-8"))
            self.assertFalse(registry["tenants"][0]["enabled"])
            self.assertFalse(channels["channels"][0]["enabled"])
            self.assertEqual(env_path.read_text(encoding="utf-8"), "")

    def test_apply_persists_when_smoke_passes(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            argv = [
                "activate_partner_tenant.py",
                "--tenant-id",
                "partner_template_standard",
                "--registry",
                str(registry_path),
                "--channels",
                str(channels_path),
                "--env-file",
                str(env_path),
                "--proof-url",
                "https://partner.example.com/contract-proof",
                "--approve-source",
                "--api-key-value",
                "test_partner_key_1234567890",
                "--apply",
            ]
            stdout = io.StringIO()
            with patch("scripts.activate_partner_tenant.run_smoke", return_value={"ok": True, "results": [{"kind": "health", "ok": True}]}) as smoke_mock:
                with patch("sys.argv", argv):
                    with patch("sys.stdout", stdout):
                        exit_code = activate_partner_tenant.main()

            self.assertEqual(exit_code, 0)
            smoke_mock.assert_called_once()
            self.assertEqual(smoke_mock.call_args.kwargs["base_url"], "https://calc.example.com")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            channels = json.loads(channels_path.read_text(encoding="utf-8"))
            env_text = env_path.read_text(encoding="utf-8")

            self.assertTrue(registry["tenants"][0]["enabled"])
            self.assertTrue(channels["channels"][0]["enabled"])
            self.assertIn("TENANT_API_KEY_PARTNER_TEMPLATE_STANDARD=test_partner_key_1234567890", env_text)

    def test_offering_template_aligns_tenant_channel_and_smoke_service(self):
        with tempfile.TemporaryDirectory() as td:
            registry_path, channels_path, env_path = self._write_files(td)
            argv = [
                "activate_partner_tenant.py",
                "--tenant-id",
                "partner_template_standard",
                "--registry",
                str(registry_path),
                "--channels",
                str(channels_path),
                "--env-file",
                str(env_path),
                "--offering-id",
                "permit_standard",
                "--proof-url",
                "https://partner.example.com/contract-proof",
                "--approve-source",
                "--api-key-value",
                "test_partner_key_1234567890",
                "--apply",
            ]
            stdout = io.StringIO()
            with patch("scripts.activate_partner_tenant.run_smoke", return_value={"ok": True, "results": [{"kind": "health", "ok": True}]}) as smoke_mock:
                with patch("sys.argv", argv):
                    with patch("sys.stdout", stdout):
                        exit_code = activate_partner_tenant.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(smoke_mock.call_args.kwargs["service"], "permit")

            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            channels = json.loads(channels_path.read_text(encoding="utf-8"))
            self.assertEqual(registry["tenants"][0]["allowed_systems"], ["permit"])
            self.assertEqual(registry["tenants"][0]["allowed_features"], ["permit_precheck", "usage"])
            self.assertEqual(channels["channels"][0]["exposed_systems"], ["permit"])


if __name__ == "__main__":
    unittest.main()
