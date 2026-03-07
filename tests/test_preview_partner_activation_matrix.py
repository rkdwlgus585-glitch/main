import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.preview_partner_activation_matrix import build_preview_matrix, main


class PreviewPartnerActivationMatrixTests(unittest.TestCase):
    def test_build_preview_matrix_tracks_removed_inputs(self):
        seen_cmds = []
        results = iter(
            [
                {"ok": False, "json": {"ok": False, "activation_blockers": ["missing_source_proof_url_pending", "missing_api_key_value", "missing_approved_data_source"], "handoff": {"activation_ready": False, "remaining_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"], "resolved_inputs": [], "next_actions": ["proof", "key", "approval"]}}},
                {"ok": False, "json": {"ok": False, "activation_blockers": ["missing_api_key_value", "missing_approved_data_source"], "handoff": {"activation_ready": False, "remaining_required_inputs": ["partner_api_key", "partner_data_source_approval"], "resolved_inputs": ["partner_proof_url"], "next_actions": ["key", "approval"]}}},
                {"ok": False, "json": {"ok": False, "activation_blockers": ["missing_approved_data_source"], "handoff": {"activation_ready": False, "remaining_required_inputs": ["partner_data_source_approval"], "resolved_inputs": ["partner_proof_url", "partner_api_key"], "next_actions": ["approval"]}}},
                {"ok": True, "json": {"ok": True, "activation_blockers": [], "handoff": {"activation_ready": True, "remaining_required_inputs": [], "resolved_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"], "next_actions": ["handoff"]}}},
            ]
        )
        def _fake_run(cmd):
            seen_cmds.append(cmd)
            return next(results)

        with patch("scripts.preview_partner_activation_matrix._run_flow", side_effect=_fake_run):
            payload = build_preview_matrix(
                offering_id="permit_standard",
                tenant_id="partner_permit_demo",
                channel_id="partner_permit_demo",
                host="permit-demo.example.com",
                brand_name="Permit Demo",
                proof_url="https://example.com/proof",
                api_key_value="test-key",
                smoke_base_url="",
            )
        self.assertEqual(payload["recommended_path"]["scenario"], "proof_key_and_approval")
        self.assertEqual(payload["scenarios"][1]["removed_inputs_since_previous"], ["partner_proof_url"])
        self.assertEqual(payload["scenarios"][2]["removed_inputs_since_previous"], ["partner_api_key"])
        self.assertTrue(all("--report" in cmd for cmd in seen_cmds))

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            json_path = Path(td) / "preview.json"
            md_path = Path(td) / "preview.md"
            argv = [
                "preview_partner_activation_matrix.py",
                "--offering-id",
                "permit_standard",
                "--tenant-id",
                "partner_permit_demo",
                "--channel-id",
                "partner_permit_demo",
                "--host",
                "permit-demo.example.com",
                "--brand-name",
                "Permit Demo",
                "--json",
                str(json_path),
                "--md",
                str(md_path),
            ]
            fake_payload = {
                "generated_at": "2026-03-06 00:00:00",
                "offering_id": "permit_standard",
                "tenant_id": "partner_permit_demo",
                "channel_id": "partner_permit_demo",
                "host": "permit-demo.example.com",
                "scenarios": [],
                "recommended_path": {"scenario": "proof_key_and_approval", "remaining_required_inputs": [], "next_actions": ["handoff"]},
            }
            with patch("scripts.preview_partner_activation_matrix.build_preview_matrix", return_value=fake_payload):
                with patch("sys.argv", argv):
                    code = main()
            self.assertEqual(code, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["recommended_path"]["scenario"], "proof_key_and_approval")
            self.assertIn("Partner Activation Preview", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
