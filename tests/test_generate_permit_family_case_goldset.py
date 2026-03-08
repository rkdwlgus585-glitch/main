import unittest

from scripts import generate_permit_family_case_goldset


class GeneratePermitFamilyCaseGoldsetTests(unittest.TestCase):
    def test_build_family_case_goldset_generates_edge_cases_per_family(self):
        focus_family_registry = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2 건설업 등록기준",
                    "registration_requirement_profile": {
                        "capital_eok": 3.5,
                        "technicians_required": 5,
                        "other_components": ["equipment_inventory"],
                    },
                    "raw_source_proof": {
                        "capture_meta": {"family_key": "건설산업기본법 시행령"},
                    },
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "service_name": "토목공사업(종합)",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2 건설업 등록기준",
                    "registration_requirement_profile": {
                        "capital_eok": 5.0,
                        "technicians_required": 6,
                        "other_components": ["equipment_inventory", "deposit_hold_days"],
                    },
                    "raw_source_proof": {
                        "capture_meta": {"family_key": "건설산업기본법 시행령"},
                    },
                },
            ]
        }
        patent_bundle = {
            "summary": {"claim_packet_complete_family_total": 1},
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_packet": {
                        "claim_id": "permit-family-123",
                        "source_proof_summary": {
                            "proof_coverage_ratio": "2/2",
                            "checksum_sample_total": 2,
                        },
                    },
                }
            ],
        }

        bundle = generate_permit_family_case_goldset.build_family_case_goldset(
            focus_family_registry=focus_family_registry,
            permit_patent_evidence_bundle=patent_bundle,
        )

        self.assertEqual(bundle["summary"]["family_total"], 1)
        self.assertEqual(bundle["summary"]["case_total"], 6)
        self.assertEqual(bundle["summary"]["minimum_pass_case_total"], 1)
        self.assertEqual(bundle["summary"]["boundary_case_total"], 1)
        self.assertEqual(bundle["summary"]["shortfall_case_total"], 1)
        self.assertEqual(bundle["summary"]["capital_only_fail_case_total"], 1)
        self.assertEqual(bundle["summary"]["technician_only_fail_case_total"], 1)
        self.assertEqual(bundle["summary"]["document_missing_review_case_total"], 1)
        self.assertEqual(bundle["summary"]["edge_case_total"], 3)
        self.assertEqual(bundle["summary"]["edge_case_family_total"], 1)
        self.assertEqual(bundle["summary"]["manual_review_case_total"], 1)
        self.assertTrue(bundle["summary"]["edge_case_ready"])
        self.assertTrue(bundle["summary"]["goldset_ready"])
        family = bundle["families"][0]
        self.assertEqual(family["claim_id"], "permit-family-123")
        self.assertEqual(len(family["cases"]), 6)
        case_kinds = [case["case_kind"] for case in family["cases"]]
        self.assertEqual(
            case_kinds,
            [
                "minimum_pass",
                "boundary_pass",
                "shortfall_fail",
                "capital_only_fail",
                "technician_only_fail",
                "document_missing_review",
            ],
        )
        shortfall_case = family["cases"][2]
        self.assertEqual(shortfall_case["expected"]["overall_status"], "shortfall")
        self.assertGreaterEqual(shortfall_case["expected"]["capital_gap_eok"], 0.1)
        self.assertEqual(shortfall_case["expected"]["technicians_gap"], 1)
        self.assertEqual(shortfall_case["expected"]["review_reason"], "capital_and_technician_shortfall")
        document_missing_case = family["cases"][5]
        self.assertEqual(document_missing_case["expected"]["overall_status"], "shortfall")
        self.assertEqual(document_missing_case["expected"]["review_reason"], "other_requirement_documents_missing")
        self.assertTrue(document_missing_case["expected"]["manual_review_expected"])

    def test_build_family_case_goldset_falls_back_to_master_for_real_focus_family(self):
        patent_bundle = {
            "summary": {"claim_packet_complete_family_total": 1},
            "families": [
                {
                    "family_key": "목재의 지속가능한 이용에 관한 법률 시행령",
                    "claim_packet": {
                        "claim_id": "permit-family-wood",
                        "source_proof_summary": {
                            "proof_coverage_ratio": "1/1",
                            "checksum_sample_total": 1,
                        },
                    },
                }
            ],
        }
        master_catalog = {
            "industries": [
                {
                    "service_code": "09_27_03_P",
                    "service_name": "제재업",
                    "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                    "legal_basis_title": "목재생산업의 종류별 등록기준(제24조제1항 관련)",
                    "registration_requirement_profile": {
                        "focus_target": True,
                        "capital_eok": 0.3,
                        "technicians_required": 1,
                        "other_required": False,
                        "other_components": [],
                    },
                }
            ]
        }

        bundle = generate_permit_family_case_goldset.build_family_case_goldset(
            focus_family_registry={"industries": []},
            permit_patent_evidence_bundle=patent_bundle,
            master_catalog=master_catalog,
        )

        self.assertEqual(bundle["summary"]["family_total"], 1)
        family = bundle["families"][0]
        self.assertEqual(family["claim_id"], "permit-family-wood")
        self.assertEqual(family["row_total"], 1)
        self.assertEqual(family["cases"][5]["case_kind"], "document_missing_review")
        self.assertEqual(family["cases"][5]["expected"]["overall_status"], "pass")
        self.assertFalse(family["cases"][5]["expected"]["manual_review_expected"])


if __name__ == "__main__":
    unittest.main()
