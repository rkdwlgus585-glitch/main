import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_partner_input_snapshot import build_partner_input_snapshot, main


class GeneratePartnerInputSnapshotTests(unittest.TestCase):
    @patch("scripts.generate_partner_input_snapshot.build_resolution_report")
    def test_build_snapshot_derives_scenarios(self, mock_resolution):
        mock_resolution.return_value = {
            "summary": {"ok": True, "matches_preview_expected_remaining": True},
            "actual": {"remaining_required_inputs": []},
        }
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            registry = base / "tenant_registry.json"
            channels = base / "channel_profiles.json"
            env_file = base / ".env"
            registry.write_text(
                json.dumps(
                    {
                        "plan_feature_defaults": {
                            "standard": ["estimate", "permit_precheck", "consult", "usage"]
                        },
                        "tenants": [
                            {
                                "tenant_id": "partner_template_standard",
                                "display_name": "Partner Combo",
                                "plan": "standard",
                                "allowed_systems": ["yangdo", "permit"],
                                "api_key_envs": ["TENANT_API_KEY_PARTNER_TEMPLATE_STANDARD"],
                                "data_sources": [
                                    {
                                        "source_id": "partner_combo_source",
                                        "access_mode": "partner_contract",
                                        "status": "pending",
                                        "allows_commercial_use": False,
                                        "proof_url": "",
                                    }
                                ],
                            },
                            {
                                "tenant_id": "partner_permit_standard",
                                "display_name": "Partner Permit",
                                "plan": "standard",
                                "allowed_systems": ["permit"],
                                "allowed_features": ["permit_precheck", "usage"],
                                "api_key_envs": ["TENANT_API_KEY_PARTNER_PERMIT_STANDARD"],
                                "data_sources": [
                                    {
                                        "source_id": "partner_source",
                                        "access_mode": "partner_contract",
                                        "status": "approved",
                                        "allows_commercial_use": True,
                                        "proof_url": "https://example.com/proof",
                                    }
                                ],
                            },
                            {
                                "tenant_id": "partner_yangdo_standard",
                                "display_name": "Partner Yangdo",
                                "plan": "standard",
                                "allowed_systems": ["yangdo"],
                                "allowed_features": ["estimate", "consult", "usage"],
                                "api_key_envs": ["TENANT_API_KEY_PARTNER_YANGDO_STANDARD"],
                                "data_sources": [
                                    {
                                        "source_id": "partner_source_y",
                                        "access_mode": "partner_contract",
                                        "status": "pending",
                                        "allows_commercial_use": False,
                                        "proof_url": "",
                                    }
                                ],
                            },
                        ],
                        "offering_templates": [
                            {
                                "offering_id": "combo_standard",
                                "plan": "standard",
                                "allowed_systems": ["yangdo", "permit"],
                                "allowed_features": ["estimate", "permit_precheck", "consult", "usage"],
                            },
                            {
                                "offering_id": "permit_standard",
                                "plan": "standard",
                                "allowed_systems": ["permit"],
                                "allowed_features": ["permit_precheck", "usage"],
                            },
                            {
                                "offering_id": "yangdo_standard",
                                "plan": "standard",
                                "allowed_systems": ["yangdo"],
                                "allowed_features": ["estimate", "consult", "usage"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            channels.write_text(
                json.dumps(
                    {
                        "channels": [
                            {
                                "channel_id": "partner_template",
                                "default_tenant_id": "partner_template_standard",
                                "channel_hosts": ["partner-template.example.com"],
                                "branding": {"brand_name": "Partner Combo"},
                            },
                            {
                                "channel_id": "partner_permit_template",
                                "default_tenant_id": "partner_permit_standard",
                                "channel_hosts": ["partner-permit.example.com"],
                                "branding": {"brand_name": "Partner Permit"},
                            },
                            {
                                "channel_id": "partner_yangdo_template",
                                "default_tenant_id": "partner_yangdo_standard",
                                "channel_hosts": ["partner-yangdo.example.com"],
                                "branding": {"brand_name": "Partner Yangdo"},
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            env_file.write_text("TENANT_API_KEY_PARTNER_PERMIT_STANDARD=permit-secret-token-value\n", encoding="utf-8")

            payload = build_partner_input_snapshot(
                registry_path=registry,
                channels_path=channels,
                env_path=env_file,
                include_resolution=True,
            )

            self.assertEqual(payload["summary"]["partner_tenant_count"], 3)
            self.assertEqual(payload["summary"]["ready_tenant_count"], 1)
            self.assertEqual(payload["summary"]["scenario_counts"]["proof_key_and_approval"], 1)
            self.assertEqual(payload["summary"]["scenario_counts"]["baseline"], 2)
            combo_row = payload["partners"][0]
            self.assertEqual(combo_row["offering_id"], "combo_standard")
            self.assertEqual(combo_row["feature_source"], "plan_default")
            permit_row = payload["partners"][1]
            self.assertEqual(permit_row["offering_id"], "permit_standard")
            self.assertTrue(permit_row["proof_url_present"])
            self.assertTrue(permit_row["api_key_present"])
            self.assertTrue(permit_row["approval_present"])
            self.assertEqual(permit_row["current_scenario"], "proof_key_and_approval")
            yangdo_row = payload["partners"][2]
            self.assertEqual(yangdo_row["current_scenario"], "baseline")
            self.assertEqual(
                yangdo_row["missing_required_inputs"],
                ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
            )

    @patch("scripts.generate_partner_input_snapshot.build_partner_input_snapshot")
    def test_cli_writes_outputs(self, mock_build):
        mock_build.return_value = {
            "summary": {"partner_tenant_count": 1, "ready_tenant_count": 0, "scenario_counts": {"baseline": 1}, "include_resolution": True},
            "partners": [{"tenant_id": "partner_demo", "channel_id": "partner_demo", "current_scenario": "baseline", "missing_required_inputs": ["partner_proof_url"], "proof_url_present": False, "api_key_present": False, "approval_present": False}],
        }
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            json_path = base / "snapshot.json"
            md_path = base / "snapshot.md"
            argv = [
                "generate_partner_input_snapshot.py",
                "--json",
                str(json_path),
                "--md",
                str(md_path),
            ]
            with patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["partner_tenant_count"], 1)
            self.assertIn("Partner Input Snapshot", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
