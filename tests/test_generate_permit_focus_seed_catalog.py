import unittest

from scripts import generate_permit_focus_seed_catalog


class GeneratePermitFocusSeedCatalogTests(unittest.TestCase):
    def test_build_focus_seed_catalog_materializes_rule_only_focus_rows(self):
        base_catalog = {
            "summary": {},
            "major_categories": [],
            "industries": [],
        }
        rule_catalog = {
            "version": "1",
            "effective_date": "2026-03-08",
            "source": {},
            "rule_groups": [
                {
                    "rule_id": "construction-general-geonchuk",
                    "industry_name": "건축공사업(종합)",
                    "legal_basis": [
                        {
                            "law_title": "건설산업기본법 시행령",
                            "article": "별표 2 건설업 등록기준",
                            "url": "https://www.law.go.kr/법령/건설산업기본법시행령",
                        }
                    ],
                    "requirements": {
                        "capital_eok": 5.0,
                        "technicians": 5,
                        "equipment_count": 0,
                        "deposit_days": 0,
                    },
                    "typed_criteria": [
                        {
                            "criterion_id": "capital.minimum",
                            "label": "자본금",
                            "input_key": "capital_eok",
                            "value_type": "number",
                            "operator": ">=",
                            "required_value": 5.0,
                            "blocking": True,
                        }
                    ],
                }
            ],
        }

        payload = generate_permit_focus_seed_catalog.build_focus_seed_catalog(base_catalog, rule_catalog)

        self.assertEqual(payload["summary"]["seed_industry_total"], 1)
        self.assertEqual(payload["summary"]["seed_focus_rules_only_total"], 1)
        self.assertEqual(payload["major_categories"][0]["major_name"], "건설")
        row = payload["industries"][0]
        self.assertEqual(row["service_code"], "FOCUS::construction-general-geonchuk")
        self.assertEqual(row["seed_rule_service_code"], "RULE::construction-general-geonchuk")
        self.assertEqual(row["catalog_source_kind"], "focus_seed_catalog")
        self.assertEqual(row["group_name"], "건설업 등록기준")
        self.assertEqual(row["law_title"], "건설산업기본법 시행령")
        self.assertEqual(row["registration_requirement_profile"]["focus_target"], True)
        self.assertEqual(row["registration_requirement_profile"]["focus_target_with_other"], True)

        markdown = generate_permit_focus_seed_catalog.render_markdown(payload)
        self.assertIn("Permit Focus Seed Catalog", markdown)
        self.assertIn("FOCUS::construction-general-geonchuk", markdown)


if __name__ == "__main__":
    unittest.main()
