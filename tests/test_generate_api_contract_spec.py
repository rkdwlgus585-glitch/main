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

        spec = generate_api_contract_spec.build_contract_spec(
            registry,
            thresholds,
            permit_selector_catalog=selector_catalog,
            permit_platform_catalog=platform_catalog,
            permit_master_catalog=master_catalog,
            permit_provenance_audit=permit_provenance,
            permit_patent_evidence_bundle=permit_patent,
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
            catalog_contracts["master_catalog"]["proof_surface_examples"]["family_checksum_samples"][0]["checksum"],
            "checksum-a",
        )
        self.assertIn(
            "claim_statement",
            catalog_contracts["master_catalog"]["proof_surface_examples"]["claim_packet_fields"],
        )


if __name__ == "__main__":
    unittest.main()
