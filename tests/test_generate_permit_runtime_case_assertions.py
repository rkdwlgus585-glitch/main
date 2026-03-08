import base64
import gzip
import json
import unittest

from scripts import generate_permit_runtime_case_assertions


def _compressed_html(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    return (
        '<div id="proofClaimBox"></div>'
        '<script>'
        'const renderProofClaim = (industry) => { return industry.claim_packet_summary; };'
        'const permitDataUrl = "";'
        'const inlineBootstrap = {};'
        f'const inlineBootstrapCompressed = "{encoded}";'
        'const marker = "법령군 증빙";'
        "</script>"
    )


class GeneratePermitRuntimeCaseAssertionsTests(unittest.TestCase):
    def test_build_runtime_case_assertions_validates_goldset_against_runtime_bootstrap(self):
        master_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2 건설업 등록기준",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "capital_eok": 5.0,
                        "technical_personnel_required": True,
                        "technicians_required": 5,
                        "equipment_count_required": 1,
                        "deposit_days_required": 30,
                    },
                    "raw_source_proof": {
                        "official_snapshot_note": "law.go.kr curated snapshot",
                        "source_checksum": "checksum-a",
                        "source_urls": ["https://www.law.go.kr/법령/건설산업기본법시행령/별표2"],
                    },
                    "claim_packet_summary": {
                        "family_key": "건설산업기본법 시행령",
                        "claim_id": "permit-family-aaa111",
                        "proof_coverage_ratio": "1/1",
                        "checksum_samples": ["checksum-a"],
                        "official_snapshot_note": "law.go.kr curated snapshot",
                    },
                }
            ]
        }
        goldset = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_id": "permit-family-aaa111",
                    "row_total": 1,
                    "cases": [
                        {
                            "case_id": "permit-family-aaa111:boundary_pass:FOCUS::construction-general-geonchuk",
                            "case_kind": "boundary_pass",
                            "family_key": "건설산업기본법 시행령",
                            "claim_id": "permit-family-aaa111",
                            "service_code": "FOCUS::construction-general-geonchuk",
                            "service_name": "건축공사업(종합)",
                            "inputs": {
                                "industry_selector": "FOCUS::construction-general-geonchuk",
                                "capital_eok": 5.0,
                                "technicians_count": 5,
                                "other_requirement_checklist": {"equipment": True},
                            },
                            "expected": {
                                "overall_status": "pass",
                                "capital_gap_eok": 0.0,
                                "technicians_gap": 0,
                                "proof_visible": True,
                                "claim_id_visible": True,
                                "snapshot_visible": True,
                                "checksum_sample_visible": True,
                                "proof_coverage_ratio": "1/1",
                            },
                        }
                    ],
                }
            ]
        }
        html = _compressed_html({"permitCatalog": {"industries": master_catalog["industries"]}})

        report = generate_permit_runtime_case_assertions.build_runtime_case_assertions(
            master_catalog=master_catalog,
            permit_family_case_goldset=goldset,
            runtime_html=html,
        )

        self.assertTrue(report["summary"]["runtime_proof_surface_ready"])
        self.assertTrue(report["summary"]["runtime_assertions_ready"])
        self.assertEqual(report["summary"]["family_total"], 1)
        self.assertEqual(report["summary"]["case_total"], 1)
        self.assertEqual(report["summary"]["asserted_case_total"], 1)
        self.assertEqual(report["summary"]["failed_case_total"], 0)
        family = report["families"][0]
        self.assertTrue(family["ok"])
        case = family["cases"][0]
        self.assertTrue(case["ok"])
        self.assertEqual(case["actual_status"], "pass")
        self.assertTrue(case["assertion_flags"]["claim_id_match"])
        self.assertTrue(case["assertion_flags"]["proof_coverage_ratio_match"])


if __name__ == "__main__":
    unittest.main()
