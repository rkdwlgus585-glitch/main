import unittest

from scripts.generate_permit_review_reason_decision_ladder import build_report


class GeneratePermitReviewReasonDecisionLadderTests(unittest.TestCase):
    def test_build_report_creates_reason_ladders_from_story_and_demo(self):
        case_story_surface = {
            "summary": {
                "story_family_total": 3,
            },
            "families": [
                {
                    "claim_id": "permit-family-aaa111",
                    "representative_cases": [
                        {"preset_id": "preset-doc-a"},
                    ],
                },
                {
                    "family_key": "family-z",
                    "claim_id": "permit-family-zzz333",
                    "representative_cases": [
                        {"preset_id": "preset-both-z"},
                    ],
                },
                {
                    "claim_id": "permit-family-bbb222",
                    "representative_cases": [
                        {"preset_id": "preset-tech-b"},
                    ],
                },
            ],
        }
        operator_demo_packet = {
            "summary": {
                "family_total": 3,
            },
            "families": [
                {
                    "family_key": "family-a",
                    "claim_id": "permit-family-aaa111",
                    "prompt_case_binding": {
                        "preset_id": "preset-doc-a",
                        "review_reason": "other_requirement_documents_missing",
                        "binding_focus": "manual_review_gate",
                        "binding_question": "어디서 자동판단을 멈출 것인가.",
                    },
                    "demo_cases": [
                        {
                            "preset_id": "preset-doc-a",
                            "service_name": "건축공사업",
                            "expected_status": "shortfall",
                            "review_reason": "other_requirement_documents_missing",
                            "manual_review_expected": True,
                        }
                    ],
                },
                {
                    "family_key": "family-z",
                    "claim_id": "permit-family-zzz333",
                    "prompt_case_binding": {
                        "preset_id": "preset-both-z",
                        "review_reason": "capital_and_technician_shortfall",
                        "binding_focus": "capital_and_technician_gap_first",
                        "binding_question": "두 핵심 요건이 모두 부족한가.",
                    },
                    "demo_cases": [
                        {
                            "preset_id": "preset-both-z",
                            "service_name": "정보통신공사업",
                            "expected_status": "shortfall",
                            "review_reason": "capital_and_technician_shortfall",
                            "manual_review_expected": False,
                        }
                    ],
                },
                {
                    "family_key": "family-b",
                    "claim_id": "permit-family-bbb222",
                    "prompt_case_binding": {
                        "preset_id": "preset-tech-b",
                        "review_reason": "technician_shortfall_only",
                        "binding_focus": "technician_gap_first",
                        "binding_question": "기술인력 부족을 먼저 고정했는가.",
                    },
                    "demo_cases": [
                        {
                            "preset_id": "preset-tech-b",
                            "service_name": "전기공사업",
                            "expected_status": "shortfall",
                            "review_reason": "technician_shortfall_only",
                            "manual_review_expected": False,
                        }
                    ],
                },
            ],
        }

        report = build_report(
            permit_case_story_surface=case_story_surface,
            permit_operator_demo_packet=operator_demo_packet,
        )

        summary = report["summary"]
        self.assertTrue(summary["decision_ladder_ready"])
        self.assertEqual(summary["review_reason_total"], 3)
        self.assertEqual(summary["manual_review_gate_total"], 1)
        self.assertEqual(summary["prompt_bound_reason_total"], 3)
        self.assertEqual(summary["execution_lane_id"], "review_reason_decision_ladder")
        self.assertEqual(summary["parallel_lane_id"], "thinking_prompt_bundle_lock")

        first = report["ladders"][0]
        self.assertEqual(first["review_reason"], "other_requirement_documents_missing")
        self.assertTrue(first["manual_review_gate"])
        self.assertIn("document_ready", first["missing_input_focus"])
        self.assertIn("preset-doc-a", first["binding_preset_ids"])
        second = report["ladders"][1]
        self.assertEqual(second["review_reason"], "capital_and_technician_shortfall")
        self.assertIn("capital_eok", second["missing_input_focus"])
        self.assertIn("technicians_count", second["missing_input_focus"])

    def test_build_report_keeps_reason_binding_even_when_prompt_binding_points_elsewhere(self):
        report = build_report(
            permit_case_story_surface={
                "summary": {"story_family_total": 1},
                "families": [
                    {
                        "claim_id": "permit-family-aaa111",
                        "representative_cases": [{"preset_id": "preset-gap-a"}],
                    }
                ],
            },
            permit_operator_demo_packet={
                "summary": {"family_total": 1},
                "families": [
                    {
                        "family_key": "family-a",
                        "claim_id": "permit-family-aaa111",
                        "prompt_case_binding": {
                            "preset_id": "preset-doc-a",
                            "review_reason": "other_requirement_documents_missing",
                            "binding_focus": "manual_review_gate",
                            "binding_question": "서류 누락 우선 확인",
                        },
                        "demo_cases": [
                            {
                                "preset_id": "preset-gap-a",
                                "service_name": "전기공사업",
                                "expected_status": "shortfall",
                                "review_reason": "capital_and_technician_shortfall",
                                "manual_review_expected": False,
                            },
                            {
                                "preset_id": "preset-doc-a",
                                "service_name": "전기공사업",
                                "expected_status": "shortfall",
                                "review_reason": "other_requirement_documents_missing",
                                "manual_review_expected": True,
                            },
                        ],
                    }
                ],
            },
        )

        ladder_by_reason = {row["review_reason"]: row for row in report["ladders"]}
        self.assertEqual(report["summary"]["prompt_bound_reason_total"], 2)
        self.assertIn("preset-gap-a", ladder_by_reason["capital_and_technician_shortfall"]["binding_preset_ids"])
        self.assertIn(
            "capital_and_technician_gap_first",
            ladder_by_reason["capital_and_technician_shortfall"]["binding_focuses"],
        )


if __name__ == "__main__":
    unittest.main()
