import unittest

from scripts import generate_permit_provenance_audit


class GeneratePermitProvenanceAuditTests(unittest.TestCase):
    def test_build_audit_summarizes_focus_seed_and_candidate_pack_risk(self):
        payload = {
            "summary": {
                "master_industry_total": 3,
                "master_real_row_total": 3,
                "master_focus_registry_row_total": 0,
                "master_promoted_row_total": 0,
                "master_absorbed_row_total": 0,
                "master_real_with_alias_total": 1,
                "master_focus_row_total": 2,
                "master_inferred_overlay_total": 1,
            },
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "canonical_service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "catalog_source_kind": "focus_seed_catalog",
                    "catalog_source_label": "permit_focus_seed_catalog",
                    "criteria_source_type": "rule_pack",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2 건설업 등록기준",
                    "platform_has_focus_alias": True,
                    "raw_source_proof": {
                        "proof_status": "raw_source_hardened",
                        "source_checksum": "proof-1",
                        "source_urls": ["https://www.law.go.kr/법령/건설산업기본법시행령/별표2"],
                    },
                    "platform_selector_aliases": [
                        {"selector_code": "SEL::FOCUS::RULE::construction-general-geonchuk", "selector_kind": "focus"}
                    ],
                },
                {
                    "service_code": "A001",
                    "canonical_service_code": "A001",
                    "service_name": "제재업",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "criteria_source_type": "candidate_pack",
                    "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                    "legal_basis_title": "제31조(등록)",
                    "quality_flags": ["article_name_unmatched"],
                },
                {
                    "service_code": "A002",
                    "canonical_service_code": "A002",
                    "service_name": "테스트업",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "criteria_source_type": "article_body",
                    "law_title": "",
                    "legal_basis_title": "",
                    "platform_has_inferred_alias": True,
                    "platform_selector_aliases": [
                        {"selector_code": "SEL::INFERRED::A002", "selector_kind": "inferred"}
                    ],
                },
                {
                    "service_code": "FOCUS::security-machine",
                    "canonical_service_code": "FOCUS::security-machine",
                    "service_name": "기계경비업",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "catalog_source_kind": "focus_family_registry",
                    "criteria_source_type": "rule_pack",
                    "law_title": "경비업법 시행령",
                    "legal_basis_title": "별표 1 경비업 허가기준",
                },
            ],
        }

        audit = generate_permit_provenance_audit.build_audit(payload)

        self.assertEqual(audit["summary"]["master_promoted_row_total"], 0)
        self.assertEqual(audit["summary"]["master_focus_registry_row_total"], 0)
        self.assertEqual(audit["summary"]["master_absorbed_row_total"], 0)
        self.assertEqual(audit["summary"]["focus_seed_row_total"], 1)
        self.assertEqual(audit["summary"]["focus_family_registry_row_total"], 1)
        self.assertEqual(audit["summary"]["focus_seed_real_row_total"], 1)
        self.assertEqual(audit["summary"]["rows_with_raw_source_proof_total"], 1)
        self.assertEqual(audit["summary"]["focus_family_registry_with_raw_source_proof_total"], 0)
        self.assertEqual(audit["summary"]["focus_family_registry_missing_raw_source_proof_total"], 1)
        self.assertEqual(audit["summary"]["rows_with_quality_flags_total"], 1)
        self.assertEqual(audit["summary"]["rows_missing_legal_basis_total"], 1)
        self.assertEqual(audit["summary"]["candidate_pack_total"], 1)
        self.assertEqual(audit["summary"]["article_body_total"], 1)
        self.assertEqual(audit["summary"]["rule_pack_total"], 2)
        self.assertEqual(audit["criteria_source_breakdown"]["candidate_pack"], 1)
        self.assertEqual(audit["quality_flag_breakdown"]["article_name_unmatched"], 1)
        self.assertTrue(audit["next_actions"])
        self.assertEqual(
            audit["review_queues"]["focus_seed_rows"][0]["service_code"],
            "FOCUS::construction-general-geonchuk",
        )
        self.assertEqual(
            audit["review_queues"]["rows_missing_raw_source_proof"][0]["service_code"],
            "FOCUS::security-machine",
        )

        markdown = generate_permit_provenance_audit.render_markdown(audit)
        self.assertIn("focus_seed_row_total", markdown)
        self.assertIn("rows_with_raw_source_proof_total", markdown)
        self.assertIn("Focus Seed Rows", markdown)
        self.assertIn("Rows Missing Raw Source Proof", markdown)
        self.assertIn("FOCUS::construction-general-geonchuk", markdown)


if __name__ == "__main__":
    unittest.main()
