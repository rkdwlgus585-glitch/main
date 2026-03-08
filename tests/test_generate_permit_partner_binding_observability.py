import unittest

from scripts import generate_permit_partner_binding_observability


class GeneratePermitPartnerBindingObservabilityTests(unittest.TestCase):
    def test_build_observability_report_is_ready_when_widget_and_api_cover_all_families(self):
        report = generate_permit_partner_binding_observability.build_observability_report(
            operator_demo_packet={
                "summary": {"prompt_case_binding_total": 2},
                "families": [
                    {
                        "claim_id": "permit-family-a",
                        "family_key": "family-a",
                        "prompt_case_binding": {
                            "preset_id": "preset-a",
                            "service_code": "A001",
                            "expected_status": "shortfall",
                            "review_reason": "capital_shortfall_only",
                            "manual_review_expected": False,
                        },
                    },
                    {
                        "claim_id": "permit-family-b",
                        "family_key": "family-b",
                        "prompt_case_binding": {
                            "preset_id": "preset-b",
                            "service_code": "B001",
                            "expected_status": "review",
                            "review_reason": "other_requirement_documents_missing",
                            "manual_review_expected": True,
                        },
                    },
                ],
            },
            permit_partner_binding_parity_packet={
                "summary": {"packet_ready": True, "family_total": 2},
                "partner_surface": [
                    {
                        "claim_id": "permit-family-a",
                        "family_key": "family-a",
                        "binding_preset_id": "preset-a",
                        "service_code": "A001",
                        "expected_status": "shortfall",
                        "review_reason": "capital_shortfall_only",
                        "manual_review_expected": False,
                    },
                    {
                        "claim_id": "permit-family-b",
                        "family_key": "family-b",
                        "binding_preset_id": "preset-b",
                        "service_code": "B001",
                        "expected_status": "review",
                        "review_reason": "other_requirement_documents_missing",
                        "manual_review_expected": True,
                    },
                ],
            },
            widget_rental_catalog={
                "summary": {
                    "permit_partner_binding_surface_ready": True,
                },
                "packaging": {
                    "partner_rental": {
                        "permit_widget_feeds": {
                            "partner_demo_samples": [
                                {"claim_id": "permit-family-a", "binding_preset_id": "preset-a"},
                                {"claim_id": "permit-family-b", "binding_preset_id": "preset-b"},
                            ]
                        }
                    }
                },
            },
            api_contract_spec={
                "services": {
                    "permit": {
                        "response_contract": {
                            "catalog_contracts": {
                                "master_catalog": {
                                    "current_summary": {
                                        "partner_binding_surface_ready": True,
                                    },
                                    "proof_surface_examples": {
                                        "partner_demo_samples": [
                                            {"claim_id": "permit-family-a", "binding_preset_id": "preset-a"},
                                            {"claim_id": "permit-family-b", "binding_preset_id": "preset-b"},
                                        ]
                                    },
                                }
                            }
                        }
                    }
                }
            },
        )

        summary = report["summary"]
        self.assertTrue(summary["observability_ready"])
        self.assertEqual(summary["expected_family_total"], 2)
        self.assertEqual(summary["widget_binding_family_total"], 2)
        self.assertEqual(summary["api_binding_family_total"], 2)
        self.assertEqual(summary["widget_missing_family_total"], 0)
        self.assertEqual(summary["api_missing_family_total"], 0)
        self.assertEqual(report["widget_missing_preview"], [])
        self.assertEqual(report["api_missing_preview"], [])
        self.assertEqual(report["families"][0]["binding_preset_id"], "preset-a")
        self.assertEqual(report["families"][1]["binding_preset_id"], "preset-b")

        markdown = generate_permit_partner_binding_observability.render_markdown(report)
        self.assertIn("Permit Partner Binding Observability", markdown)
        self.assertIn("expected_family_total", markdown)

    def test_build_observability_report_exposes_missing_family_preview(self):
        report = generate_permit_partner_binding_observability.build_observability_report(
            operator_demo_packet={"summary": {"prompt_case_binding_total": 2}, "families": []},
            permit_partner_binding_parity_packet={
                "summary": {"packet_ready": True, "family_total": 2},
                "partner_surface": [
                    {
                        "claim_id": "permit-family-a",
                        "family_key": "family-a",
                        "binding_preset_id": "preset-a",
                        "service_code": "A001",
                    },
                    {
                        "claim_id": "permit-family-b",
                        "family_key": "family-b",
                        "binding_preset_id": "preset-b",
                        "service_code": "B001",
                    },
                ],
            },
            widget_rental_catalog={
                "summary": {"permit_partner_binding_surface_ready": True},
                "packaging": {
                    "partner_rental": {
                        "permit_widget_feeds": {
                            "partner_demo_samples": [
                                {"claim_id": "permit-family-a", "binding_preset_id": "preset-a"},
                            ]
                        }
                    }
                },
            },
            api_contract_spec={
                "services": {
                    "permit": {
                        "response_contract": {
                            "catalog_contracts": {
                                "master_catalog": {
                                    "current_summary": {"partner_binding_surface_ready": True},
                                    "proof_surface_examples": {
                                        "partner_demo_samples": [
                                            {"claim_id": "permit-family-a", "binding_preset_id": "preset-a"},
                                            {"claim_id": "permit-family-b", "binding_preset_id": "preset-b"},
                                        ]
                                    },
                                }
                            }
                        }
                    }
                }
            },
        )

        summary = report["summary"]
        self.assertFalse(summary["observability_ready"])
        self.assertEqual(summary["widget_missing_family_total"], 1)
        self.assertEqual(report["widget_missing_preview"][0]["claim_id"], "permit-family-b")


if __name__ == "__main__":
    unittest.main()
