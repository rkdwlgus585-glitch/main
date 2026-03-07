import unittest

from scripts import generate_permit_source_upgrade_backlog


class GeneratePermitSourceUpgradeBacklogTests(unittest.TestCase):
    def test_build_backlog_groups_focus_seed_candidate_and_inferred_tracks(self):
        master_catalog = {
            "summary": {
                "master_industry_total": 4,
                "master_absorbed_row_total": 0,
            },
            "industries": [
                {
                    "service_code": "FOCUS::construction-general-geonchuk",
                    "canonical_service_code": "FOCUS::construction-general-geonchuk",
                    "service_name": "건축공사업(종합)",
                    "major_name": "건설",
                    "group_name": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2",
                    "criteria_source_type": "rule_pack",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "catalog_source_kind": "focus_seed_catalog",
                },
                {
                    "service_code": "FOCUS::construction-general-tomok",
                    "canonical_service_code": "FOCUS::construction-general-tomok",
                    "service_name": "토목공사업(종합)",
                    "major_name": "건설",
                    "group_name": "건설업 등록기준",
                    "law_title": "건설산업기본법 시행령",
                    "legal_basis_title": "별표 2",
                    "criteria_source_type": "rule_pack",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "catalog_source_kind": "focus_seed_catalog",
                },
                {
                    "service_code": "A001",
                    "canonical_service_code": "A001",
                    "service_name": "제재업",
                    "major_name": "임업",
                    "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                    "legal_basis_title": "제31조(등록)",
                    "criteria_source_type": "candidate_pack",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                },
                {
                    "service_code": "A002",
                    "canonical_service_code": "A002",
                    "service_name": "테스트업",
                    "major_name": "유통",
                    "law_title": "전자상거래법",
                    "legal_basis_title": "제12조(신고)",
                    "criteria_source_type": "candidate_pack",
                    "platform_row_origin": "real_catalog",
                    "master_row_origin": "real_catalog",
                    "platform_has_inferred_alias": True,
                },
            ],
        }
        provenance_audit = {
            "summary": {
                "focus_seed_row_total": 2,
                "candidate_pack_total": 2,
                "master_absorbed_row_total": 0,
            }
        }

        backlog = generate_permit_source_upgrade_backlog.build_backlog(master_catalog, provenance_audit)

        self.assertEqual(backlog["summary"]["master_absorbed_row_total"], 0)
        self.assertEqual(backlog["summary"]["focus_family_registry_row_total"], 0)
        self.assertEqual(backlog["summary"]["focus_seed_row_total"], 2)
        self.assertEqual(backlog["summary"]["candidate_pack_total"], 2)
        self.assertEqual(backlog["summary"]["inferred_reverification_total"], 1)
        self.assertEqual(backlog["summary"]["focus_seed_group_total"], 1)
        self.assertEqual(backlog["summary"]["candidate_pack_group_total"], 2)
        self.assertTrue(backlog["next_actions"])
        self.assertEqual(
            backlog["upgrade_tracks"]["focus_seed_source_groups"][0]["group_key"],
            "건설산업기본법 시행령",
        )
        self.assertEqual(
            backlog["upgrade_tracks"]["inferred_reverification_rows"][0]["service_code"],
            "A002",
        )

        markdown = generate_permit_source_upgrade_backlog.render_markdown(backlog)
        self.assertIn("focus_seed_row_total", markdown)
        self.assertIn("Focus Seed Source Groups", markdown)
        self.assertIn("건설산업기본법 시행령", markdown)


if __name__ == "__main__":
    unittest.main()
