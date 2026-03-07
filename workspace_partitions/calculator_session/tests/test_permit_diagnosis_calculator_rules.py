import unittest

import permit_diagnosis_calculator


class PermitDiagnosisCalculatorRulesTest(unittest.TestCase):
    def test_rule_catalog_only_accepts_objective_legal_sources(self):
        rule_catalog = permit_diagnosis_calculator._load_rule_catalog(
            permit_diagnosis_calculator.DEFAULT_RULES_PATH
        )
        index = permit_diagnosis_calculator._build_rule_index(rule_catalog)
        self.assertGreaterEqual(len(index["rules"]), 20)
        for rule in index["rules"]:
            legal_basis = list(rule.get("legal_basis") or [])
            self.assertTrue(legal_basis)
            for basis in legal_basis:
                self.assertTrue(
                    permit_diagnosis_calculator._is_objective_source_url(str(basis.get("url", "") or ""))
                )

    def test_evaluate_registration_diagnosis_boundary_inputs(self):
        rule = {
            "industry_name": "테스트업",
            "requirements": {
                "capital_eok": 1.5,
                "technicians": 2,
                "equipment_count": 1,
                "deposit_days": 10,
            },
            "legal_basis": [{"law_title": "테스트법", "article": "별표 1", "url": "https://www.law.go.kr"}],
        }
        low = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=-5,
            current_technicians=-2,
            current_equipment_count=-1,
            raw_capital_input="-5",
        )
        self.assertEqual(low["capital"]["current"], 0)
        self.assertEqual(low["technicians"]["current"], 0)
        self.assertEqual(low["equipment"]["current"], 0)
        self.assertFalse(low["overall_ok"])
        self.assertEqual(low["capital"]["gap"], 1.5)
        self.assertEqual(low["technicians"]["gap"], 2)
        self.assertEqual(low["equipment"]["gap"], 1)

        ok = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=1.5,
            current_technicians=2,
            current_equipment_count=1,
            raw_capital_input="1.5",
        )
        self.assertTrue(ok["overall_ok"])
        self.assertEqual(ok["capital"]["gap"], 0)
        self.assertEqual(ok["technicians"]["gap"], 0)
        self.assertEqual(ok["equipment"]["gap"], 0)

        suspicious = permit_diagnosis_calculator.evaluate_registration_diagnosis(
            rule=rule,
            current_capital_eok=120,
            current_technicians=2,
            current_equipment_count=1,
            raw_capital_input="120",
        )
        self.assertTrue(suspicious["capital_input_suspicious"])

    def test_prepare_ui_payload_includes_rules_only_category(self):
        payload = permit_diagnosis_calculator._prepare_ui_payload(
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                permit_diagnosis_calculator.DEFAULT_RULES_PATH
            ),
        )
        major_codes = {row.get("major_code") for row in payload.get("major_categories", [])}
        self.assertIn(permit_diagnosis_calculator.RULES_ONLY_CATEGORY_CODE, major_codes)
        self.assertGreater(payload.get("summary", {}).get("industry_total", 0), 0)
        self.assertGreater(payload.get("summary", {}).get("with_registration_rule_total", 0), 0)

    def test_build_html_contains_expanded_input_fields(self):
        html = permit_diagnosis_calculator.build_html(
            title="AI 인허가 사전검토 진단기(신규등록)",
            catalog=permit_diagnosis_calculator._blank_catalog(),
            rule_catalog=permit_diagnosis_calculator._load_rule_catalog(
                permit_diagnosis_calculator.DEFAULT_RULES_PATH
            ),
        )
        self.assertIn('id="categorySelect"', html)
        self.assertIn('id="industrySelect"', html)
        self.assertIn('id="capitalInput"', html)
        self.assertIn('id="technicianInput"', html)
        self.assertIn('id="equipmentInput"', html)
        self.assertIn('id="legalBasis"', html)
        self.assertIn("const permitCatalog", html)
        self.assertIn("const ruleLookup", html)


if __name__ == "__main__":
    unittest.main()
