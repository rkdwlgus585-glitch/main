import unittest

from scripts import generate_permit_operator_demo_packet


class GeneratePermitOperatorDemoPacketTests(unittest.TestCase):
    def test_build_operator_demo_packet_links_presets_story_and_proof(self):
        review_case_presets = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_id": "permit-family-123",
                    "presets": [
                        {
                            "preset_id": "preset-0",
                            "case_kind": "shortfall_fail",
                            "preset_label": "자본금·기술인력 동시 부족 프리셋",
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업(종합)",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "capital_and_technician_shortfall",
                                "manual_review_expected": False,
                                "proof_coverage_ratio": "39/39",
                            },
                            "operator_note": "동시 부족 시나리오",
                        },
                        {
                            "preset_id": "preset-1",
                            "case_kind": "capital_only_fail",
                            "preset_label": "자본금 부족 프리셋",
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업(종합)",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "capital_shortfall_only",
                                "manual_review_expected": False,
                                "proof_coverage_ratio": "39/39",
                            },
                            "operator_note": "자본금 부족 시나리오",
                        },
                        {
                            "preset_id": "preset-2",
                            "case_kind": "document_missing_review",
                            "preset_label": "서류 누락 검토 프리셋",
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업(종합)",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "other_requirement_documents_missing",
                                "manual_review_expected": True,
                                "proof_coverage_ratio": "39/39",
                            },
                            "operator_note": "서류 누락 시나리오",
                        },
                        {
                            "preset_id": "preset-3",
                            "case_kind": "technician_only_fail",
                            "preset_label": "기술인력 부족 프리셋",
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업(종합)",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "technician_shortfall_only",
                                "manual_review_expected": False,
                                "proof_coverage_ratio": "39/39",
                            },
                            "operator_note": "기술인력 부족 시나리오",
                        },
                    ],
                }
            ]
        }
        case_story_surface = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "operator_story_points": [
                        "자본금 부족과 기술인력 부족을 분리해 설명합니다.",
                        "서류 누락은 수동 검토로 분기합니다.",
                    ],
                }
            ]
        }
        patent_evidence_bundle = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_packet": {
                        "claim_id": "permit-family-123",
                        "claim_title": "건설업 등록기준 패킷",
                        "source_proof_summary": {
                            "proof_coverage_ratio": "39/39",
                            "checksum_samples": ["aaa", "bbb"],
                        },
                    },
                }
            ]
        }

        report = generate_permit_operator_demo_packet.build_operator_demo_packet(
            permit_review_case_presets=review_case_presets,
            permit_case_story_surface=case_story_surface,
            permit_patent_evidence_bundle=patent_evidence_bundle,
        )

        self.assertTrue(report["summary"]["operator_demo_ready"])
        self.assertEqual(report["summary"]["family_total"], 1)
        self.assertEqual(report["summary"]["demo_case_total"], 4)
        self.assertEqual(report["summary"]["manual_review_demo_total"], 1)
        self.assertEqual(report["summary"]["prompt_case_binding_total"], 1)
        self.assertEqual(report["summary"]["review_reason_total"], 4)
        family = report["families"][0]
        self.assertEqual(family["proof_coverage_ratio"], "39/39")
        self.assertEqual(family["checksum_samples"], ["aaa", "bbb"])
        self.assertEqual(len(family["demo_cases"]), 4)
        self.assertEqual(family["prompt_case_binding"]["preset_id"], "preset-2")
        self.assertTrue(family["prompt_case_binding"]["manual_review_expected"])
        self.assertEqual(family["demo_cases"][0]["review_reason"], "capital_and_technician_shortfall")
        self.assertEqual(family["demo_cases"][1]["demo_steps"][1], "`자본금 부족 프리셋` 클릭")
        markdown = generate_permit_operator_demo_packet.render_markdown(report)
        self.assertIn("prompt_case_binding_total", markdown)
        self.assertIn("preset `preset-2`", markdown)
        self.assertIn("focus `manual_review_gate`", markdown)


if __name__ == "__main__":
    unittest.main()
