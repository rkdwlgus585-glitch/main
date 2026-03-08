import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_critical_prompt_surface_packet import build_packet


class GeneratePermitCriticalPromptSurfacePacketTests(unittest.TestCase):
    def test_build_packet_marks_founder_lane_surface_ready(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            case_binding = base / "case_binding.json"

            brainstorm.write_text(json.dumps({
                "summary": {"prompt_doc_ready": True},
                "current_execution_lane": {
                    "id": "partner_binding_parity",
                    "title": "partner binding parity",
                    "current_gap": "partner-safe runtime surfaces are not yet aligned",
                    "evidence": "partner widget and api packets do not expose the same shortcut",
                    "proposed_next_step": "publish a partner-safe prompt-bound case surface",
                    "success_metric": "partner surfaces show one prompt-bound case per family",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": ["Does it cut operator lookup time?"],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {"primary_system": "permit", "primary_lane_id": "prompt_case_binding"},
                "primary_execution": {
                    "id": "prompt_case_binding",
                    "title": "prompt case binding",
                    "current_gap": "operators still bridge founder questions to presets manually",
                    "evidence": "jump targets are not yet canonical in permit surfaces",
                    "proposed_next_step": "bind founder prompts to representative permit cases",
                    "success_metric": "operators can jump from founder prompt to the right permit lane",
                },
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({"summary": {"packet_ready": True, "lane_id": "prompt_case_binding", "founder_lane_match": True, "operator_jump_table_ready": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                case_binding_path=case_binding,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertEqual(summary["lane_id"], "prompt_case_binding")
            self.assertEqual(summary["current_execution_lane_id"], "partner_binding_parity")
            self.assertFalse(summary["current_execution_lane_matches_packet"])
            self.assertTrue(summary["operator_surface_ready"])
            self.assertTrue(summary["release_surface_ready"])
            self.assertTrue(summary["founder_lane_match"])
            self.assertTrue(summary["prompt_case_binding_ready"])
            self.assertTrue(summary["operator_jump_table_ready"])
            self.assertTrue(summary["compact_lens_ready"])
            self.assertTrue(summary["runtime_surface_contract_ready"])
            self.assertTrue(summary["release_surface_contract_ready"])
            self.assertTrue(summary["operator_surface_contract_ready"])
            self.assertIn("permit_prompt_case_binding_ready == true", payload["verification_targets"])
            self.assertIn("permit_critical_prompt_compact_lens_ready == true", payload["verification_targets"])
            self.assertIn("permit_service_alignment_ok == true", payload["verification_targets"])
            self.assertIn("founder primary lane == permit/prompt_case_binding", payload["verification_targets"])
            compact_lens = payload["compact_decision_lens"]
            self.assertEqual(compact_lens["lane_id"], "prompt_case_binding")
            self.assertTrue(compact_lens["lens_ready"])
            self.assertTrue(compact_lens["inspect_first"])
            self.assertTrue(compact_lens["next_action"])
            self.assertTrue(compact_lens["falsification_test"])
            self.assertIn("Keep the critical prompt block visible in operator-facing permit packets.", payload["next_actions"])
            self.assertIn("Keep the compact decision lens reusable across runtime, release, and operator surfaces.", payload["next_actions"])

    def test_build_packet_ignores_non_permit_founder_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            copy_packet = base / "copy.json"
            ux_packet = base / "ux.json"
            alignment = base / "alignment.json"
            case_binding = base / "case_binding.json"

            brainstorm.write_text(json.dumps({
                "summary": {"prompt_doc_ready": True},
                "current_execution_lane": {
                    "id": "capital_registration_logic_lock",
                    "title": "capital and registration logic lock",
                    "current_gap": "core-only boundary guard",
                    "evidence": "capital packet still needs a runtime-safe guard",
                    "proposed_next_step": "refresh the capital logic chain",
                    "success_metric": "capital packet and runtime assertions stay aligned",
                },
                "critical_prompts": {
                    "execution_prompt": "permit execution prompt",
                    "brainstorm_prompt": "permit brainstorm prompt",
                    "first_principles_prompt": "permit first principles prompt",
                    "founder_mode_questions": ["Does it reduce operator delay?"],
                },
            }, ensure_ascii=False), encoding="utf-8")
            founder.write_text(json.dumps({
                "summary": {"primary_system": "yangdo", "primary_lane_id": "special_sector_publication_guard"},
                "primary_execution": {
                    "id": "special_sector_publication_guard",
                    "title": "special sector publication guard",
                },
            }, ensure_ascii=False), encoding="utf-8")
            copy_packet.write_text(json.dumps({"summary": {"service_copy_ready": True}}, ensure_ascii=False), encoding="utf-8")
            ux_packet.write_text(json.dumps({"summary": {"packet_ready": True}}, ensure_ascii=False), encoding="utf-8")
            alignment.write_text(json.dumps({"summary": {"alignment_ok": True}}, ensure_ascii=False), encoding="utf-8")
            case_binding.write_text(json.dumps({"summary": {"packet_ready": True, "operator_jump_table_ready": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                copy_path=copy_packet,
                ux_path=ux_packet,
                alignment_path=alignment,
                case_binding_path=case_binding,
            )

            summary = payload["summary"]
            self.assertEqual(summary["lane_id"], "capital_registration_logic_lock")
            self.assertTrue(summary["founder_lane_match"])
            self.assertTrue(summary["packet_ready"])
            self.assertIn(
                "current permit execution lane == capital_registration_logic_lock",
                payload["verification_targets"],
            )


if __name__ == "__main__":
    unittest.main()
