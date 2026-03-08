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
            permit_family_case_goldset = base / "permit_family_case_goldset.json"
            permit_case_story_surface = base / "permit_case_story_surface.json"
            permit_operator_demo_packet = base / "permit_operator_demo_packet.json"
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
                                "offering_id": "permit_pro_assist",
                                "display_name": "Permit Pro Assist",
                                "plan": "pro",
                                "allowed_systems": ["permit"],
                                "allowed_features": ["permit_precheck", "permit_precheck_detail", "consult", "meta"],
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
            permit_family_case_goldset.write_text(
                json.dumps(
                    {
                        "summary": {
                            "goldset_complete_family_total": 2,
                            "case_total": 4,
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
                                            "proof_coverage_ratio": "2/2",
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
                                            "proof_coverage_ratio": "2/2",
                                            "review_reason": "capital_shortfall_only",
                                            "manual_review_expected": False,
                                        },
                                    },
                                ],
                            },
                            {
                                "family_key": "전기공사업법 시행령",
                                "claim_id": "permit-family-bbb222",
                                "cases": [
                                    {
                                        "case_id": "permit-family-bbb222:boundary_pass:B001",
                                        "case_kind": "boundary_pass",
                                        "service_code": "B001",
                                        "expected": {
                                            "overall_status": "pass",
                                            "proof_coverage_ratio": "1/1",
                                            "review_reason": "",
                                            "manual_review_expected": False,
                                        },
                                    },
                                    {
                                        "case_id": "permit-family-bbb222:shortfall_fail:B001",
                                        "case_kind": "shortfall_fail",
                                        "service_code": "B001",
                                        "expected": {
                                            "overall_status": "shortfall",
                                            "proof_coverage_ratio": "1/1",
                                            "review_reason": "other_requirement_documents_missing",
                                            "manual_review_expected": True,
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_case_story_surface.write_text(
                json.dumps(
                    {
                        "summary": {
                            "story_family_total": 2,
                            "review_reason_total": 2,
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
                            },
                            {
                                "family_key": "전기공사업법 시행령",
                                "claim_id": "permit-family-bbb222",
                                "preset_total": 3,
                                "manual_review_preset_total": 0,
                                "representative_cases": [
                                    {
                                        "preset_id": "permit-family-bbb222:technician_only_fail:B001",
                                        "review_reason": "technician_shortfall_only",
                                    }
                                ],
                                "operator_story_points": ["기술인력 부족 여부를 즉시 구분"],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            permit_operator_demo_packet.write_text(
                json.dumps(
                    {
                        "summary": {
                            "operator_demo_ready": True,
                            "family_total": 2,
                            "demo_case_total": 4,
                            "manual_review_demo_total": 1,
                            "prompt_case_binding_total": 2,
                        },
                        "families": [
                            {
                                "family_key": "건설산업기본법 시행령",
                                "claim_id": "permit-family-aaa111",
                                "claim_title": "건설업 등록기준 패킷",
                                "proof_coverage_ratio": "2/2",
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
                            },
                            {
                                "family_key": "전기공사업법 시행령",
                                "claim_id": "permit-family-bbb222",
                                "claim_title": "전기공사업 등록기준 패킷",
                                "proof_coverage_ratio": "1/1",
                                "prompt_case_binding": {
                                    "preset_id": "permit-family-bbb222:technician_only_fail:B001",
                                    "service_code": "B001",
                                    "service_name": "build-demo-b",
                                    "expected_status": "shortfall",
                                    "review_reason": "technician_shortfall_only",
                                    "binding_focus": "technician_gap_first",
                                    "binding_question": "기술인력 부족을 먼저 고정했는가.",
                                    "manual_review_expected": False,
                                },
                                "demo_cases": [
                                    {
                                        "service_code": "B001",
                                        "service_name": "전기공사업",
                                        "expected_status": "pass",
                                        "review_reason": "",
                                        "manual_review_expected": False,
                                    },
                                    {
                                        "service_code": "B001",
                                        "service_name": "전기공사업",
                                        "expected_status": "shortfall",
                                        "review_reason": "technician_shortfall_only",
                                        "manual_review_expected": False,
                                    },
                                ],
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
                permit_family_case_goldset_path=permit_family_case_goldset,
                permit_case_story_surface_path=permit_case_story_surface,
                permit_operator_demo_packet_path=permit_operator_demo_packet,
                yangdo_precision_path=yangdo_precision,
                yangdo_contract_path=yangdo_contract,
            )

            self.assertEqual(payload["summary"]["offering_count"], 4)
            self.assertEqual(payload["summary"]["standard_offering_count"], 1)
            self.assertEqual(payload["summary"]["pro_offering_count"], 3)
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
            self.assertEqual(payload["summary"]["permit_family_case_goldset_family_total"], 2)
            self.assertEqual(payload["summary"]["permit_family_case_total"], 4)
            self.assertEqual(payload["summary"]["permit_family_case_sample_total"], 4)
            self.assertEqual(payload["summary"]["permit_edge_case_total"], 0)
            self.assertEqual(payload["summary"]["permit_edge_case_family_total"], 0)
            self.assertEqual(payload["summary"]["permit_manual_review_case_total"], 0)
            self.assertEqual(payload["summary"]["permit_widget_case_parity_family_total"], 2)
            self.assertEqual(payload["summary"]["permit_case_story_family_total"], 2)
            self.assertEqual(payload["summary"]["permit_case_story_review_reason_total"], 2)
            self.assertEqual(payload["summary"]["permit_case_story_manual_review_family_total"], 1)
            self.assertEqual(payload["summary"]["permit_case_story_sample_total"], 2)
            self.assertTrue(payload["summary"]["permit_case_story_surface_ready"])
            self.assertEqual(payload["summary"]["permit_operator_demo_family_total"], 2)
            self.assertEqual(payload["summary"]["permit_operator_demo_case_total"], 4)
            self.assertEqual(payload["summary"]["permit_operator_demo_manual_review_total"], 1)
            self.assertEqual(payload["summary"]["permit_partner_demo_sample_total"], 2)
            self.assertEqual(payload["summary"]["permit_partner_binding_sample_total"], 2)
            self.assertTrue(payload["summary"]["permit_partner_demo_surface_ready"])
            self.assertTrue(payload["summary"]["permit_partner_binding_surface_ready"])
            self.assertEqual(payload["packaging"]["public_platform"]["host"], "seoulmna.kr")
            self.assertEqual(payload["packaging"]["listing_market"]["host"], "seoulmna.co.kr")
            self.assertIn("yangdo_standard", payload["packaging"]["partner_rental"]["widget_standard"])
            self.assertIn("permit_pro", payload["packaging"]["partner_rental"]["api_or_detail_pro"])

            self.assertEqual(payload["summary"]["permit_offering_count"], 3)
            self.assertEqual(payload["summary"]["permit_standard_count"], 0)
            self.assertEqual(payload["summary"]["permit_detail_checklist_count"], 2)
            self.assertEqual(payload["summary"]["permit_manual_review_assist_count"], 1)

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
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["family_case_goldset_family_total"],
                2,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["widget_case_parity_family_total"],
                2,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_family_total"],
                2,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_review_reason_total"],
                2,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_manual_review_family_total"],
                1,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_samples"][0]["claim_id"],
                "permit-family-aaa111",
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_samples"][0]["representative_preset_ids"],
                ["permit-family-aaa111:document_missing_review:A001"],
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["operator_demo_family_total"],
                2,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["operator_demo_case_total"],
                4,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["operator_demo_manual_review_total"],
                1,
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_sample_total"],
                2,
            )
            self.assertTrue(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_surface_ready"]
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_binding_sample_total"],
                2,
            )
            self.assertTrue(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_binding_surface_ready"]
            )
            self.assertIn(
                "claim_title",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_fields"],
            )
            self.assertIn(
                "binding_preset_id",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_fields"],
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_samples"][0]["claim_id"],
                "permit-family-aaa111",
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_samples"][0]["binding_preset_id"],
                "permit-family-aaa111:document_missing_review:A001",
            )
            self.assertIn(
                "other_requirement_documents_missing",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["partner_demo_samples"][0]["review_reasons"],
            )
            self.assertIn(
                "review_reasons",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_sample_fields"],
            )
            self.assertIn(
                "representative_preset_ids",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_sample_fields"],
            )
            self.assertIn(
                "operator_story_points",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["case_story_sample_fields"],
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["family_case_samples"][0]["case_id"],
                "permit-family-aaa111:boundary_pass:A001",
            )
            self.assertEqual(
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["family_case_samples"][0]["expected_status"],
                "pass",
            )
            self.assertIn(
                "review_reason",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["family_case_sample_fields"],
            )
            self.assertIn(
                "manual_review_expected",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["family_case_sample_fields"],
            )
            self.assertIn(
                "manual_review_expected",
                payload["packaging"]["partner_rental"]["permit_widget_feeds"]["family_case_samples"][0],
            )

            permit_precheck = payload["packaging"]["partner_rental"]["permit_precheck"]
            self.assertEqual(permit_precheck["package_matrix"]["detail_checklist"]["offering_ids"], ["permit_pro", "combo_pro"])
            self.assertEqual(permit_precheck["package_matrix"]["manual_review_assist"]["offering_ids"], ["permit_pro_assist"])
            self.assertEqual(permit_precheck["lane_positioning"]["detail_checklist"]["upgrade_target"], "manual_review_assist")
            self.assertEqual(permit_precheck["service_flow_policy"], "public_summary_then_checklist_or_manual_review")

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
