import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_permit_prompt_case_binding_packet import build_packet


class GeneratePermitPromptCaseBindingPacketTests(unittest.TestCase):
    def test_build_packet_creates_operator_jump_table(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            presets = base / "presets.json"
            stories = base / "stories.json"
            operator_demo = base / "operator_demo.json"

            brainstorm.write_text(
                json.dumps(
                    {
                        "summary": {"prompt_doc_ready": True},
                        "current_execution_lane": {"id": "prompt_case_binding", "title": "prompt case binding"},
                        "critical_prompts": {
                            "founder_mode_questions": [
                                "이 질문이 바로 대표 케이스로 이어지는가?",
                                "수동 판정 케이스를 즉시 식별하는가?",
                            ]
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            founder.write_text(
                json.dumps({"summary": {"primary_system": "permit", "primary_lane_id": "prompt_case_binding"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            presets.write_text(json.dumps({"summary": {"preset_ready": True}}, ensure_ascii=False), encoding="utf-8")
            stories.write_text(
                json.dumps(
                    {
                        "summary": {"story_ready": True},
                        "families": [
                            {
                                "claim_id": "claim-1",
                                "representative_cases": [
                                    {
                                        "case_kind": "capital_only_fail",
                                        "service_code": "permit-001",
                                        "expected_status": "shortfall",
                                        "review_reason": "capital shortfall",
                                        "manual_review_expected": False,
                                    },
                                    {
                                        "case_kind": "document_missing_review",
                                        "service_code": "permit-001",
                                        "expected_status": "manual_review",
                                        "review_reason": "document missing",
                                        "manual_review_expected": True,
                                    },
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operator_demo.write_text(
                json.dumps(
                    {
                        "summary": {"operator_demo_ready": True},
                        "families": [
                            {
                                "family_key": "permit-family",
                                "claim_id": "claim-1",
                                "demo_cases": [
                                    {
                                        "case_kind": "capital_only_fail",
                                        "preset_id": "preset-capital",
                                        "service_code": "permit-001",
                                        "expected_status": "shortfall",
                                        "review_reason": "capital shortfall",
                                        "manual_review_expected": False,
                                    },
                                    {
                                        "case_kind": "document_missing_review",
                                        "preset_id": "preset-doc",
                                        "service_code": "permit-001",
                                        "expected_status": "manual_review",
                                        "review_reason": "document missing",
                                        "manual_review_expected": True,
                                    },
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                presets_path=presets,
                stories_path=stories,
                operator_demo_path=operator_demo,
            )

            summary = payload["summary"]
            self.assertTrue(summary["packet_ready"])
            self.assertEqual(summary["lane_id"], "prompt_case_binding")
            self.assertTrue(summary["founder_lane_match"])
            self.assertTrue(summary["operator_jump_table_ready"])
            self.assertEqual(summary["representative_family_total"], 1)
            self.assertEqual(summary["representative_case_total"], 2)
            self.assertEqual(summary["manual_review_case_total"], 1)
            self.assertEqual(payload["operator_jump_table"][0]["claim_id"], "claim-1")
            self.assertEqual(payload["operator_jump_table"][0]["jump_targets"][0]["preset_id"], "preset-capital")

    def test_build_packet_ignores_non_permit_founder_lane(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            brainstorm = base / "brainstorm.json"
            founder = base / "founder.json"
            presets = base / "presets.json"
            stories = base / "stories.json"
            operator_demo = base / "operator_demo.json"

            brainstorm.write_text(
                json.dumps(
                    {
                        "summary": {"prompt_doc_ready": True},
                        "current_execution_lane": {
                            "id": "capital_registration_logic_lock",
                            "title": "capital and registration logic lock",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            founder.write_text(
                json.dumps(
                    {"summary": {"primary_system": "yangdo", "primary_lane_id": "special_sector_publication_guard"}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            presets.write_text(json.dumps({"summary": {"preset_ready": True}}, ensure_ascii=False), encoding="utf-8")
            stories.write_text(
                json.dumps(
                    {
                        "summary": {"story_ready": True},
                        "families": [{"claim_id": "claim-1", "representative_cases": []}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operator_demo.write_text(
                json.dumps(
                    {
                        "summary": {"operator_demo_ready": True},
                        "families": [
                            {
                                "family_key": "permit-family",
                                "claim_id": "claim-1",
                                "demo_cases": [
                                    {
                                        "case_kind": "capital_only_fail",
                                        "preset_id": "preset-capital",
                                        "service_code": "permit-001",
                                        "expected_status": "shortfall",
                                    }
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_packet(
                brainstorm_path=brainstorm,
                founder_path=founder,
                presets_path=presets,
                stories_path=stories,
                operator_demo_path=operator_demo,
            )

            summary = payload["summary"]
            self.assertEqual(summary["lane_id"], "capital_registration_logic_lock")
            self.assertTrue(summary["founder_lane_match"])
            self.assertTrue(summary["packet_ready"])


if __name__ == "__main__":
    unittest.main()
