import unittest

from scripts import generate_permit_focus_priority_report


class GeneratePermitFocusPriorityReportTests(unittest.TestCase):
    def test_selector_entry_strips_focus_seed_prefix(self):
        entry = generate_permit_focus_priority_report._selector_entry(
            {"service_code": "FOCUS::construction-general-geonchuk"},
            "focus",
        )
        self.assertEqual(entry["selector_code"], "SEL::FOCUS::construction-general-geonchuk")

    def test_build_report_separates_high_confidence_and_inferred_rows(self):
        payload = {
            "generated_at": "2026-03-07T12:00:00",
            "summary": {
                "scope_industry_total": 4,
                "scope_real_industry_total": 3,
                "scope_rules_only_industry_total": 1,
            },
            "industries": [
                {
                    "service_code": "REAL001",
                    "service_name": "실업종A",
                    "major_name": "실업종",
                    "law_title": "테스트법",
                    "legal_basis_title": "제10조(등록)",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": True,
                        "focus_target_with_other": True,
                        "inferred_focus_candidate": False,
                        "capital_eok": 1.5,
                        "technicians_required": 2,
                        "other_components": ["office"],
                        "profile_source": "structured_requirements",
                        "focus_bucket": "capital_technical_other",
                    },
                },
                {
                    "service_code": "RULE::R1",
                    "service_name": "규칙업종A",
                    "major_name": "등록기준 업종군",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": True,
                        "focus_target_with_other": True,
                        "inferred_focus_candidate": False,
                        "capital_eok": 5.0,
                        "technicians_required": 5,
                        "other_components": ["equipment"],
                        "profile_source": "structured_requirements",
                        "focus_bucket": "capital_technical_other",
                    },
                },
                {
                    "service_code": "REAL003",
                    "service_name": "실업종C",
                    "major_name": "실업종",
                    "law_title": "테스트법",
                    "legal_basis_title": "제11조(등록)",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": True,
                        "focus_target_with_other": False,
                        "inferred_focus_candidate": False,
                        "capital_eok": 0.3,
                        "technicians_required": 1,
                        "other_components": [],
                        "profile_source": "structured_requirements",
                        "focus_bucket": "capital_technical",
                    },
                },
                {
                    "service_code": "REAL002",
                    "service_name": "실업종B",
                    "registration_requirement_profile": {
                        "capital_required": True,
                        "technical_personnel_required": True,
                        "focus_target": False,
                        "focus_target_with_other": False,
                        "inferred_focus_candidate": True,
                        "capital_eok": 0,
                        "technicians_required": 0,
                        "other_components": ["document"],
                        "profile_source": "text_inference",
                        "focus_bucket": "inferred_capital_technical_other",
                    },
                },
            ],
        }

        report = generate_permit_focus_priority_report.build_report(payload)

        self.assertEqual(report["summary"]["scope_industry_total"], 4)
        self.assertEqual(report["summary"]["scope_real_industry_total"], 3)
        self.assertEqual(report["summary"]["scope_rules_only_industry_total"], 1)
        self.assertEqual(report["summary"]["focus_target_total"], 3)
        self.assertEqual(report["summary"]["real_focus_target_total"], 2)
        self.assertEqual(report["summary"]["rules_only_focus_target_total"], 1)
        self.assertEqual(report["summary"]["selector_ready_focus_total"], 3)
        self.assertEqual(report["summary"]["focus_target_with_other_total"], 2)
        self.assertEqual(report["summary"]["focus_core_only_total"], 1)
        self.assertEqual(report["summary"]["high_confidence_focus_total"], 3)
        self.assertEqual(report["summary"]["real_high_confidence_focus_total"], 2)
        self.assertEqual(report["summary"]["rules_only_high_confidence_focus_total"], 1)
        self.assertEqual(report["summary"]["inferred_focus_total"], 1)
        self.assertEqual(report["summary"]["selector_ready_inferred_total"], 1)
        self.assertEqual(report["focus_target_rows"][0]["service_code"], "REAL001")
        self.assertEqual(report["focus_target_rows"][0]["selector_code"], "SEL::FOCUS::REAL001")
        self.assertEqual(report["focus_target_rows"][1]["selector_code"], "SEL::FOCUS::REAL003")
        self.assertEqual(report["focus_target_rows"][2]["selector_code"], "SEL::FOCUS::RULE::R1")
        self.assertEqual(report["focus_target_with_other_rows"][1]["selector_code"], "SEL::FOCUS::RULE::R1")
        self.assertEqual(report["focus_core_only_rows"][0]["service_code"], "REAL003")
        self.assertEqual(report["inferred_focus_candidates"][0]["service_code"], "REAL002")
        self.assertEqual(report["inferred_focus_candidates"][0]["selector_code"], "SEL::INFERRED::REAL002")
        self.assertTrue(report["priority_actions"])

        markdown = generate_permit_focus_priority_report.render_markdown(report)
        self.assertIn("focus_target_total", markdown)
        self.assertIn("Capital + Technical + Other", markdown)
        self.assertIn("SEL::FOCUS::REAL001", markdown)
        self.assertIn("SEL::INFERRED::REAL002", markdown)


if __name__ == "__main__":
    unittest.main()
