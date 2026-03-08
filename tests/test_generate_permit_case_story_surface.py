import unittest

from scripts import generate_permit_case_story_surface


class GeneratePermitCaseStorySurfaceTests(unittest.TestCase):
    def test_build_case_story_surface_summarizes_representative_reasons(self):
        presets = {
            "families": [
                {
                    "family_key": "전기공사업법 시행령",
                    "claim_id": "permit-family-456",
                    "preset_total": 3,
                    "presets": [
                        {
                            "preset_id": "p1",
                            "case_kind": "capital_only_fail",
                            "service_code": "E001",
                            "service_name": "전기공사업",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "capital_shortfall_only",
                                "manual_review_expected": False,
                            },
                        },
                        {
                            "preset_id": "p2",
                            "case_kind": "technician_only_fail",
                            "service_code": "E001",
                            "service_name": "전기공사업",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "technician_shortfall_only",
                                "manual_review_expected": False,
                            },
                        },
                        {
                            "preset_id": "p3",
                            "case_kind": "document_missing_review",
                            "service_code": "E001",
                            "service_name": "전기공사업",
                            "expected_outcome": {
                                "overall_status": "shortfall",
                                "review_reason": "other_requirement_documents_missing",
                                "manual_review_expected": True,
                            },
                        },
                    ],
                }
            ]
        }
        guard = {"summary": {"release_guard_ready": True}}

        report = generate_permit_case_story_surface.build_case_story_surface(
            permit_review_case_presets=presets,
            permit_case_release_guard=guard,
        )

        self.assertEqual(report["summary"]["family_total"], 1)
        self.assertEqual(report["summary"]["edge_case_total"], 3)
        self.assertEqual(report["summary"]["review_reason_total"], 3)
        self.assertEqual(report["summary"]["manual_review_family_total"], 1)
        self.assertTrue(report["summary"]["story_ready"])
        family = report["families"][0]
        self.assertEqual(family["manual_review_preset_total"], 1)
        self.assertEqual(len(family["operator_story_points"]), 3)


if __name__ == "__main__":
    unittest.main()
