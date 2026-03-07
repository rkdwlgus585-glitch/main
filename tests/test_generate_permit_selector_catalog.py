import unittest

from scripts import generate_permit_selector_catalog


class GeneratePermitSelectorCatalogTests(unittest.TestCase):
    def test_build_selector_artifact_groups_focus_and_inferred_rows(self):
        bootstrap_payload = {
            "permitCatalog": {
                "summary": {
                    "real_focus_target_total": 1,
                    "rules_only_focus_target_total": 1,
                    "real_focus_target_with_other_total": 0,
                    "rules_only_focus_target_with_other_total": 1,
                    "focus_selector_entry_total": 2,
                    "inferred_selector_entry_total": 1,
                },
                "selector_catalog": {
                    "major_categories": [
                        {"major_code": "SEL-FOCUS", "major_name": "핵심 업종군", "industry_count": 2},
                        {"major_code": "SEL-INFERRED", "major_name": "추론 점검군", "industry_count": 1},
                    ],
                    "summary": {
                        "selector_category_total": 2,
                        "selector_entry_total": 3,
                        "selector_focus_total": 2,
                        "selector_inferred_total": 1,
                        "selector_real_entry_total": 1,
                        "selector_rules_only_entry_total": 2,
                    },
                    "industries": [
                        {
                            "service_code": "SEL::FOCUS::A001",
                            "canonical_service_code": "A001",
                            "service_name": "제재업",
                            "selector_kind": "focus",
                            "major_code": "SEL-FOCUS",
                            "major_name": "핵심 업종군",
                            "selector_category_code": "SEL-FOCUS",
                            "selector_category_name": "핵심 업종군",
                            "is_rules_only": False,
                            "law_title": "목재의 지속가능한 이용에 관한 법률 시행령",
                            "legal_basis_title": "목재생산업의 종류별 등록기준",
                        },
                        {
                            "service_code": "SEL::FOCUS::RULE::R1",
                            "canonical_service_code": "RULE::R1",
                            "service_name": "건축공사업(종합)",
                            "selector_kind": "focus",
                            "major_code": "SEL-FOCUS",
                            "major_name": "핵심 업종군",
                            "selector_category_code": "SEL-FOCUS",
                            "selector_category_name": "핵심 업종군",
                            "is_rules_only": True,
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                        },
                        {
                            "service_code": "SEL::INFERRED::A001",
                            "canonical_service_code": "A001",
                            "service_name": "통신판매업",
                            "selector_kind": "inferred",
                            "major_code": "SEL-INFERRED",
                            "major_name": "추론 점검군",
                            "selector_category_code": "SEL-INFERRED",
                            "selector_category_name": "추론 점검군",
                            "is_rules_only": True,
                        },
                    ],
                },
            }
        }

        artifact = generate_permit_selector_catalog.build_selector_artifact(bootstrap_payload)

        self.assertEqual(artifact["summary"]["selector_entry_total"], 3)
        self.assertEqual(artifact["summary"]["selector_focus_total"], 2)
        self.assertEqual(artifact["summary"]["selector_inferred_total"], 1)
        self.assertEqual(artifact["summary"]["real_focus_target_total"], 1)
        self.assertEqual(artifact["summary"]["rules_only_focus_target_total"], 1)
        self.assertEqual(artifact["summary"]["real_focus_target_with_other_total"], 0)
        self.assertEqual(artifact["summary"]["rules_only_focus_target_with_other_total"], 1)
        self.assertEqual(artifact["focus_selector_rows"][0]["service_code"], "SEL::FOCUS::A001")
        self.assertEqual(artifact["focus_selector_rows"][1]["canonical_service_code"], "RULE::R1")
        self.assertEqual(artifact["inferred_selector_rows"][0]["service_code"], "SEL::INFERRED::A001")

        markdown = generate_permit_selector_catalog.render_markdown(artifact)
        self.assertIn("selector_entry_total", markdown)
        self.assertIn("real_focus_target_total", markdown)
        self.assertIn("SEL::FOCUS::RULE::R1", markdown)
        self.assertIn("SEL::INFERRED::A001", markdown)


if __name__ == "__main__":
    unittest.main()
