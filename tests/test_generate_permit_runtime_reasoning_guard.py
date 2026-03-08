import unittest

from scripts import generate_permit_runtime_reasoning_guard


class GeneratePermitRuntimeReasoningGuardTests(unittest.TestCase):
    def test_build_guard_report_flags_missing_prompt_bound_reasons(self):
        report = generate_permit_runtime_reasoning_guard.build_guard_report(
            permit_review_reason_decision_ladder={
                "summary": {
                    "review_reason_total": 4,
                    "prompt_bound_reason_total": 1,
                    "decision_ladder_ready": True,
                },
                "ladders": [
                    {
                        "review_reason": "other_requirement_documents_missing",
                        "review_reason_label": "서류 보완 검토",
                        "inspect_first": "누락 서류 확인",
                        "binding_preset_ids": ["preset-doc"],
                    },
                    {
                        "review_reason": "capital_and_technician_shortfall",
                        "review_reason_label": "자본금·기술인력 동시 부족",
                        "inspect_first": "자본금과 기술인력 증빙",
                        "binding_preset_ids": [],
                    },
                ],
            },
            permit_demo_surface_observability={
                "summary": {
                    "observability_ready": True,
                    "runtime_reasoning_card_surface_ready": True,
                    "runtime_prompt_case_binding_surface_ready": True,
                    "runtime_critical_prompt_surface_ready": True,
                }
            },
            permit_surface_drift_digest={
                "summary": {
                    "digest_ready": True,
                    "delta_ready": True,
                    "reasoning_changed_surface_total": 0,
                    "reasoning_regression_total": 0,
                }
            },
            permit_prompt_case_binding_packet={"summary": {"packet_ready": True, "representative_family_total": 6}},
        )

        summary = report["summary"]
        self.assertFalse(summary["guard_ready"])
        self.assertEqual(summary["binding_gap_total"], 3)
        self.assertEqual(summary["missing_binding_reason_total"], 1)
        self.assertTrue(summary["runtime_reasoning_card_surface_ready"])
        self.assertEqual(report["missing_binding_reason_preview"][0]["review_reason"], "capital_and_technician_shortfall")

    def test_build_guard_report_turns_green_when_reasoning_contract_is_closed(self):
        report = generate_permit_runtime_reasoning_guard.build_guard_report(
            permit_review_reason_decision_ladder={
                "summary": {
                    "review_reason_total": 2,
                    "prompt_bound_reason_total": 2,
                    "decision_ladder_ready": True,
                },
                "ladders": [
                    {
                        "review_reason": "other_requirement_documents_missing",
                        "review_reason_label": "서류 보완 검토",
                        "inspect_first": "누락 서류 확인",
                        "binding_preset_ids": ["preset-doc"],
                    },
                    {
                        "review_reason": "capital_and_technician_shortfall",
                        "review_reason_label": "자본금·기술인력 동시 부족",
                        "inspect_first": "자본금과 기술인력 증빙",
                        "binding_preset_ids": ["preset-gap"],
                    },
                ],
            },
            permit_demo_surface_observability={
                "summary": {
                    "observability_ready": True,
                    "runtime_reasoning_card_surface_ready": True,
                    "runtime_prompt_case_binding_surface_ready": True,
                    "runtime_critical_prompt_surface_ready": True,
                }
            },
            permit_surface_drift_digest={
                "summary": {
                    "digest_ready": True,
                    "delta_ready": True,
                    "reasoning_changed_surface_total": 0,
                    "reasoning_regression_total": 0,
                }
            },
            permit_prompt_case_binding_packet={"summary": {"packet_ready": True, "representative_family_total": 6}},
        )

        self.assertTrue(report["summary"]["guard_ready"])
        self.assertEqual(report["summary"]["binding_gap_total"], 0)
        self.assertEqual(report["missing_binding_reason_preview"], [])


if __name__ == "__main__":
    unittest.main()
