import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_partner_input_handoff_packet import build_partner_input_handoff_packet


class GeneratePartnerInputHandoffPacketTests(unittest.TestCase):
    def test_build_handoff_packet_aggregates_uniform_partner_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            registry = base / "registry.json"
            channels = base / "channels.json"
            snapshot = base / "snapshot.json"
            simulation = base / "simulation.json"

            registry.write_text(
                json.dumps(
                    {
                        "tenants": [
                            {
                                "tenant_id": "partner_yangdo_standard",
                                "display_name": "Partner Yangdo",
                                "api_key_envs": ["TENANT_API_KEY_PARTNER_YANGDO_STANDARD"],
                                "data_sources": [{"source_id": "yangdo_source"}],
                            },
                            {
                                "tenant_id": "partner_permit_standard",
                                "display_name": "Partner Permit",
                                "api_key_envs": ["TENANT_API_KEY_PARTNER_PERMIT_STANDARD"],
                                "data_sources": [{"source_id": "permit_source"}],
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            channels.write_text(
                json.dumps(
                    {
                        "channels": [
                            {"channel_id": "partner_yangdo_template", "branding": {"brand_name": "Yangdo"}, "default_tenant_id": "partner_yangdo_standard"},
                            {"channel_id": "partner_permit_template", "branding": {"brand_name": "Permit"}, "default_tenant_id": "partner_permit_standard"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            snapshot.write_text(
                json.dumps(
                    {
                        "partners": [
                            {
                                "tenant_id": "partner_yangdo_standard",
                                "channel_id": "partner_yangdo_template",
                                "offering_id": "yangdo_standard",
                                "systems": ["yangdo"],
                                "host": "partner-yangdo.example.com",
                                "missing_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
                                "api_key_env": "",
                            },
                            {
                                "tenant_id": "partner_permit_standard",
                                "channel_id": "partner_permit_template",
                                "offering_id": "permit_standard",
                                "systems": ["permit"],
                                "host": "partner-permit.example.com",
                                "missing_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
                                "api_key_env": "",
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            simulation.write_text(
                json.dumps(
                    {
                        "summary": {"all_ready_after_simulation": True, "ready_after_simulation_count": 2},
                        "partners": [
                            {
                                "tenant_id": "partner_yangdo_standard",
                                "simulated_decision": "ready",
                                "simulated_remaining_required_inputs": [],
                                "removed_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
                            },
                            {
                                "tenant_id": "partner_permit_standard",
                                "simulated_decision": "ready",
                                "simulated_remaining_required_inputs": [],
                                "removed_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_partner_input_handoff_packet(
                registry_path=registry,
                channels_path=channels,
                snapshot_path=snapshot,
                simulation_path=simulation,
            )

            self.assertEqual(payload["summary"]["partner_count"], 2)
            self.assertTrue(payload["summary"]["uniform_required_inputs"])
            self.assertEqual(
                payload["summary"]["common_required_inputs"],
                ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
            )
            self.assertTrue(payload["summary"]["ready_after_recommended_injection"])
            self.assertTrue(payload["summary"]["copy_paste_ready"])
            self.assertEqual(payload["partners"][0]["expected_api_key_env"], "TENANT_API_KEY_PARTNER_YANGDO_STANDARD")
            self.assertEqual(payload["partners"][1]["recommended_source_id"], "permit_source")
            self.assertEqual(
                payload["partners"][0]["copy_paste_packet"]["proof_url_field"],
                "proof_url=https://partner-yangdo.example.com/contracts/partner_yangdo_standard",
            )


if __name__ == "__main__":
    unittest.main()
