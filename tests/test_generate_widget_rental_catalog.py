import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_widget_rental_catalog import build_widget_rental_catalog


class GenerateWidgetRentalCatalogTests(unittest.TestCase):
    def test_build_widget_rental_catalog_summarizes_offerings_and_bridge_policy(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            registry = base / "tenant_registry.json"
            thresholds = base / "plan_thresholds.json"
            operations = base / "operations.json"
            permit_selector = base / "permit_selector.json"
            permit_platform = base / "permit_platform.json"
            permit_master = base / "permit_master.json"
            permit_provenance = base / "permit_provenance.json"
            permit_patent = base / "permit_patent.json"
            yangdo_precision = base / "yangdo_precision.json"
            yangdo_contract = base / "yangdo_contract.json"

            registry.write_text(
                json.dumps(
                    {
                        "default_tenant_id": "seoul_main",
                        "tenants": [
                            {
                                "tenant_id": "seoul_main",
                                "display_name": "SeoulMNA",
                                "plan": "pro_internal",
                                "hosts": ["seoulmna.kr"],
                                "allowed_systems": ["yangdo", "permit"],
                            },
                            {
                                "tenant_id": "seoul_widget_unlimited",
                                "display_name": "Seoul Widget Internal",
                                "plan": "pro_internal",
                                "hosts": ["seoulmna.co.kr"],
                                "allowed_systems": ["yangdo", "permit"],
                            },
                        ],
                        "offering_templates": [
                            {
                                "offering_id": "yangdo_standard",
                                "display_name": "Yangdo Standard",
                                "plan": "standard",
                                "allowed_systems": ["yangdo"],
                                "allowed_features": ["estimate", "consult", "usage"],
                            },
                            {
                                "offering_id": "permit_pro",
                                "display_name": "Permit Pro",
                                "plan": "pro",
                                "allowed_systems": ["permit"],
                                "allowed_features": ["permit_precheck", "permit_precheck_detail", "meta"],
                            },
                            {
                                "offering_id": "combo_pro",
                                "display_name": "Combo Pro",
                                "plan": "pro",
                                "allowed_systems": ["yangdo", "permit"],
                                "allowed_features": ["estimate_detail", "permit_precheck_detail", "usage"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            thresholds.write_text(
                json.dumps(
                    {
                        "token_estimates": {"yangdo_ok": 1200, "permit_ok": 900},
                        "plans": {
                            "standard": {"included_tokens": 1000000, "max_usage_events": 4000, "overage_price_per_1k_usd": 0.002},
                            "pro": {"included_tokens": 5000000, "max_usage_events": 15000, "overage_price_per_1k_usd": 0.0016},
                            "pro_internal": {"included_tokens": 0, "max_usage_events": 0, "overage_price_per_1k_usd": 0.0},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            operations.write_text(
                json.dumps(
                    {
                        "topology": {
                            "main_platform_host": "seoulmna.kr",
                            "listing_market_host": "seoulmna.co.kr",
                            "public_calculator_mount_host": "seoulmna.kr",
                            "private_engine_public_path": "/_calc/*",
                        },
                        "decisions": {"partner_uniform_required_inputs": True},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_selector.write_text(
                json.dumps({"summary": {"selector_entry_total": 53, "selector_focus_total": 50, "selector_inferred_total": 3}}, ensure_ascii=False),
                encoding="utf-8",
            )
            permit_platform.write_text(
                json.dumps(
                    {
                        "summary": {
                            "platform_industry_total": 53,
                            "platform_focus_registry_row_total": 50,
                            "platform_promoted_selector_total": 0,
                            "platform_absorbed_focus_total": 0,
                            "platform_real_with_selector_alias_total": 3,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_master.write_text(
                json.dumps(
                    {
                        "summary": {
                            "master_industry_total": 53,
                            "master_focus_registry_row_total": 50,
                            "master_promoted_row_total": 0,
                            "master_absorbed_row_total": 0,
                            "master_real_with_alias_total": 3,
                            "master_canonicalized_promoted_total": 0,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_provenance.write_text(
                json.dumps(
                    {
                        "summary": {
                            "candidate_pack_total": 3,
                            "master_inferred_overlay_total": 3,
                            "rows_with_raw_source_proof_total": 50,
                            "focus_family_registry_with_raw_source_proof_total": 50,
                            "focus_family_registry_missing_raw_source_proof_total": 0,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_patent.write_text(
                json.dumps(
                    {
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
                            },
                            {
                                "family_key": "전기공사업법 시행령",
                                "claim_packet": {
                                    "claim_id": "permit-family-bbb222",
                                    "source_proof_summary": {
                                        "checksum_samples": ["checksum-b"],
                                    },
                                },
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_precision.write_text(
                json.dumps(
                    {
                        "summary": {
                            "scenario_count": 6,
                            "precision_ok": True,
                            "high_precision_ok": True,
                            "summary_publication_ok": True,
                            "detail_explainability_ok": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_contract.write_text(
                json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_widget_rental_catalog(
                registry_path=registry,
                thresholds_path=thresholds,
                operations_path=operations,
                permit_selector_path=permit_selector,
                permit_platform_path=permit_platform,
                permit_master_path=permit_master,
                permit_provenance_path=permit_provenance,
                permit_patent_path=permit_patent,
                yangdo_precision_path=yangdo_precision,
                yangdo_contract_path=yangdo_contract,
            )

            self.assertEqual(payload["summary"]["offering_count"], 3)
            self.assertEqual(payload["summary"]["standard_offering_count"], 1)
            self.assertEqual(payload["summary"]["pro_offering_count"], 2)
            self.assertEqual(payload["summary"]["yangdo_recommendation_offering_count"], 2)
            self.assertEqual(payload["summary"]["yangdo_recommendation_standard_count"], 1)
            self.assertEqual(payload["summary"]["yangdo_recommendation_detail_count"], 1)
            self.assertEqual(payload["summary"]["yangdo_recommendation_summary_bridge_count"], 1)
            self.assertEqual(payload["summary"]["yangdo_recommendation_detail_lane_count"], 1)
            self.assertEqual(payload["summary"]["yangdo_recommendation_consult_assist_count"], 0)
            self.assertEqual(payload["summary"]["yangdo_recommendation_precision_scenario_count"], 6)
            self.assertTrue(payload["summary"]["yangdo_recommendation_precision_ok"])
            self.assertTrue(payload["summary"]["yangdo_recommendation_contract_ok"])
            self.assertEqual(payload["summary"]["yangdo_recommendation_bridge_policy"], "kr_service_to_listing_or_consult")
            self.assertEqual(payload["summary"]["internal_tenant_count"], 2)
            self.assertEqual(payload["summary"]["permit_selector_entry_total"], 53)
            self.assertEqual(payload["summary"]["permit_platform_industry_total"], 53)
            self.assertEqual(payload["summary"]["permit_platform_focus_registry_row_total"], 50)
            self.assertEqual(payload["summary"]["permit_master_industry_total"], 53)
            self.assertEqual(payload["summary"]["permit_master_focus_registry_row_total"], 50)
            self.assertEqual(payload["summary"]["permit_candidate_pack_total"], 3)
            self.assertEqual(payload["summary"]["permit_raw_source_proof_row_total"], 50)
            self.assertEqual(payload["summary"]["permit_focus_family_registry_with_raw_source_proof_total"], 50)
            self.assertEqual(payload["summary"]["permit_focus_family_registry_missing_raw_source_proof_total"], 0)
            self.assertEqual(payload["summary"]["permit_raw_source_proof_family_total"], 6)
            self.assertEqual(payload["summary"]["permit_claim_packet_family_total"], 6)
            self.assertEqual(payload["summary"]["permit_claim_packet_complete_family_total"], 6)
            self.assertEqual(payload["summary"]["permit_checksum_sample_family_total"], 6)
            self.assertEqual(payload["summary"]["permit_checksum_sample_total"], 2)
            self.assertEqual(payload["packaging"]["public_platform"]["host"], "seoulmna.kr")
            self.assertEqual(payload["packaging"]["listing_market"]["host"], "seoulmna.co.kr")
            self.assertIn("yangdo_standard", payload["packaging"]["partner_rental"]["widget_standard"])
            self.assertIn("permit_pro", payload["packaging"]["partner_rental"]["api_or_detail_pro"])

            recommendation = payload["packaging"]["partner_rental"]["yangdo_recommendation"]
            self.assertIn("yangdo_standard", recommendation["summary_offerings"])
            self.assertIn("combo_pro", recommendation["detail_offerings"])
            self.assertEqual(recommendation["package_matrix"]["summary_market_bridge"]["offering_ids"], ["yangdo_standard"])
            self.assertEqual(recommendation["package_matrix"]["detail_explainable"]["offering_ids"], ["combo_pro"])
            self.assertEqual(recommendation["package_matrix"]["consult_assist"]["offering_ids"], [])
            self.assertEqual(recommendation["lane_positioning"]["detail_explainable"]["upgrade_target"], "consult_assist")
            self.assertEqual(recommendation["lane_positioning"]["detail_explainable"]["cta_bias"], "explanation_first")
            self.assertEqual(recommendation["precision_scenario_count"], 6)
            self.assertEqual(recommendation["listing_runtime_policy"], "never_embed_tools_on_listing_domain")
            self.assertTrue(bool(recommendation["bridge_story"]))
            self.assertTrue(bool(recommendation["public_story"]))
            self.assertTrue(bool(recommendation["detail_story"]))
            self.assertEqual(len(recommendation["supported_precision_labels"]), 3)
            self.assertTrue(recommendation["contract_ok"])

            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["recommended_primary_feed"],
                "master_catalog",
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["candidate_pack_total"],
                3,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["raw_source_proof_row_total"],
                50,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["raw_source_proof_family_total"],
                6,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["claim_packet_family_total"],
                6,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["checksum_sample_family_total"],
                6,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["platform_focus_registry_row_total"],
                50,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["proof_checksum_samples"][0]["checksum"],
                "checksum-a",
            )

            combo = next(row for row in payload["offerings"] if row["offering_id"] == "combo_pro")
            self.assertEqual(combo["response_tier"], "detail")
            self.assertIn("api", combo["delivery_modes"])
            self.assertEqual(combo["request_token_estimates"]["combo"], 2100)
            self.assertEqual(combo["limits"]["effective_limit"], 2380)
            self.assertTrue(combo["recommendation_enabled"])
            self.assertEqual(combo["recommendation_visibility"], "detail_explainable")
            self.assertEqual(combo["recommendation_package_lane"], "detail_explainable")


if __name__ == "__main__":
    unittest.main()
