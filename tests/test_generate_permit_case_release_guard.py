import unittest

from scripts import generate_permit_case_release_guard


class GeneratePermitCaseReleaseGuardTests(unittest.TestCase):
    def test_build_release_guard_passes_when_runtime_widget_and_api_match_goldset(self):
        goldset = {
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "cases": [
                        {"case_id": "case-1"},
                        {"case_id": "case-2"},
                    ],
                }
            ]
        }
        runtime_assertions = {
            "summary": {"runtime_assertions_ready": True},
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "cases": [
                        {"case_id": "case-1", "ok": True},
                        {"case_id": "case-2", "ok": True},
                    ],
                }
            ],
        }
        widget_catalog = {
            "packaging": {
                "partner_rental": {
                    "permit_widget_feeds": {
                        "family_case_samples": [
                            {"family_key": "건설산업기본법 시행령", "case_id": "case-1"},
                            {"family_key": "건설산업기본법 시행령", "case_id": "case-2"},
                        ]
                    }
                }
            }
        }
        api_contract = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "proof_surface_examples": {
                                    "family_case_samples": [
                                        {"family_key": "건설산업기본법 시행령", "case_id": "case-1"},
                                        {"family_key": "건설산업기본법 시행령", "case_id": "case-2"},
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }

        report = generate_permit_case_release_guard.build_release_guard(
            permit_family_case_goldset=goldset,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract,
        )

        self.assertTrue(report["summary"]["release_guard_ready"])
        self.assertEqual(report["summary"]["runtime_missing_case_total"], 0)
        self.assertEqual(report["summary"]["widget_missing_case_total"], 0)
        self.assertEqual(report["summary"]["api_missing_case_total"], 0)
        self.assertEqual(report["summary"]["family_total"], 1)
        self.assertEqual(report["summary"]["case_total"], 2)

    def test_build_release_guard_fails_when_widget_case_is_missing(self):
        goldset = {
            "families": [
                {
                    "family_key": "전기공사업법 시행령",
                    "cases": [
                        {"case_id": "case-1"},
                        {"case_id": "case-2"},
                    ],
                }
            ]
        }
        runtime_assertions = {
            "summary": {"runtime_assertions_ready": True},
            "families": [
                {
                    "family_key": "전기공사업법 시행령",
                    "cases": [
                        {"case_id": "case-1", "ok": True},
                        {"case_id": "case-2", "ok": True},
                    ],
                }
            ],
        }
        widget_catalog = {
            "packaging": {
                "partner_rental": {
                    "permit_widget_feeds": {
                        "family_case_samples": [
                            {"family_key": "전기공사업법 시행령", "case_id": "case-1"},
                        ]
                    }
                }
            }
        }
        api_contract = {
            "services": {
                "permit": {
                    "response_contract": {
                        "catalog_contracts": {
                            "master_catalog": {
                                "proof_surface_examples": {
                                    "family_case_samples": [
                                        {"family_key": "전기공사업법 시행령", "case_id": "case-1"},
                                        {"family_key": "전기공사업법 시행령", "case_id": "case-2"},
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }

        report = generate_permit_case_release_guard.build_release_guard(
            permit_family_case_goldset=goldset,
            permit_runtime_case_assertions=runtime_assertions,
            widget_rental_catalog=widget_catalog,
            api_contract_spec=api_contract,
        )

        self.assertFalse(report["summary"]["release_guard_ready"])
        self.assertEqual(report["summary"]["widget_missing_case_total"], 1)
        self.assertEqual(report["missing"]["widget_cases"], ["case-2"])


if __name__ == "__main__":
    unittest.main()
