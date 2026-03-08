import unittest

from scripts import generate_permit_patent_evidence_bundle


class GeneratePermitPatentEvidenceBundleTests(unittest.TestCase):
    def test_build_bundle_groups_focus_seed_families_and_builds_claim_packets(self):
        focus_seed_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "group_name": "건설업 등록기준",
                    "seed_law_family": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "registration_requirement_profile": {
                        "capital_eok": 5.0,
                        "technicians_required": 5,
                    },
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "service_name": "토목공사업(종합)",
                    "group_name": "건설업 등록기준",
                    "seed_law_family": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "registration_requirement_profile": {
                        "capital_eok": 5.0,
                        "technicians_required": 6,
                    },
                },
                {
                    "service_code": "FOCUS::electrical-construction",
                    "service_name": "전기공사업",
                    "group_name": "전기공사업 등록기준",
                    "seed_law_family": "전기공사업 등록기준",
                    "law_title": "전기공사업법 시행령",
                    "registration_requirement_profile": {
                        "capital_eok": 1.5,
                        "technicians_required": 3,
                    },
                },
            ]
        }
        focus_family_registry = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "group_name": "건설업 등록기준",
                    "seed_law_family": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "registration_requirement_profile": {
                        "capital_eok": 5.0,
                        "technicians_required": 5,
                    },
                    "raw_source_proof": {
                        "proof_status": "raw_source_hardened",
                        "source_checksum": "abc123",
                        "source_urls": ["https://www.law.go.kr/법령/건설산업기본법시행령/별표2"],
                    },
                }
            ]
        }
        master_catalog = {
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "platform_selector_aliases": [{"selector_code": "SEL::FOCUS::construction-general-geonchuk"}],
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "platform_selector_aliases": [{"selector_code": "SEL::FOCUS::construction-general-tomok"}],
                },
                {
                    "service_code": "FOCUS::electrical-construction",
                    "platform_selector_aliases": [{"selector_code": "SEL::FOCUS::electrical-construction"}],
                },
            ]
        }
        focus_report = {
            "summary": {
                "real_focus_target_total": 3,
                "focus_core_only_total": 1,
            }
        }
        bundle = generate_permit_patent_evidence_bundle.build_bundle(
            focus_seed_catalog=focus_seed_catalog,
            focus_family_registry=focus_family_registry,
            master_catalog=master_catalog,
            focus_report=focus_report,
        )

        self.assertEqual(bundle["summary"]["focus_source_row_total"], 3)
        self.assertEqual(bundle["summary"]["focus_source_family_total"], 2)
        self.assertEqual(bundle["summary"]["focus_seed_row_total"], 3)
        self.assertEqual(bundle["summary"]["focus_family_registry_row_total"], 1)
        self.assertEqual(bundle["summary"]["focus_seed_family_total"], 2)
        self.assertEqual(bundle["summary"]["real_focus_target_total"], 3)
        self.assertEqual(bundle["summary"]["focus_core_only_total"], 1)
        self.assertEqual(bundle["summary"]["raw_source_proof_row_total"], 1)
        self.assertEqual(bundle["summary"]["raw_source_proof_family_total"], 0)
        self.assertEqual(bundle["summary"]["claim_packet_family_total"], 2)
        self.assertEqual(bundle["summary"]["claim_packet_complete_family_total"], 0)
        self.assertEqual(bundle["summary"]["checksum_sample_family_total"], 1)
        self.assertEqual(bundle["summary"]["execution_lane_id"], "patent_evidence_bundle_lock")
        self.assertEqual(bundle["summary"]["parallel_lane_id"], "platform_contract_proof_surface")
        self.assertEqual(bundle["families"][0]["family_key"], "건설산업기본법 시행령")
        self.assertEqual(bundle["families"][0]["row_total"], 2)
        self.assertEqual(bundle["families"][0]["selector_alias_total"], 2)
        self.assertEqual(bundle["families"][0]["raw_source_proof_row_total"], 1)
        self.assertEqual(bundle["families"][0]["raw_source_proof_url_total"], 1)
        self.assertIn(
            "SEL::FOCUS::construction-general-geonchuk",
            bundle["families"][0]["sample_selector_codes"],
        )
        claim_packet = bundle["families"][0]["claim_packet"]
        self.assertTrue(claim_packet["claim_id"].startswith("permit-family-"))
        self.assertIn("capital_eok", claim_packet["covered_input_domains"])
        self.assertIn("technicians_count", claim_packet["covered_input_domains"])
        self.assertEqual(claim_packet["optional_input_domains"], [])
        self.assertEqual(claim_packet["source_proof_summary"]["proof_coverage_ratio"], "1/2")
        self.assertFalse(bundle["families"][0]["claim_packet_complete"])

        markdown = generate_permit_patent_evidence_bundle.render_markdown(bundle)
        self.assertIn("Permit Patent Evidence Bundle", markdown)
        self.assertIn("patent_evidence_bundle_lock", markdown)
        self.assertIn("focus_source_row_total", markdown)
        self.assertIn("raw_source_proof_row_total", markdown)
        self.assertIn("claim_packet_family_total", markdown)
        self.assertIn("claim_statement:", markdown)
        self.assertIn("건설산업기본법 시행령", markdown)

    def test_build_bundle_adds_manual_rule_group_fallback_for_real_focus_row(self):
        bundle = generate_permit_patent_evidence_bundle.build_bundle(
            focus_seed_catalog={"industries": []},
            focus_family_registry={"industries": []},
            master_catalog={
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
                        },
                        "platform_selector_aliases": [
                            {"selector_code": "SEL::FOCUS::09_27_03_P"}
                        ],
                    }
                ]
            },
            focus_report={"summary": {"real_focus_target_total": 1, "focus_core_only_total": 1}},
            focus_scope_overrides={
                "manual_rule_groups": [
                    {
                        "industry_name": "제재업",
                        "service_codes": ["09_27_03_P"],
                        "legal_basis": [
                            {
                                "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                                "article": "목재생산업의 종류별 등록기준(제24조제1항 관련)",
                                "url": "https://www.law.go.kr/법령/목재의지속가능한이용에관한법률시행령",
                            }
                        ],
                    }
                ]
            },
        )

        self.assertEqual(bundle["summary"]["focus_source_row_total"], 1)
        self.assertEqual(bundle["summary"]["focus_source_family_total"], 1)
        self.assertEqual(bundle["summary"]["raw_source_proof_row_total"], 1)
        self.assertEqual(bundle["summary"]["raw_source_proof_family_total"], 1)
        self.assertEqual(bundle["summary"]["claim_packet_complete_family_total"], 1)
        family = bundle["families"][0]
        self.assertEqual(family["family_key"], "목재의 지속가능한 이용에 관한 법률 시행령")
        self.assertEqual(family["sample_service_codes"], ["09_27_03_P"])
        self.assertEqual(family["raw_source_proof_row_total"], 1)
        self.assertTrue(family["claim_packet_complete"])
        self.assertEqual(
            family["claim_packet"]["source_proof_summary"]["proof_coverage_ratio"],
            "1/1",
        )
        self.assertEqual(
            family["claim_packet"]["official_snapshot_note"],
            "목재의 지속가능한 이용에 관한 법률 시행령 / 목재생산업의 종류별 등록기준(제24조제1항 관련) 기준으로 제재업 row를 manual rule group fallback source로 고정",
        )


if __name__ == "__main__":
    unittest.main()
