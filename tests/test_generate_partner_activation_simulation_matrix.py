import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_partner_activation_simulation_matrix import build_simulation_matrix


class GeneratePartnerActivationSimulationMatrixTests(unittest.TestCase):
    @patch("scripts.generate_partner_activation_simulation_matrix.build_simulation_report")
    @patch("scripts.generate_partner_activation_simulation_matrix.build_partner_input_snapshot")
    def test_build_simulation_matrix_uses_tenant_row_as_current_baseline(self, mock_snapshot, mock_report):
        mock_snapshot.return_value = {
            "partners": [
                {
                    "tenant_id": "partner_yangdo_standard",
                    "channel_id": "partner_yangdo_template",
                    "offering_id": "yangdo_standard",
                    "host": "partner-yangdo.example.com",
                    "current_scenario": "baseline",
                    "missing_required_inputs": ["partner_proof_url", "partner_api_key"],
                },
                {
                    "tenant_id": "partner_permit_standard",
                    "channel_id": "partner_permit_template",
                    "offering_id": "permit_standard",
                    "host": "partner-permit.example.com",
                    "current_scenario": "baseline",
                    "missing_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
                },
            ]
        }
        mock_report.side_effect = [
            {
                "simulated": {
                    "partner_activation_decision": "ready",
                    "remaining_required_inputs": [],
                    "preview_alignment_ok": True,
                    "resolution_ok": True,
                },
                "delta": {"simulated_required_count": 0},
                "refresh_summary": {"ok": True},
            },
            {
                "simulated": {
                    "partner_activation_decision": "ready",
                    "remaining_required_inputs": [],
                    "preview_alignment_ok": True,
                    "resolution_ok": True,
                },
                "delta": {"simulated_required_count": 0},
                "refresh_summary": {"ok": True},
            },
        ]

        payload = build_simulation_matrix(
            registry_path=Path("C:/tmp/tenant_registry.json"),
            channels_path=Path("C:/tmp/channel_profiles.json"),
            env_path=Path("C:/tmp/.env"),
        )

        self.assertEqual(payload["summary"]["partner_count"], 2)
        self.assertEqual(payload["summary"]["baseline_ready_count"], 0)
        self.assertEqual(payload["summary"]["ready_after_simulation_count"], 2)
        self.assertEqual(payload["summary"]["newly_ready_count"], 2)
        self.assertTrue(payload["summary"]["all_ready_after_simulation"])
        self.assertEqual(
            payload["partners"][0]["current_missing_required_inputs"],
            ["partner_proof_url", "partner_api_key"],
        )
        self.assertEqual(
            payload["partners"][0]["removed_required_inputs"],
            ["partner_proof_url", "partner_api_key"],
        )
        self.assertEqual(
            payload["partners"][1]["removed_required_inputs"],
            ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
        )


if __name__ == "__main__":
    unittest.main()
