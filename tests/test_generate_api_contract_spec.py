import unittest

from scripts import generate_api_contract_spec


class GenerateApiContractSpecTests(unittest.TestCase):
    def test_build_contract_spec_includes_permit_catalog_contracts(self):
        registry = {
            "plan_feature_defaults": {
                "standard": ["estimate", "permit_precheck"],
                "pro": ["estimate_detail", "permit_precheck_detail"],
            },
            "offering_templates": [
                {
                    "offering_id": "permit_pro",
                    "display_name": "Permit Pro",
                    "plan": "pro",
                    "allowed_systems": ["permit"],
                    "allowed_features": ["permit_precheck_detail"],
                }
            ],
        }
        thresholds = {
            "plans": {
                "standard": {"included_tokens": 1000, "max_usage_events": 10},
                "pro": {"included_tokens": 5000, "max_usage_events": 50},
            }
        }
        selector_catalog = {
            "summary": {
                "selector_entry_total": 53,
                "selector_focus_total": 50,
                "selector_inferred_total": 3,
            }
        }
        platform_catalog = {
            "summary": {
                "platform_industry_total": 53,
                "platform_focus_registry_row_total": 50,
                "platform_promoted_selector_total": 0,
                "platform_absorbed_focus_total": 0,
                "platform_real_with_selector_alias_total": 3,
            }
        }
        master_catalog = {
            "summary": {
                "master_industry_total": 53,
                "master_real_row_total": 3,
                "master_focus_registry_row_total": 50,
                "master_promoted_row_total": 0,
                "master_absorbed_row_total": 0,
                "master_canonicalized_promoted_total": 0,
                "master_real_with_alias_total": 3,
                "master_focus_row_total": 50,
                "master_inferred_overlay_total": 3,
                "master_selector_alias_total": 53,
            }
        }
        permit_provenance = {
            "summary": {
                "rows_with_raw_source_proof_total": 50,
                "focus_family_registry_with_raw_source_proof_total": 50,
                "focus_family_registry_missing_raw_source_proof_total": 0,
            }
        }
        permit_patent = {
            "summary": {
                "raw_source_proof_family_total": 6,
                "claim_packet_family_total": 6,
                "claim_packet_complete_family_total": 6,
                "checksum_sample_family_total": 6,
            }
            ,
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_packet": {
                        "claim_id": "permit-family-aaa111",
                        "source_proof_summary": {
                            "checksum_samples": ["checksum-a"],
                        },
                    },
                }
            ],
        }
        permit_family_case_goldset = {
            "summary": {
                "goldset_complete_family_total": 1,
                "case_total": 2,
            },
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_id": "permit-family-aaa111",
                    "cases": [
                        {
                            "case_id": "permit-family-aaa111:boundary_pass:A001",
                            "case_kind": "boundary_pass",
                            "service_code": "A001",
                            "expected": {
                                "overall_status": "pass",
                                "proof_coverage_ratio": "1/1",
                                "review_reason": "",
                                "manual_review_expected": False,
                            },
                        },
                        {
                            "case_id": "permit-family-aaa111:shortfall_fail:A001",
                            "case_kind": "shortfall_fail",
                            "service_code": "A001",
                            "expected": {
                                "overall_status": "shortfall",
                                "proof_coverage_ratio": "1/1",
                                "review_reason": "technician_shortfall_only",
                                "manual_review_expected": False,
                            },
                        },
                    ],
                }
            ],
        }
        permit_case_story_surface = {
            "summary": {
                "story_family_total": 1,
                "review_reason_total": 1,
                "manual_review_family_total": 1,
                "story_ready": True,
            },
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_id": "permit-family-aaa111",
                    "preset_total": 3,
                    "manual_review_preset_total": 1,
                    "representative_cases": [
                        {
                            "preset_id": "permit-family-aaa111:document_missing_review:A001",
                            "review_reason": "other_requirement_documents_missing",
                        }
                    ],
                    "operator_story_points": ["서류 누락 시 수동 검토로 전환"],
                }
            ],
        }
        permit_operator_demo_packet = {
            "summary": {
                "operator_demo_ready": True,
                "family_total": 1,
                "demo_case_total": 2,
                "manual_review_demo_total": 1,
                "prompt_case_binding_total": 1,
            },
            "families": [
                {
                    "family_key": "건설산업기본법 시행령",
                    "claim_id": "permit-family-aaa111",
                    "claim_title": "건설업 등록기준 패킷",
                    "proof_coverage_ratio": "1/1",
                    "prompt_case_binding": {
                        "preset_id": "permit-family-aaa111:document_missing_review:A001",
                        "service_code": "A001",
                        "service_name": "build-demo-a",
                        "expected_status": "review",
                        "review_reason": "other_requirement_documents_missing",
                        "binding_focus": "manual_review_gate",
                        "binding_question": "서류 공백에서 자동판단을 멈췄는가.",
                        "manual_review_expected": True,
                    },
                    "demo_cases": [
                        {
                            "service_code": "A001",
                            "service_name": "건축공사업(종합)",
                            "expected_status": "pass",
                            "review_reason": "",
                            "manual_review_expected": False,
                        },
                        {
                            "service_code": "A001",
                            "service_name": "건축공사업(종합)",
                            "expected_status": "review",
                            "review_reason": "other_requirement_documents_missing",
                            "manual_review_expected": True,
                        },
                    ],
                }
            ],
        }

        spec = generate_api_contract_spec.build_contract_spec(
            registry,
            thresholds,
            permit_selector_catalog=selector_catalog,
            permit_platform_catalog=platform_catalog,
            permit_master_catalog=master_catalog,
            permit_provenance_audit=permit_provenance,
            permit_patent_evidence_bundle=permit_patent,
            permit_family_case_goldset=permit_family_case_goldset,
            permit_case_story_surface=permit_case_story_surface,
            permit_operator_demo_packet=permit_operator_demo_packet,
        )

        permit_service = spec["services"]["permit"]
        self.assertIn("selector_code", permit_service["request_contract"]["selector_fields"])
        self.assertIn("canonical_service_code", permit_service["request_contract"]["selector_fields"])
        catalog_contracts = permit_service["response_contract"]["catalog_contracts"]
        self.assertEqual(
            catalog_contracts["selector_catalog"]["current_summary"]["selector_entry_total"],
            53,
        )
        self.assertEqual(
            catalog_contracts["platform_catalog"]["current_summary"]["platform_industry_total"],
            53,
        )
        self.assertEqual(
            catalog_contracts["platform_catalog"]["current_summary"]["platform_focus_registry_row_total"],
            50,
        )
        self.assertEqual(
            catalog_contracts["platform_catalog"]["current_summary"]["platform_promoted_selector_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["platform_catalog"]["current_summary"]["platform_absorbed_focus_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["master_industry_total"],
            53,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["master_focus_registry_row_total"],
            50,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["master_promoted_row_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["master_absorbed_row_total"],
            0,
        )
        self.assertIn(
            "platform_selector_aliases",
            catalog_contracts["master_catalog"]["row_fields"],
        )
        self.assertIn(
            "focus_registry_row_key_policy",
            catalog_contracts["master_catalog"]["feed_contract_fields"],
        )
        self.assertIn(
            "absorbed_row_key_policy",
            catalog_contracts["master_catalog"]["feed_contract_fields"],
        )
        self.assertIn("raw_source_proof", catalog_contracts["master_catalog"]["row_fields"])
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["rows_with_raw_source_proof_total"],
            50,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["focus_family_registry_with_raw_source_proof_total"],
            50,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["focus_family_registry_missing_raw_source_proof_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["raw_source_proof_family_total"],
            6,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["claim_packet_family_total"],
            6,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["claim_packet_complete_family_total"],
            6,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["checksum_sample_family_total"],
            6,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["checksum_sample_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["family_case_goldset_family_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["family_case_total"],
            2,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["family_case_sample_total"],
            2,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["edge_case_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["edge_case_family_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["manual_review_case_total"],
            0,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["case_story_surface_family_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["case_story_review_reason_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["case_story_manual_review_family_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["case_story_sample_total"],
            1,
        )
        self.assertTrue(
            catalog_contracts["master_catalog"]["current_summary"]["case_story_surface_ready"]
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["partner_demo_family_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["partner_demo_case_total"],
            2,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["partner_demo_manual_review_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["partner_demo_sample_total"],
            1,
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["current_summary"]["partner_binding_sample_total"],
            1,
        )
        self.assertTrue(
            catalog_contracts["master_catalog"]["current_summary"]["partner_demo_surface_ready"]
        )
        self.assertTrue(
            catalog_contracts["master_catalog"]["current_summary"]["partner_binding_surface_ready"]
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["proof_surface_examples"]["family_checksum_samples"][0]["checksum"],
            "checksum-a",
        )
        self.assertIn(
            "claim_statement",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["claim_packet_fields"],
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["proof_surface_examples"]["family_case_samples"][0]["case_id"],
            "permit-family-aaa111:boundary_pass:A001",
        )
        self.assertIn(
            "expected_status",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["family_case_fields"],
        )
        self.assertIn(
            "review_reason",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["family_case_fields"],
        )
        self.assertIn(
            "manual_review_expected",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["family_case_fields"],
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["proof_surface_examples"]["case_story_samples"][0]["claim_id"],
            "permit-family-aaa111",
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["proof_surface_examples"]["case_story_samples"][0]["representative_preset_ids"],
            ["permit-family-aaa111:document_missing_review:A001"],
        )
        self.assertIn(
            "review_reasons",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["case_story_fields"],
        )
        self.assertIn(
            "representative_preset_ids",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["case_story_fields"],
        )
        self.assertIn(
            "operator_story_points",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["case_story_fields"],
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["proof_surface_examples"]["partner_demo_samples"][0]["claim_id"],
            "permit-family-aaa111",
        )
        self.assertEqual(
            catalog_contracts["master_catalog"]["proof_surface_examples"]["partner_demo_samples"][0]["binding_preset_id"],
            "permit-family-aaa111:document_missing_review:A001",
        )
        self.assertIn(
            "other_requirement_documents_missing",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["partner_demo_samples"][0]["review_reasons"],
        )
        self.assertIn(
            "representative_statuses",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["partner_demo_fields"],
        )
        self.assertIn(
            "binding_preset_id",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["partner_demo_fields"],
        )


if __name__ == "__main__":
    unittest.main()
