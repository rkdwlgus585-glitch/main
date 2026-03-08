import unittest

from scripts import generate_permit_review_case_presets


class GeneratePermitReviewCasePresetsTests(unittest.TestCase):
    def test_build_review_case_presets_extracts_edge_cases(self):
        goldset = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_id": "permit-family-123",
                    "cases": [
                        {
                            "case_id": "permit-family-123:shortfall_fail:A001",
                            "case_kind": "shortfall_fail",
                            "service_code": "A001",
                            "service_name": "건축공사업(종합)",
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                            "inputs": {
                                "industry_selector": "A001",
                                "capital_eok": 3.4,
                                "technicians_count": 5,
                                "other_requirement_checklist": {"facility_equipment": True},
                            },
                            "expected": {
                                "overall_status": "shortfall",
                                "capital_gap_eok": 0.1,
                                "technicians_gap": 1,
                                "review_reason": "capital_and_technician_shortfall",
                                "manual_review_expected": False,
                                "proof_coverage_ratio": "39/39",
                            },
                        },
                        {
                            "case_id": "permit-family-123:capital_only_fail:A001",
                            "case_kind": "capital_only_fail",
                            "service_code": "A001",
                            "service_name": "건축공사업(종합)",
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                            "inputs": {
                                "industry_selector": "A001",
                                "capital_eok": 3.4,
                                "technicians_count": 6,
                                "other_requirement_checklist": {"equipment_inventory": True},
                            },
                            "expected": {
                                "overall_status": "shortfall",
                                "capital_gap_eok": 0.1,
                                "technicians_gap": 0,
                                "review_reason": "capital_shortfall_only",
                                "manual_review_expected": False,
                                "proof_coverage_ratio": "39/39",
                            },
                        },
                        {
                            "case_id": "permit-family-123:document_missing_review:A001",
                            "case_kind": "document_missing_review",
                            "service_code": "A001",
                            "service_name": "건축공사업(종합)",
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                            "inputs": {
                                "industry_selector": "A001",
                                "capital_eok": 3.5,
                                "technicians_count": 6,
                                "other_requirement_checklist": {},
                            },
                            "expected": {
                                "overall_status": "shortfall",
                                "capital_gap_eok": 0.0,
                                "technicians_gap": 0,
                                "review_reason": "other_requirement_documents_missing",
                                "manual_review_expected": True,
                                "proof_coverage_ratio": "39/39",
                            },
                        },
                        {
                            "case_id": "permit-family-123:boundary_pass:A001",
                            "case_kind": "boundary_pass",
                            "service_code": "A001",
                            "service_name": "건축공사업(종합)",
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                            "inputs": {
                                "industry_selector": "A001",
                                "capital_eok": 3.5,
                                "technicians_count": 6,
                                "other_requirement_checklist": {"equipment_inventory": True},
                            },
                            "expected": {
                                "overall_status": "pass",
                                "capital_gap_eok": 0.0,
                                "technicians_gap": 0,
                                "review_reason": "",
                                "manual_review_expected": False,
                                "proof_coverage_ratio": "39/39",
                            },
                        },
                    ],
                }
            ]
        }

        report = generate_permit_review_case_presets.build_review_case_presets(
            permit_family_case_goldset=goldset,
        )

        self.assertEqual(report["summary"]["family_total"], 1)
        self.assertEqual(report["summary"]["preset_total"], 3)
        self.assertEqual(report["summary"]["shortfall_fail_preset_total"], 1)
        self.assertEqual(report["summary"]["capital_only_fail_preset_total"], 1)
        self.assertEqual(report["summary"]["document_missing_review_preset_total"], 1)
        self.assertEqual(report["summary"]["manual_review_expected_total"], 1)
        self.assertFalse(report["summary"]["preset_ready"])
        family = report["families"][0]
        self.assertEqual(family["preset_total"], 3)
        self.assertEqual(family["presets"][0]["preset_label"], "자본금·기술인력 동시 부족 프리셋")
        self.assertEqual(family["presets"][0]["expected_outcome"]["review_reason"], "capital_and_technician_shortfall")
        self.assertTrue(family["presets"][2]["expected_outcome"]["manual_review_expected"])


if __name__ == "__main__":
    unittest.main()
