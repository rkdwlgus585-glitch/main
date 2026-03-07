import unittest

from scripts import generate_permit_master_catalog


class GeneratePermitMasterCatalogTests(unittest.TestCase):
    def test_build_master_artifact_preserves_feed_contract_and_rows(self):
        bootstrap_payload = {
            "permitCatalog": {
                "master_catalog": {
                    "summary": {
                        "master_industry_total": 2,
                        "master_real_row_total": 1,
                        "master_focus_registry_row_total": 1,
                        "master_promoted_row_total": 0,
                        "master_absorbed_row_total": 0,
                        "master_real_with_alias_total": 1,
                        "master_focus_row_total": 1,
                        "master_inferred_overlay_total": 1,
                        "master_selector_alias_total": 2,
                        "master_canonicalized_promoted_total": 0,
                    },
                    "feed_contract": {
                        "primary_feed_name": "master_catalog",
                        "overlay_feed_name": "selector_catalog",
                        "primary_row_key": "service_code",
                        "canonical_row_key": "canonical_service_code",
                        "focus_registry_row_key_policy": "focus_registry_source rows use canonical_service_code as primary service_code",
                        "absorbed_row_key_policy": "focus_source_absorbed rows use canonical_service_code as primary service_code",
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
                            "master_row_origin": "real_catalog",
                            "platform_selector_aliases": [
                                {"selector_code": "SEL::INFERRED::A001"},
                            ],
                            "law_title": "전자상거래법",
                            "legal_basis_title": "제12조(신고)",
                        },
                        {
                            "service_code": "RULE::R1",
                            "canonical_service_code": "RULE::R1",
                            "service_name": "건축공사업(종합)",
                            "platform_row_origin": "focus_registry_source",
                            "master_row_origin": "focus_registry_source",
                            "platform_selector_aliases": [
                                {"selector_code": "SEL::FOCUS::RULE::R1"},
                            ],
                            "law_title": "건설산업기본법 시행령",
                            "legal_basis_title": "별표 2",
                        },
                    ],
                }
            }
        }

        artifact = generate_permit_master_catalog.build_master_artifact(bootstrap_payload)

        self.assertEqual(artifact["summary"]["master_industry_total"], 2)
        self.assertEqual(artifact["summary"]["master_promoted_row_total"], 0)
        self.assertEqual(artifact["summary"]["master_focus_registry_row_total"], 1)
        self.assertEqual(artifact["summary"]["master_absorbed_row_total"], 0)
        self.assertEqual(artifact["summary"]["master_canonicalized_promoted_total"], 0)
        self.assertEqual(artifact["feed_contract"]["primary_feed_name"], "master_catalog")
        self.assertEqual(
            artifact["feed_contract"]["focus_registry_row_key_policy"],
            "focus_registry_source rows use canonical_service_code as primary service_code",
        )
        self.assertEqual(
            artifact["feed_contract"]["absorbed_row_key_policy"],
            "focus_source_absorbed rows use canonical_service_code as primary service_code",
        )
        self.assertEqual(artifact["industries"][0]["service_code"], "A001")
        self.assertEqual(artifact["industries"][1]["service_code"], "RULE::R1")
        self.assertEqual(artifact["industries"][1]["master_row_origin"], "focus_registry_source")

        markdown = generate_permit_master_catalog.render_markdown(artifact)
        self.assertIn("master_industry_total", markdown)
        self.assertIn("master_catalog", markdown)
        self.assertIn("SEL::FOCUS::RULE::R1", markdown)
        self.assertIn("focus_registry_row_key_policy", markdown)
        self.assertIn("absorbed_row_key_policy", markdown)


if __name__ == "__main__":
    unittest.main()
