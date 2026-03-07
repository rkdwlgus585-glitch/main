import unittest

from scripts import generate_permit_platform_catalog


class GeneratePermitPlatformCatalogTests(unittest.TestCase):
    def test_build_platform_artifact_preserves_promoted_and_real_alias_rows(self):
        bootstrap_payload = {
            "permitCatalog": {
                "platform_catalog": {
                    "summary": {
                        "platform_category_total": 2,
                        "platform_industry_total": 2,
                        "platform_real_row_total": 1,
                        "platform_focus_registry_row_total": 1,
                        "platform_promoted_selector_total": 0,
                        "platform_absorbed_focus_total": 0,
                        "platform_real_with_selector_alias_total": 1,
                        "platform_focus_registry_with_alias_total": 1,
                        "platform_focus_alias_total": 1,
                        "platform_inferred_alias_total": 1,
                        "platform_selector_alias_total": 2,
                    },
                    "major_categories": [
                        {"major_code": "09", "major_name": "유통", "industry_count": 1},
                        {"major_code": "SEL-FOCUS", "major_name": "핵심 업종군", "industry_count": 1},
                    ],
                    "industries": [
                        {
                            "service_code": "A001",
                            "canonical_service_code": "A001",
                            "service_name": "통신판매업",
                            "platform_row_origin": "real_catalog",
                            "platform_selector_aliases": [
                                {
                                    "selector_code": "SEL::INFERRED::A001",
                                    "selector_kind": "inferred",
                                    "selector_category_code": "SEL-INFERRED",
                                    "selector_category_name": "추론 점검군",
                                }
                            ],
                            "law_title": "전자상거래법",
                            "legal_basis_title": "제12조(신고)",
                        },
                        {
                            "service_code": "RULE::R1",
                            "canonical_service_code": "RULE::R1",
                            "service_name": "건축공사업(종합)",
                            "platform_row_origin": "focus_registry_source",
                            "platform_selector_aliases": [
                                {
                                    "selector_code": "SEL::FOCUS::RULE::R1",
                                    "selector_kind": "focus",
                                    "selector_category_code": "SEL-FOCUS",
                                    "selector_category_name": "핵심 업종군",
                                }
                            ],
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                        },
                    ],
                }
            }
        }

        artifact = generate_permit_platform_catalog.build_platform_artifact(bootstrap_payload)

        self.assertEqual(artifact["summary"]["platform_industry_total"], 2)
        self.assertEqual(artifact["summary"]["platform_promoted_selector_total"], 0)
        self.assertEqual(artifact["summary"]["platform_focus_registry_row_total"], 1)
        self.assertEqual(artifact["summary"]["platform_absorbed_focus_total"], 0)
        self.assertEqual(artifact["summary"]["platform_real_with_selector_alias_total"], 1)
        self.assertEqual(artifact["industries"][0]["service_code"], "A001")
        self.assertEqual(artifact["industries"][1]["service_code"], "RULE::R1")

        markdown = generate_permit_platform_catalog.render_markdown(artifact)
        self.assertIn("platform_industry_total", markdown)
        self.assertIn("SEL::INFERRED::A001", markdown)
        self.assertIn("platform_focus_registry_row_total", markdown)


if __name__ == "__main__":
    unittest.main()
