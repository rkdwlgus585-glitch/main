import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_operations_packet import build_operations_packet, main


class GenerateOperationsPacketTests(unittest.TestCase):
    def test_build_operations_packet_aggregates_sources(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            readiness = base / "readiness.json"
            release = base / "release.json"
            risk = base / "risk.json"
            attorney = base / "attorney.json"
            platform_audit = base / "platform_audit.json"
            surface_stack = base / "surface_stack.json"
            private_proxy = base / "private_proxy.json"
            wp_lab = base / "wp_lab.json"
            wp_runtime = base / "wp_runtime.json"
            wp_runtime_validation = base / "wp_runtime_validation.json"
            wp_assets = base / "wp_assets.json"
            wp_ia = base / "wp_ia.json"
            wp_ux = base / "wp_ux.json"
            wp_blueprints = base / "wp_blueprints.json"
            wp_apply = base / "wp_apply.json"
            wp_strategy = base / "wp_strategy.json"
            astra_ref = base / "astra_ref.json"
            kr_cutover = base / "kr_cutover.json"
            kr_traffic = base / "kr_traffic.json"
            kr_ready = base / "kr_ready.json"
            kr_preview = base / "kr_preview.json"
            onboarding = base / "onboarding.json"
            partner_flow = base / "partner_flow.json"
            partner_preview = base / "partner_preview.json"
            partner_alignment = base / "partner_alignment.json"
            partner_resolution = base / "partner_resolution.json"
            partner_snapshot = base / "partner_snapshot.json"
            partner_simulation = base / "partner_simulation.json"
            yangdo_qa = base / "yangdo_qa.json"
            yangdo_precision = base / "yangdo_precision.json"
            yangdo_diversity = base / "yangdo_diversity.json"
            yangdo_contract = base / "yangdo_contract.json"
            yangdo_bridge = base / "yangdo_bridge.json"
            yangdo_ux = base / "yangdo_ux.json"
            yangdo_alignment = base / "yangdo_alignment.json"
            yangdo_service_copy = base / "yangdo_service_copy.json"
            rental_catalog = base / "rental_catalog.json"
            improvement_loop = base / "improvement_loop.json"

            readiness.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"release_ready": True, "next_actions": ["release go"]}}), encoding="utf-8")
            release.write_text(json.dumps({"ok": False, "blocking_issues": ["confirm_live_missing"], "handoff": {"runtime_verified": False, "next_actions": ["confirm-live input"]}, "artifact_summary": {"runtime": {"blocking_issues": ["runtime_failed"]}}}), encoding="utf-8")
            risk.write_text(json.dumps({"ok": True, "business_core_status": "green", "run_summary": {"ran_tests": 10, "issue_count": 0}}), encoding="utf-8")
            attorney.write_text(json.dumps({"tracks": [{}, {}], "executive_summary": {"independent_systems": ["yangdo", "permit"], "claim_strategy": ["A/B split"], "attorney_handoff": ["independent filings"]}}), encoding="utf-8")
            platform_audit.write_text(json.dumps({"front": {"canonical_public_host": "seoulmna.kr", "channel_role": "platform_front", "listing_market_host": "seoulmna.co.kr", "public_calculator_mount_base": "https://seoulmna.kr/_calc", "private_engine_visibility": "reverse_proxy_hidden_origin", "engine_origin": "https://calc.seoulmna.co.kr", "current_live_public_stack": "wordpress_astra_live"}, "completion_summary": {"front_platform_status": "policy_ready_live_confirmation_pending"}}, ensure_ascii=False), encoding="utf-8")
            surface_stack.write_text(json.dumps({"surfaces": {"kr": {"stack": "nextjs_vercel_front"}, "co": {"stack": "gnuboard_weaver_like"}}, "wordpress": {"live_applicability": {"decision": "sandbox_only"}, "candidate_package_slugs": ["wordpress-core", "astra"]}, "decisions": {"plugin_theme_strategy": "wordpress_assets_sandbox_only"}}, ensure_ascii=False), encoding="utf-8")
            private_proxy.write_text(json.dumps({"topology": {"main_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr", "public_mount_base": "https://seoulmna.kr/_calc", "private_engine_origin": "https://calc.seoulmna.co.kr"}, "decision": {"public_contract": "https://seoulmna.kr/_calc/*", "engine_visibility": "hidden_origin_only"}}, ensure_ascii=False), encoding="utf-8")
            wp_lab.write_text(json.dumps({"summary": {"package_count": 4, "downloaded_count": 4, "staging_ready_count": 4, "runtime_ready": False, "runtime_blockers": ["php_missing", "docker_missing"]}, "runtime": {"blockers": ["php_missing", "docker_missing"]}}, ensure_ascii=False), encoding="utf-8")
            wp_runtime.write_text(json.dumps({"summary": {"runtime_scaffold_ready": True, "docker_available": False, "local_bind_only": True}, "policy": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False), encoding="utf-8")
            wp_runtime_validation.write_text(json.dumps({"summary": {"runtime_scaffold_ready": True, "runtime_ready": False, "blockers": ["docker_missing"]}, "handoff": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False), encoding="utf-8")
            wp_assets.write_text(json.dumps({"summary": {"theme_ready": True, "plugin_ready": True}, "theme": {"slug": "seoulmna-platform-child"}, "plugin": {"slug": "seoulmna-platform-bridge", "public_mount_host": "seoulmna.kr", "public_mount_base": "https://seoulmna.kr/_calc", "lazy_iframe_policy": True}}, ensure_ascii=False), encoding="utf-8")
            wp_ia.write_text(json.dumps({"summary": {"page_count": 6, "service_page_count": 2, "lazy_gate_pages": ["yangdo", "permit"], "cta_only_pages": ["home", "knowledge"]}, "topology": {"platform_host": "seoulmna.kr", "public_mount": "https://seoulmna.kr/_calc/<type>?embed=1"}}, ensure_ascii=False), encoding="utf-8")
            wp_ux.write_text(json.dumps({"summary": {"page_count": 6, "issue_count": 0, "ux_ok": True, "service_pages_ok": True, "market_bridge_ok": True, "yangdo_recommendation_surface_ok": True}}, ensure_ascii=False), encoding="utf-8")
            wp_blueprints.write_text(json.dumps({"summary": {"blueprint_count": 6, "lazy_gate_pages": ["yangdo", "permit"], "cta_only_pages": ["home", "knowledge"], "navigation_ready": True}}, ensure_ascii=False), encoding="utf-8")
            wp_apply.write_text(json.dumps({"summary": {"page_step_count": 6, "cutover_ready": True, "service_page_count": 2}}, ensure_ascii=False), encoding="utf-8")
            wp_strategy.write_text(json.dumps({"current_live_stack": {"kr_host": "seoulmna.kr", "co_role": "listing_market_site"}, "runtime_decision": {"primary_runtime": "wordpress_astra_live", "support_runtime": "private_engine_behind_kr_reverse_proxy"}, "calculator_mount_decision": {"recommended_pattern": "cta_on_home_lazy_gate_on_service_page_private_runtime_on_kr", "private_engine_public_mount": "https://seoulmna.kr/_calc/<type>?embed=1", "recommended_by_page": {"listing_site_policy": "https://seoulmna.co.kr/ stays listing-focused and links back to seoulmna.kr service pages."}}, "plugin_stack": {"keep_live": ["astra", "rank-math"], "stage_first": ["seoulmna-platform-child"], "avoid_live_duplication": ["wordpress-seo"]}}, ensure_ascii=False), encoding="utf-8")
            astra_ref.write_text(json.dumps({"astra": {"theme_name": "Astra", "theme_version": "4.12.3"}, "decision": {"strategy": "reference_only_for_next_front", "usable_for_next_front": ["typography_scale_reference"]}}, ensure_ascii=False), encoding="utf-8")
            kr_cutover.write_text(json.dumps({"summary": {"cutover_ready": True, "service_page_count": 2, "traffic_gate_ok": True}, "topology": {"public_mount_base": "https://seoulmna.kr/_calc", "private_engine_origin": "https://calc.seoulmna.co.kr"}}, ensure_ascii=False), encoding="utf-8")
            kr_traffic.write_text(json.dumps({"decision": {"traffic_leak_blocked": True, "remaining_risks": []}, "live_probe": {"server_started": True, "all_routes_no_iframe": True}}, ensure_ascii=False), encoding="utf-8")
            kr_ready.write_text(json.dumps({"blocking_issues": ["vercel_auth_missing"], "handoff": {"preview_deploy_ready": False, "next_actions": ["Authenticate Vercel CLI for the kr platform front"]}}, ensure_ascii=False), encoding="utf-8")
            kr_preview.write_text(json.dumps({"handoff": {"preview_deployed": False, "preview_url": ""}}, ensure_ascii=False), encoding="utf-8")
            onboarding.write_text(json.dumps({"tenants": [{"tenant_id": "partner_demo", "activation_ready": False}], "channels": [{"channel_id": "partner_demo", "activation_ready": False}]}), encoding="utf-8")
            partner_flow.write_text(json.dumps({"ok": False, "activation_blockers": ["missing_source_proof_url_pending", "missing_api_key_value"], "handoff": {"activation_ready": False, "next_actions": ["Provide partner contract proof URL"], "remaining_required_inputs": ["partner_proof_url", "partner_api_key"], "resolved_inputs": []}}), encoding="utf-8")
            partner_preview.write_text(json.dumps({"recommended_path": {"scenario": "proof_and_key", "remaining_required_inputs": ["partner_data_source_approval"], "next_actions": ["approval"]}}), encoding="utf-8")
            partner_alignment.write_text(json.dumps({"summary": {"ok": True, "baseline_matches_current": True, "recommended_clears_current": False}}), encoding="utf-8")
            partner_resolution.write_text(json.dumps({"summary": {"ok": True, "matches_preview_expected_remaining": True}}), encoding="utf-8")
            partner_snapshot.write_text(json.dumps({"summary": {"partner_tenant_count": 2, "ready_tenant_count": 1, "scenario_counts": {"baseline": 1, "proof_key_and_approval": 1}}}), encoding="utf-8")
            partner_simulation.write_text(json.dumps({"summary": {"partner_count": 2, "baseline_ready_count": 1, "ready_after_simulation_count": 2, "newly_ready_count": 1, "all_ready_after_simulation": True}}), encoding="utf-8")
            yangdo_qa.write_text(json.dumps({"summary": {"scenario_count": 5, "passed_count": 5, "failed_count": 0, "qa_ok": True, "strict_profile_regression_ok": True, "fallback_regression_ok": True, "balance_exclusion_regression_ok": True, "assistive_precision_regression_ok": True, "summary_projection_regression_ok": True, "precision_counts": {"high": 2, "medium": 1, "assist": 1}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_precision.write_text(json.dumps({"summary": {"scenario_count": 6, "passed_count": 6, "failed_count": 0, "precision_ok": True, "high_precision_ok": True, "fallback_precision_ok": True, "balance_excluded_precision_ok": True, "assist_precision_ok": True, "summary_publication_ok": True, "detail_explainability_ok": True, "sector_groups": {"general": {"scenario_count": 5, "passed_count": 5, "failed_count": 0}}, "price_bands": {"mid_2_to_4_eok": {"scenario_count": 3, "passed_count": 3, "failed_count": 0}}, "response_tiers": {"summary": {"scenario_count": 1, "passed_count": 1, "failed_count": 0}, "detail": {"scenario_count": 1, "passed_count": 1, "failed_count": 0}}, "precision_counts": {"high": 2, "medium": 1, "assist": 1}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_diversity.write_text(json.dumps({"summary": {"scenario_count": 7, "passed_count": 7, "failed_count": 0, "diversity_ok": True, "top1_stability_ok": True, "price_band_spread_ok": True, "focus_signature_spread_ok": True, "detail_projection_contract_ok": True, "precision_tier_spread_ok": True, "unique_listing_ok": True, "listing_bridge_ok": True, "listing_band_spread_ok": True, "cluster_concentration_ok": True, "top_rank_signature_concentration_ok": True, "price_band_concentration_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_contract.write_text(json.dumps({"summary": {"contract_ok": True, "summary_safe": True, "detail_explainable": True, "internal_debug_visible": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_bridge.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_slug": "/yangdo",
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                            "market_bridge_ready": True,
                            "rental_ready": True,
                            "supported_precision_labels": ["우선 추천", "조건 유사", "보조 검토"],
                        },
                        "public_summary_contract": {
                            "fields": [
                                "display_low_eok",
                                "display_high_eok",
                                "recommendation_label",
                                "recommendation_focus",
                                "reasons",
                                "url",
                            ]
                        },
                        "detail_contract": {
                            "fields": ["precision_tier", "fit_summary", "matched_axes", "mismatch_flags"]
                        },
                        "market_bridge_policy": {"service_flow_policy": "public_summary_then_market_or_consult"},
                        "rental_packaging": {
                            "summary_offerings": ["yangdo_standard"],
                            "detail_offerings": ["yangdo_pro_detail", "yangdo_pro"],
                            "internal_offerings": ["seoul_internal"],
                            "summary_policy": "safe-summary",
                            "detail_policy": "detail-explainable",
                            "internal_policy": "internal-full",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_ux.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_surface_ready": True,
                            "market_bridge_ready": True,
                            "rental_exposure_ready": True,
                            "precision_ready": True,
                            "detail_explainability_ready": True,
                            "service_flow_policy": "public_summary_then_market_or_consult",
                        },
                        "public_summary_experience": {
                            "visible_fields": [
                                "display_low_eok",
                                "display_high_eok",
                                "recommendation_label",
                                "recommendation_focus",
                                "reasons",
                                "url",
                            ],
                            "cta_primary_label": "?? ?? ?? ??",
                            "cta_secondary_label": "??? ?? ??",
                        },
                        "detail_explainable_experience": {
                            "visible_fields": [
                                "precision_tier",
                                "fit_summary",
                                "matched_axes",
                                "mismatch_flags",
                            ]
                        },
                        "consult_detail_experience": {
                            "visible_fields": [
                                "precision_tier",
                                "fit_summary",
                                "matched_axes",
                                "mismatch_flags",
                            ]
                        },
                        "rental_exposure_matrix": {
                            "standard": {"offerings": ["yangdo_standard"]},
                            "pro_detail": {"offerings": ["yangdo_pro_detail"]},
                            "pro_consult": {"offerings": ["yangdo_pro"]},
                            "internal": {"offerings": ["seoul_internal"]},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_alignment.write_text(json.dumps({"summary": {"alignment_ok": True, "issue_count": 0, "service_flow_policy_ok": True, "cta_labels_ok": True, "field_contract_ok": True, "offering_exposure_ok": True, "patent_handoff_ok": True, "contract_story_ok": True, "supported_labels_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_service_copy.write_text(json.dumps({"summary": {"packet_ready": True, "service_copy_ready": True, "low_precision_consult_first_ready": True, "market_bridge_story_ready": True, "market_fit_interpretation_ready": True, "lane_stories_ready": True, "service_slug": "/yangdo", "platform_host": "seoulmna.kr", "listing_host": "seoulmna.co.kr", "precision_label_count": 3, "recommendation_offering_count": 3}, "hero": {"title": "가격 범위와 유사매물 추천을 함께 읽고, 실제 시장 확인과 상담으로 분기합니다."}, "cta_ladder": {"primary_market_bridge": {"label": "추천 매물 흐름 보기"}, "secondary_consult": {"label": "상담형 상세 요청"}}, "offering_matrix": {"summary_market_bridge": ["yangdo_standard"], "detail_explainable": ["yangdo_pro_detail"], "consult_assist": ["yangdo_pro"], "internal_full": ["seoul_internal"]}}, ensure_ascii=False), encoding="utf-8")
            rental_catalog.write_text(json.dumps({"summary": {"offering_count": 6, "standard_offering_count": 3, "pro_offering_count": 3, "combo_offering_count": 2, "yangdo_recommendation_offering_count": 3, "yangdo_recommendation_standard_count": 1, "yangdo_recommendation_detail_count": 2, "yangdo_recommendation_summary_bridge_count": 1, "yangdo_recommendation_detail_lane_count": 1, "yangdo_recommendation_consult_assist_count": 1, "internal_tenant_count": 2, "public_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr"}, "packaging": {"partner_rental": {"widget_standard": ["yangdo_standard", "permit_standard"], "api_or_detail_pro": ["yangdo_pro_detail", "yangdo_pro", "permit_pro"], "yangdo_recommendation": {"summary_offerings": ["yangdo_standard"], "detail_offerings": ["yangdo_pro_detail", "yangdo_pro"], "internal_offerings": ["seoul_internal"], "summary_policy": "safe-summary", "detail_policy": "detail-explainable", "package_matrix": {"summary_market_bridge": {"offering_ids": ["yangdo_standard"]}, "detail_explainable": {"offering_ids": ["yangdo_pro_detail"]}, "consult_assist": {"offering_ids": ["yangdo_pro"]}, "internal_full": {"offering_ids": ["seoul_internal"]}}}}}}, ensure_ascii=False), encoding="utf-8")
            improvement_loop.write_text(json.dumps({"summary": {"immediate_blocker_count": 3, "structural_improvement_count": 2, "patent_hardening_count": 3, "commercialization_gap_count": 2, "top_action_count": 4}, "top_next_actions": [{"priority": 1, "title": "서울건설정보 live release final confirmation", "action": "Run deploy_seoul_widget_embed_release.py with --confirm-live YES"}]}, ensure_ascii=False), encoding="utf-8")

            packet = build_operations_packet(
                readiness_path=readiness,
                release_path=release,
                risk_map_path=risk,
                attorney_path=attorney,
                platform_front_audit_path=platform_audit,
                surface_stack_audit_path=surface_stack,
                private_engine_proxy_spec_path=private_proxy,
                wp_surface_lab_path=wp_lab,
                wp_surface_lab_runtime_path=wp_runtime,
                wp_surface_lab_runtime_validation_path=wp_runtime_validation,
                wp_platform_assets_path=wp_assets,
                wordpress_platform_ia_path=wp_ia,
                wordpress_platform_ux_audit_path=wp_ux,
                wp_platform_blueprints_path=wp_blueprints,
                wordpress_staging_apply_plan_path=wp_apply,
                wordpress_platform_strategy_path=wp_strategy,
                astra_design_reference_path=astra_ref,
                kr_reverse_proxy_cutover_path=kr_cutover,
                kr_traffic_gate_audit_path=kr_traffic,
                kr_deploy_readiness_path=kr_ready,
                kr_preview_deploy_path=kr_preview,
                onboarding_validation_path=onboarding,
                partner_flow_path=partner_flow,
                partner_preview_path=partner_preview,
                partner_preview_alignment_path=partner_alignment,
                partner_resolution_path=partner_resolution,
                partner_input_snapshot_path=partner_snapshot,
                partner_simulation_matrix_path=partner_simulation,
                yangdo_recommendation_qa_path=yangdo_qa,
                yangdo_recommendation_precision_matrix_path=yangdo_precision,
                yangdo_recommendation_diversity_audit_path=yangdo_diversity,
                yangdo_recommendation_contract_audit_path=yangdo_contract,
                yangdo_recommendation_bridge_packet_path=yangdo_bridge,
                yangdo_recommendation_ux_packet_path=yangdo_ux,
                yangdo_recommendation_alignment_audit_path=yangdo_alignment,
                yangdo_service_copy_packet_path=yangdo_service_copy,
                widget_rental_catalog_path=rental_catalog,
                program_improvement_loop_path=improvement_loop,
            )
            self.assertTrue(packet["go_live"]["quality_green"])
            self.assertEqual(packet["topology"]["main_platform_host"], "seoulmna.kr")
            self.assertEqual(packet["topology"]["listing_market_host"], "seoulmna.co.kr")
            self.assertEqual(packet["topology"]["public_calculator_mount_host"], "seoulmna.kr")
            self.assertEqual(packet["topology"]["private_engine_public_path"], "/_calc/*")
            self.assertEqual(packet["topology"]["engine_visibility"], "reverse_proxy_hidden_origin")
            self.assertEqual(packet["summaries"]["private_engine_proxy"]["public_mount_base"], "https://seoulmna.kr/_calc")
            self.assertEqual(packet["summaries"]["private_engine_proxy"]["public_contract"], "https://seoulmna.kr/_calc/*")
            self.assertIn("confirm_live_missing", packet["blockers"])
            self.assertIn("runtime_failed", packet["blockers"])
            self.assertIn("independent filings", packet["summaries"]["attorney"]["handoff_notes"])
            self.assertIn("release_confirmation_required", packet["normalized_blockers"])
            self.assertEqual(packet["decisions"]["kr_platform_decision"], "wordpress_live_path_in_progress")
            self.assertEqual(packet["decisions"]["kr_wordpress_platform_decision"], "wordpress_live_path_in_progress")
            self.assertEqual(packet["decisions"]["kr_next_lane_decision"], "awaiting_vercel_auth")
            self.assertEqual(packet["decisions"]["wp_plugin_decision"], "sandbox_ready_runtime_missing")
            self.assertEqual(packet["topology"]["wp_theme_live_strategy"], "wordpress_assets_sandbox_only")
            self.assertIn("vercel_auth_missing", packet["summaries"]["kr_platform"]["blocking_issues"])
            self.assertEqual(packet["summaries"]["surface_stack"]["kr_stack"], "nextjs_vercel_front")
            self.assertEqual(packet["summaries"]["wp_surface_lab"]["package_count"], 4)
            self.assertTrue(packet["summaries"]["wp_surface_lab_runtime"]["runtime_scaffold_ready"])
            self.assertEqual(packet["summaries"]["wp_surface_lab_runtime"]["localhost_url"], "http://127.0.0.1:18080")
            self.assertEqual(packet["summaries"]["wp_platform_assets"]["theme_slug"], "seoulmna-platform-child")
            self.assertEqual(packet["summaries"]["wp_platform_assets"]["public_mount_host"], "seoulmna.kr")
            self.assertEqual(packet["summaries"]["wordpress_platform_ia"]["page_count"], 6)
            self.assertEqual(packet["summaries"]["wp_platform_blueprints"]["blueprint_count"], 6)
            self.assertEqual(packet["summaries"]["wordpress_staging_apply_plan"]["page_step_count"], 6)
            self.assertEqual(packet["summaries"]["wordpress_platform_strategy"]["primary_runtime"], "wordpress_astra_live")
            self.assertEqual(packet["summaries"]["wordpress_platform_strategy"]["public_mount"], "https://seoulmna.kr/_calc/<type>?embed=1")
            self.assertEqual(packet["summaries"]["astra_design_reference"]["strategy"], "reference_only_for_next_front")
            self.assertEqual(packet["decisions"]["wordpress_ia_decision"], "service_ia_ready")
            self.assertEqual(packet["decisions"]["wp_runtime_decision"], "scaffold_ready_runtime_missing")
            self.assertEqual(packet["decisions"]["reverse_proxy_cutover_decision"], "cutover_ready")
            self.assertTrue(packet["summaries"]["kr_reverse_proxy_cutover"]["cutover_ready"])
            self.assertTrue(packet["decisions"]["kr_traffic_gate_ok"])
            self.assertTrue(packet["summaries"]["kr_traffic_gate"]["all_routes_no_iframe"])
            self.assertEqual(packet["decisions"]["partner_activation_decision"], "awaiting_partner_inputs")
            self.assertTrue(packet["decisions"]["partner_preview_alignment_ok"])
            self.assertIn("confirm_live_yes", packet["required_inputs"]["seoul_live"])
            self.assertIn("partner_proof_url", packet["required_inputs"]["partner_aggregate"])
            self.assertEqual(packet["summaries"]["partner"]["checklists"][0]["required_inputs"], ["partner_proof_url", "partner_api_key"])
            self.assertEqual(packet["summaries"]["partner"]["latest_flow_remaining_required_inputs"], ["partner_proof_url", "partner_api_key"])
            self.assertTrue(packet["summaries"]["partner"]["latest_flow_scope_registered"])
            self.assertEqual(packet["summaries"]["partner"]["preview_recommended_scenario"], "proof_and_key")
            self.assertEqual(packet["decisions"]["partner_fastest_path_scenario"], "proof_and_key")
            self.assertFalse(packet["decisions"]["partner_fastest_path_ready"])
            self.assertEqual(packet["required_inputs"]["partner_fastest_path"], ["partner_data_source_approval"])
            self.assertTrue(packet["decisions"]["partner_resolution_actionable"])
            self.assertEqual(packet["handoff_checklists"]["seoul_live"][0]["key"], "confirm_live_yes")
            self.assertEqual(packet["handoff_checklists"]["partner_activation"][0]["items"][0]["key"], "partner_proof_url")
            self.assertEqual(packet["handoff_checklists"]["seoul_live"][0]["label"], "Live release confirmation")
            self.assertIn("Run deploy_seoul_widget_embed_release.py with --confirm-live YES", packet["next_actions"])
            self.assertEqual(packet["decisions"]["partner_input_snapshot_ready_count"], 1)
            self.assertEqual(packet["decisions"]["partner_simulation_ready_count"], 2)
            self.assertEqual(packet["summaries"]["partner"]["input_snapshot_summary"]["partner_tenant_count"], 2)
            self.assertTrue(packet["summaries"]["partner"]["simulation_matrix_summary"]["all_ready_after_simulation"])
            self.assertTrue(packet["decisions"]["partner_uniform_required_inputs"])
            self.assertEqual(packet["required_inputs"]["partner_common"], ["partner_proof_url", "partner_api_key"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_qa_ok"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_precision_ok"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_diversity_ok"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_concentration_ok"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_contract_ok"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_bridge_ready"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_ux_ready"])
            self.assertTrue(packet["decisions"]["yangdo_recommendation_alignment_ok"])
            self.assertTrue(packet["decisions"]["yangdo_service_copy_ready"])
            self.assertTrue(packet["summaries"]["yangdo_service_copy"]["market_fit_interpretation_ready"])
            self.assertTrue(packet["summaries"]["yangdo_service_copy"]["lane_stories_ready"])
            self.assertTrue(packet["summaries"]["yangdo_recommendation_diversity_audit"]["top_rank_signature_concentration_ok"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_qa"]["scenario_count"], 5)
            self.assertEqual(packet["summaries"]["yangdo_recommendation_precision_matrix"]["scenario_count"], 6)
            self.assertTrue(packet["summaries"]["yangdo_recommendation_precision_matrix"]["detail_explainability_ok"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_diversity_audit"]["scenario_count"], 7)
            self.assertTrue(packet["summaries"]["yangdo_recommendation_diversity_audit"]["detail_projection_contract_ok"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_qa"]["precision_counts"]["high"], 2)
            self.assertTrue(packet["summaries"]["yangdo_recommendation_contract_audit"]["contract_ok"])
            self.assertTrue(packet["summaries"]["yangdo_recommendation_bridge"]["packet_ready"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_bridge"]["service_slug"], "/yangdo")
            self.assertTrue(packet["summaries"]["yangdo_recommendation_bridge"]["market_bridge_ready"])
            self.assertEqual(
                packet["summaries"]["yangdo_recommendation_bridge"]["public_summary_fields"],
                ["display_low_eok", "display_high_eok", "recommendation_label", "recommendation_focus", "reasons", "url"],
            )
            self.assertEqual(packet["summaries"]["yangdo_recommendation_bridge"]["summary_offerings"], ["yangdo_standard"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_bridge"]["detail_offerings"], ["yangdo_pro_detail", "yangdo_pro"])
            self.assertTrue(packet["summaries"]["yangdo_recommendation_ux"]["packet_ready"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["service_flow_policy"], "public_summary_then_market_or_consult")
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["public_primary_cta"], "?? ?? ?? ??")
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["public_secondary_cta"], "??? ?? ??")
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["public_fields"], ["display_low_eok", "display_high_eok", "recommendation_label", "recommendation_focus", "reasons", "url"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["detail_explainable_fields"], ["precision_tier", "fit_summary", "matched_axes", "mismatch_flags"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["detail_fields"], ["precision_tier", "fit_summary", "matched_axes", "mismatch_flags"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["standard_offerings"], ["yangdo_standard"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["pro_detail_offerings"], ["yangdo_pro_detail"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["pro_consult_offerings"], ["yangdo_pro"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_ux"]["internal_offerings"], ["seoul_internal"])
            self.assertTrue(packet["summaries"]["yangdo_recommendation_alignment"]["alignment_ok"])
            self.assertTrue(packet["summaries"]["yangdo_recommendation_alignment"]["service_flow_policy_ok"])
            self.assertTrue(packet["summaries"]["yangdo_recommendation_alignment"]["cta_labels_ok"])
            self.assertEqual(packet["summaries"]["yangdo_recommendation_alignment"]["issue_count"], 0)
            self.assertTrue(packet["summaries"]["yangdo_service_copy"]["packet_ready"])
            self.assertTrue(packet["summaries"]["yangdo_service_copy"]["service_copy_ready"])
            self.assertEqual(packet["summaries"]["yangdo_service_copy"]["detail_explainable_offerings"], ["yangdo_pro_detail"])
            self.assertEqual(packet["summaries"]["yangdo_service_copy"]["consult_assist_offerings"], ["yangdo_pro"])
            self.assertEqual(packet["summaries"]["yangdo_service_copy"]["hero_title"], "가격 범위와 유사매물 추천을 함께 읽고, 실제 시장 확인과 상담으로 분기합니다.")
            self.assertEqual(packet["summaries"]["widget_rental_catalog"]["offering_count"], 6)
            self.assertEqual(packet["summaries"]["widget_rental_catalog"]["yangdo_recommendation_offering_count"], 3)
            self.assertEqual(packet["summaries"]["widget_rental_catalog"]["yangdo_recommendation_summary"], ["yangdo_standard"])
            self.assertEqual(packet["summaries"]["widget_rental_catalog"]["yangdo_recommendation_detail"], ["yangdo_pro_detail", "yangdo_pro"])
            self.assertEqual(packet["summaries"]["program_improvement_loop"]["immediate_blocker_count"], 3)
            self.assertEqual(packet["summaries"]["program_improvement_loop"]["top_next_actions"][0]["priority"], 1)

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            readiness = base / "readiness.json"
            release = base / "release.json"
            risk = base / "risk.json"
            attorney = base / "attorney.json"
            platform_audit = base / "platform_audit.json"
            surface_stack = base / "surface_stack.json"
            private_proxy = base / "private_proxy.json"
            wp_lab = base / "wp_lab.json"
            wp_runtime = base / "wp_runtime.json"
            wp_runtime_validation = base / "wp_runtime_validation.json"
            wp_assets = base / "wp_assets.json"
            wp_ia = base / "wp_ia.json"
            wp_ux = base / "wp_ux.json"
            wp_blueprints = base / "wp_blueprints.json"
            wp_apply = base / "wp_apply.json"
            wp_strategy = base / "wp_strategy.json"
            astra_ref = base / "astra_ref.json"
            kr_cutover = base / "kr_cutover.json"
            kr_traffic = base / "kr_traffic.json"
            kr_ready = base / "kr_ready.json"
            kr_preview = base / "kr_preview.json"
            onboarding = base / "onboarding.json"
            partner_flow = base / "partner_flow.json"
            partner_preview = base / "partner_preview.json"
            partner_alignment = base / "partner_alignment.json"
            partner_resolution = base / "partner_resolution.json"
            partner_snapshot = base / "partner_snapshot.json"
            partner_simulation = base / "partner_simulation.json"
            yangdo_qa = base / "yangdo_qa.json"
            yangdo_precision = base / "yangdo_precision.json"
            yangdo_diversity = base / "yangdo_diversity.json"
            yangdo_contract = base / "yangdo_contract.json"
            yangdo_bridge = base / "yangdo_bridge.json"
            yangdo_ux = base / "yangdo_ux.json"
            yangdo_alignment = base / "yangdo_alignment.json"
            yangdo_service_copy = base / "yangdo_service_copy.json"
            rental_catalog = base / "rental_catalog.json"
            improvement_loop = base / "improvement_loop.json"
            readiness.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"release_ready": True}}), encoding="utf-8")
            release.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"runtime_verified": True}, "artifact_summary": {}}), encoding="utf-8")
            risk.write_text(json.dumps({"ok": True, "business_core_status": "green", "run_summary": {"ran_tests": 1, "issue_count": 0}}), encoding="utf-8")
            attorney.write_text(json.dumps({"tracks": [{}], "executive_summary": {"independent_systems": ["yangdo"]}}), encoding="utf-8")
            platform_audit.write_text(json.dumps({"front": {"canonical_public_host": "seoulmna.kr", "channel_role": "platform_front", "listing_market_host": "seoulmna.co.kr", "public_calculator_mount_base": "https://seoulmna.kr/_calc", "private_engine_visibility": "reverse_proxy_hidden_origin", "engine_origin": "https://calc.seoulmna.co.kr", "current_live_public_stack": "wordpress_astra_live"}, "completion_summary": {"front_platform_status": "policy_ready_live_confirmation_pending"}}, ensure_ascii=False), encoding="utf-8")
            surface_stack.write_text(json.dumps({"surfaces": {"kr": {"stack": "nextjs_vercel_front"}, "co": {"stack": "gnuboard_weaver_like"}}, "wordpress": {"live_applicability": {"decision": "sandbox_only"}, "candidate_package_slugs": ["astra"]}, "decisions": {"plugin_theme_strategy": "wordpress_assets_sandbox_only"}}, ensure_ascii=False), encoding="utf-8")
            private_proxy.write_text(json.dumps({"topology": {"main_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr", "public_mount_base": "https://seoulmna.kr/_calc", "private_engine_origin": "https://calc.seoulmna.co.kr"}, "decision": {"public_contract": "https://seoulmna.kr/_calc/*", "engine_visibility": "hidden_origin_only"}}, ensure_ascii=False), encoding="utf-8")
            wp_lab.write_text(json.dumps({"summary": {"package_count": 4, "downloaded_count": 4, "staging_ready_count": 4, "runtime_ready": False, "runtime_blockers": ["php_missing", "docker_missing"]}, "runtime": {"blockers": ["php_missing", "docker_missing"]}}, ensure_ascii=False), encoding="utf-8")
            wp_runtime.write_text(json.dumps({"summary": {"runtime_scaffold_ready": True, "docker_available": False, "local_bind_only": True}, "policy": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False), encoding="utf-8")
            wp_runtime_validation.write_text(json.dumps({"summary": {"runtime_scaffold_ready": True, "runtime_ready": False, "blockers": ["docker_missing"]}, "handoff": {"localhost_url": "http://127.0.0.1:18080"}}, ensure_ascii=False), encoding="utf-8")
            wp_assets.write_text(json.dumps({"summary": {"theme_ready": True, "plugin_ready": True}, "theme": {"slug": "seoulmna-platform-child"}, "plugin": {"slug": "seoulmna-platform-bridge", "public_mount_host": "seoulmna.kr", "public_mount_base": "https://seoulmna.kr/_calc", "lazy_iframe_policy": True}}, ensure_ascii=False), encoding="utf-8")
            wp_ia.write_text(json.dumps({"summary": {"page_count": 6, "service_page_count": 2, "lazy_gate_pages": ["yangdo", "permit"], "cta_only_pages": ["home", "knowledge"]}, "topology": {"platform_host": "seoulmna.kr", "public_mount": "https://seoulmna.kr/_calc/<type>?embed=1"}}, ensure_ascii=False), encoding="utf-8")
            wp_ux.write_text(json.dumps({"summary": {"page_count": 6, "issue_count": 0, "ux_ok": True, "service_pages_ok": True, "market_bridge_ok": True, "yangdo_recommendation_surface_ok": True}}, ensure_ascii=False), encoding="utf-8")
            wp_blueprints.write_text(json.dumps({"summary": {"blueprint_count": 6, "lazy_gate_pages": ["yangdo", "permit"], "cta_only_pages": ["home", "knowledge"], "navigation_ready": True}}, ensure_ascii=False), encoding="utf-8")
            wp_apply.write_text(json.dumps({"summary": {"page_step_count": 6, "cutover_ready": True, "service_page_count": 2}}, ensure_ascii=False), encoding="utf-8")
            wp_strategy.write_text(json.dumps({"current_live_stack": {"kr_host": "seoulmna.kr", "co_role": "listing_market_site"}, "runtime_decision": {"primary_runtime": "wordpress_astra_live", "support_runtime": "private_engine_behind_kr_reverse_proxy"}, "calculator_mount_decision": {"recommended_pattern": "cta_on_home_lazy_gate_on_service_page_private_runtime_on_kr", "private_engine_public_mount": "https://seoulmna.kr/_calc/<type>?embed=1", "recommended_by_page": {"listing_site_policy": "https://seoulmna.co.kr/ stays listing-focused and links back to seoulmna.kr service pages."}}, "plugin_stack": {"keep_live": ["astra", "rank-math"], "stage_first": ["seoulmna-platform-child"], "avoid_live_duplication": ["wordpress-seo"]}}, ensure_ascii=False), encoding="utf-8")
            astra_ref.write_text(json.dumps({"astra": {"theme_name": "Astra", "theme_version": "4.12.3"}, "decision": {"strategy": "reference_only_for_next_front", "usable_for_next_front": ["typography_scale_reference"]}}, ensure_ascii=False), encoding="utf-8")
            kr_cutover.write_text(json.dumps({"summary": {"cutover_ready": True, "service_page_count": 2, "traffic_gate_ok": True}, "topology": {"public_mount_base": "https://seoulmna.kr/_calc", "private_engine_origin": "https://calc.seoulmna.co.kr"}}, ensure_ascii=False), encoding="utf-8")
            kr_traffic.write_text(json.dumps({"decision": {"traffic_leak_blocked": True, "remaining_risks": []}, "live_probe": {"server_started": True, "all_routes_no_iframe": True}}, ensure_ascii=False), encoding="utf-8")
            kr_ready.write_text(json.dumps({"blocking_issues": [], "handoff": {"preview_deploy_ready": True, "next_actions": ["Run deploy_kr_platform_front_preview.py to create a preview deployment"]}}, ensure_ascii=False), encoding="utf-8")
            kr_preview.write_text(json.dumps({"handoff": {"preview_deployed": True, "preview_url": "https://preview.vercel.app"}}, ensure_ascii=False), encoding="utf-8")
            onboarding.write_text(json.dumps({"tenants": [], "channels": []}), encoding="utf-8")
            partner_flow.write_text(json.dumps({"ok": True, "activation_blockers": [], "handoff": {"activation_ready": True, "remaining_required_inputs": [], "resolved_inputs": []}}), encoding="utf-8")
            partner_preview.write_text(json.dumps({"recommended_path": {"scenario": "baseline", "remaining_required_inputs": [], "next_actions": []}}), encoding="utf-8")
            partner_alignment.write_text(json.dumps({"summary": {"ok": True, "baseline_matches_current": True, "recommended_clears_current": True}}), encoding="utf-8")
            partner_resolution.write_text(json.dumps({"summary": {"ok": True, "matches_preview_expected_remaining": True}}), encoding="utf-8")
            partner_snapshot.write_text(json.dumps({"summary": {"partner_tenant_count": 0, "ready_tenant_count": 0, "scenario_counts": {}}}), encoding="utf-8")
            partner_simulation.write_text(json.dumps({"summary": {"partner_count": 0, "baseline_ready_count": 0, "ready_after_simulation_count": 0, "newly_ready_count": 0, "all_ready_after_simulation": False}}), encoding="utf-8")
            yangdo_qa.write_text(json.dumps({"summary": {"scenario_count": 5, "passed_count": 5, "failed_count": 0, "qa_ok": True, "strict_profile_regression_ok": True, "fallback_regression_ok": True, "balance_exclusion_regression_ok": True, "assistive_precision_regression_ok": True, "summary_projection_regression_ok": True, "precision_counts": {"high": 2, "medium": 1, "assist": 1}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_precision.write_text(json.dumps({"summary": {"scenario_count": 6, "passed_count": 6, "failed_count": 0, "precision_ok": True, "high_precision_ok": True, "fallback_precision_ok": True, "balance_excluded_precision_ok": True, "assist_precision_ok": True, "summary_publication_ok": True, "detail_explainability_ok": True, "sector_groups": {"general": {"scenario_count": 5, "passed_count": 5, "failed_count": 0}}, "price_bands": {"mid_2_to_4_eok": {"scenario_count": 3, "passed_count": 3, "failed_count": 0}}, "response_tiers": {"summary": {"scenario_count": 1, "passed_count": 1, "failed_count": 0}, "detail": {"scenario_count": 1, "passed_count": 1, "failed_count": 0}}, "precision_counts": {"high": 2, "medium": 1, "assist": 1}}}, ensure_ascii=False), encoding="utf-8")
            yangdo_diversity.write_text(json.dumps({"summary": {"scenario_count": 7, "passed_count": 7, "failed_count": 0, "diversity_ok": True, "top1_stability_ok": True, "price_band_spread_ok": True, "focus_signature_spread_ok": True, "detail_projection_contract_ok": True, "precision_tier_spread_ok": True, "unique_listing_ok": True, "listing_bridge_ok": True, "listing_band_spread_ok": True, "cluster_concentration_ok": True, "top_rank_signature_concentration_ok": True, "price_band_concentration_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_contract.write_text(json.dumps({"summary": {"contract_ok": True, "summary_safe": True, "detail_explainable": True, "internal_debug_visible": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_bridge.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_slug": "/yangdo",
                            "platform_host": "seoulmna.kr",
                            "listing_host": "seoulmna.co.kr",
                            "market_bridge_ready": True,
                            "rental_ready": True,
                            "supported_precision_labels": ["우선 추천", "조건 유사", "보조 검토"],
                        },
                        "public_summary_contract": {
                            "fields": [
                                "display_low_eok",
                                "display_high_eok",
                                "recommendation_label",
                                "recommendation_focus",
                                "reasons",
                                "url",
                            ]
                        },
                        "detail_contract": {
                            "fields": ["precision_tier", "fit_summary", "matched_axes", "mismatch_flags"]
                        },
                        "market_bridge_policy": {"service_flow_policy": "public_summary_then_market_or_consult"},
                        "rental_packaging": {
                            "summary_offerings": ["yangdo_standard"],
                            "detail_offerings": ["yangdo_pro_detail", "yangdo_pro"],
                            "internal_offerings": ["seoul_internal"],
                            "summary_policy": "safe-summary",
                            "detail_policy": "detail-explainable",
                            "internal_policy": "internal-full",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_ux.write_text(
                json.dumps(
                    {
                        "summary": {
                            "packet_ready": True,
                            "service_surface_ready": True,
                            "market_bridge_ready": True,
                            "rental_exposure_ready": True,
                            "precision_ready": True,
                            "detail_explainability_ready": True,
                            "service_flow_policy": "public_summary_then_market_or_consult",
                        },
                        "public_summary_experience": {
                            "visible_fields": [
                                "display_low_eok",
                                "display_high_eok",
                                "recommendation_label",
                                "recommendation_focus",
                                "reasons",
                                "url",
                            ],
                            "cta_primary_label": "추천 매물 흐름 보기",
                            "cta_secondary_label": "상담형 상세 요청",
                        },
                        "detail_explainable_experience": {
                            "visible_fields": [
                                "precision_tier",
                                "fit_summary",
                                "matched_axes",
                                "mismatch_flags",
                            ]
                        },
                        "consult_detail_experience": {
                            "visible_fields": [
                                "precision_tier",
                                "fit_summary",
                                "matched_axes",
                                "mismatch_flags",
                            ]
                        },
                        "rental_exposure_matrix": {
                            "standard": {"offerings": ["yangdo_standard"]},
                            "pro_detail": {"offerings": ["yangdo_pro_detail"]},
                            "pro_consult": {"offerings": ["yangdo_pro"]},
                            "internal": {"offerings": ["seoul_internal"]},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            yangdo_alignment.write_text(json.dumps({"summary": {"alignment_ok": True, "issue_count": 0, "service_flow_policy_ok": True, "cta_labels_ok": True, "field_contract_ok": True, "offering_exposure_ok": True, "patent_handoff_ok": True, "contract_story_ok": True, "supported_labels_ok": True}}, ensure_ascii=False), encoding="utf-8")
            yangdo_service_copy.write_text(json.dumps({"summary": {"packet_ready": True, "service_copy_ready": True, "low_precision_consult_first_ready": True, "market_bridge_story_ready": True, "market_fit_interpretation_ready": True, "lane_stories_ready": True, "service_slug": "/yangdo", "platform_host": "seoulmna.kr", "listing_host": "seoulmna.co.kr", "precision_label_count": 3, "recommendation_offering_count": 3}, "hero": {"title": "가격 범위와 유사매물 추천을 함께 읽고, 실제 시장 확인과 상담으로 분기합니다."}, "cta_ladder": {"primary_market_bridge": {"label": "추천 매물 흐름 보기"}, "secondary_consult": {"label": "상담형 상세 요청"}}, "offering_matrix": {"summary_market_bridge": ["yangdo_standard"], "detail_explainable": ["yangdo_pro_detail"], "consult_assist": ["yangdo_pro"], "internal_full": ["seoul_internal"]}}, ensure_ascii=False), encoding="utf-8")
            rental_catalog.write_text(json.dumps({"summary": {"offering_count": 6, "standard_offering_count": 3, "pro_offering_count": 3, "combo_offering_count": 2, "yangdo_recommendation_offering_count": 3, "yangdo_recommendation_standard_count": 1, "yangdo_recommendation_detail_count": 2, "yangdo_recommendation_summary_bridge_count": 1, "yangdo_recommendation_detail_lane_count": 1, "yangdo_recommendation_consult_assist_count": 1, "internal_tenant_count": 2, "public_platform_host": "seoulmna.kr", "listing_market_host": "seoulmna.co.kr"}, "packaging": {"partner_rental": {"widget_standard": ["yangdo_standard"], "api_or_detail_pro": ["yangdo_pro_detail", "yangdo_pro"], "yangdo_recommendation": {"summary_offerings": ["yangdo_standard"], "detail_offerings": ["yangdo_pro_detail", "yangdo_pro"], "internal_offerings": ["seoul_internal"], "summary_policy": "safe-summary", "detail_policy": "detail-explainable", "package_matrix": {"summary_market_bridge": {"offering_ids": ["yangdo_standard"]}, "detail_explainable": {"offering_ids": ["yangdo_pro_detail"]}, "consult_assist": {"offering_ids": ["yangdo_pro"]}, "internal_full": {"offering_ids": ["seoul_internal"]}}}}}}, ensure_ascii=False), encoding="utf-8")
            improvement_loop.write_text(json.dumps({"summary": {"immediate_blocker_count": 0, "structural_improvement_count": 2, "patent_hardening_count": 3, "commercialization_gap_count": 2, "top_action_count": 2}, "top_next_actions": [{"priority": 2, "title": "Keep calculators off the initial .kr render path", "action": "Do not inline iframes on the homepage."}]}, ensure_ascii=False), encoding="utf-8")
            json_path = base / "packet.json"
            md_path = base / "packet.md"
            argv = [
                "generate_operations_packet.py",
                "--readiness", str(readiness),
                "--release", str(release),
                "--risk-map", str(risk),
                "--attorney", str(attorney),
                "--platform-front-audit", str(platform_audit),
                "--surface-stack-audit", str(surface_stack),
                "--private-engine-proxy-spec", str(private_proxy),
                "--wp-surface-lab", str(wp_lab),
                "--wp-surface-lab-runtime", str(wp_runtime),
                "--wp-surface-lab-runtime-validation", str(wp_runtime_validation),
                "--wp-platform-assets", str(wp_assets),
                "--wordpress-platform-ia", str(wp_ia),
                "--wordpress-platform-ux-audit", str(wp_ux),
                "--wp-platform-blueprints", str(wp_blueprints),
                "--wordpress-staging-apply-plan", str(wp_apply),
                "--wordpress-platform-strategy", str(wp_strategy),
                "--astra-design-reference", str(astra_ref),
                "--kr-reverse-proxy-cutover", str(kr_cutover),
                "--kr-traffic-gate-audit", str(kr_traffic),
                "--kr-deploy-readiness", str(kr_ready),
                "--kr-preview-deploy", str(kr_preview),
                "--onboarding-validation", str(onboarding),
                "--partner-flow", str(partner_flow),
                "--partner-preview", str(partner_preview),
                "--partner-preview-alignment", str(partner_alignment),
                "--partner-resolution", str(partner_resolution),
                "--partner-input-snapshot", str(partner_snapshot),
                "--partner-simulation-matrix", str(partner_simulation),
                "--yangdo-recommendation-qa", str(yangdo_qa),
                "--yangdo-recommendation-precision-matrix", str(yangdo_precision),
                "--yangdo-recommendation-diversity-audit", str(yangdo_diversity),
                "--yangdo-recommendation-contract-audit", str(yangdo_contract),
                "--yangdo-recommendation-bridge-packet", str(yangdo_bridge),
                "--yangdo-recommendation-ux-packet", str(yangdo_ux),
                "--yangdo-recommendation-alignment-audit", str(yangdo_alignment),
                "--yangdo-service-copy-packet", str(yangdo_service_copy),
                "--widget-rental-catalog", str(rental_catalog),
                "--program-improvement-loop", str(improvement_loop),
                "--json", str(json_path),
                "--md", str(md_path),
            ]
            with patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["go_live"]["release_ready"])
            self.assertEqual(payload["decisions"]["seoul_live_decision"], "ready")
            self.assertEqual(payload["decisions"]["kr_platform_decision"], "wordpress_live_path_ready")
            self.assertEqual(payload["decisions"]["kr_wordpress_platform_decision"], "wordpress_live_path_ready")
            self.assertEqual(payload["decisions"]["kr_next_lane_decision"], "preview_deployed")
            self.assertEqual(payload["decisions"]["wp_plugin_decision"], "sandbox_ready_runtime_missing")
            self.assertEqual(payload["decisions"]["wp_runtime_decision"], "scaffold_ready_runtime_missing")
            self.assertTrue(payload["decisions"]["kr_traffic_gate_ok"])
            self.assertEqual(payload["topology"]["listing_market_host"], "seoulmna.co.kr")
            self.assertEqual(payload["summaries"]["wp_platform_assets"]["plugin_slug"], "seoulmna-platform-bridge")
            self.assertEqual(payload["summaries"]["widget_rental_catalog"]["standard_offering_count"], 3)
            self.assertEqual(payload["summaries"]["widget_rental_catalog"]["yangdo_recommendation_offering_count"], 3)
            self.assertEqual(payload["summaries"]["widget_rental_catalog"]["yangdo_recommendation_summary"], ["yangdo_standard"])
            self.assertEqual(payload["summaries"]["widget_rental_catalog"]["yangdo_recommendation_detail"], ["yangdo_pro_detail", "yangdo_pro"])
            self.assertEqual(payload["summaries"]["program_improvement_loop"]["top_action_count"], 2)
            self.assertEqual(payload["summaries"]["wordpress_platform_ia"]["service_page_count"], 2)
            self.assertEqual(payload["summaries"]["wp_platform_blueprints"]["blueprint_count"], 6)
            self.assertEqual(payload["summaries"]["wordpress_staging_apply_plan"]["page_step_count"], 6)
            self.assertEqual(payload["summaries"]["wordpress_platform_strategy"]["recommended_pattern"], "cta_on_home_lazy_gate_on_service_page_private_runtime_on_kr")
            self.assertEqual(payload["decisions"]["wordpress_ia_decision"], "service_ia_ready")
            self.assertEqual(payload["decisions"]["reverse_proxy_cutover_decision"], "cutover_ready")
            self.assertEqual(payload["summaries"]["partner"]["preview_recommended_scenario"], "baseline")
            self.assertEqual(payload["decisions"]["partner_fastest_path_scenario"], "baseline")
            self.assertTrue(payload["decisions"]["partner_fastest_path_ready"])
            self.assertTrue(payload["decisions"]["partner_preview_alignment_ok"])
            self.assertFalse(payload["decisions"]["partner_resolution_actionable"])
            self.assertEqual(payload["decisions"]["partner_input_snapshot_ready_count"], 0)
            self.assertEqual(payload["decisions"]["partner_simulation_ready_count"], 0)
            self.assertFalse(payload["decisions"]["partner_simulation_all_ready"])
            self.assertFalse(payload["decisions"]["partner_uniform_required_inputs"])
            self.assertFalse(payload["decisions"]["partner_flow_scope_registered"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_qa_ok"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_precision_ok"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_diversity_ok"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_concentration_ok"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_contract_ok"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_bridge_ready"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_ux_ready"])
            self.assertTrue(payload["decisions"]["yangdo_recommendation_alignment_ok"])
            self.assertTrue(payload["decisions"]["yangdo_service_copy_ready"])
            self.assertTrue(payload["summaries"]["yangdo_service_copy"]["market_fit_interpretation_ready"])
            self.assertTrue(payload["summaries"]["yangdo_service_copy"]["lane_stories_ready"])
            self.assertTrue(payload["summaries"]["yangdo_recommendation_diversity_audit"]["top_rank_signature_concentration_ok"])
            self.assertEqual(payload["summaries"]["kr_platform"]["preview_url"], "https://preview.vercel.app")
            self.assertEqual(payload["required_inputs"]["partner_fastest_path"], [])
            self.assertEqual(payload["required_inputs"]["partner_common"], [])
            self.assertEqual(payload["summaries"]["yangdo_recommendation_diversity_audit"]["scenario_count"], 7)
            self.assertEqual(payload["summaries"]["yangdo_recommendation_ux"]["public_primary_cta"], "추천 매물 흐름 보기")
            self.assertEqual(payload["summaries"]["yangdo_recommendation_ux"]["public_secondary_cta"], "상담형 상세 요청")
            self.assertEqual(payload["summaries"]["yangdo_recommendation_ux"]["detail_explainable_fields"], ["precision_tier", "fit_summary", "matched_axes", "mismatch_flags"])
            self.assertEqual(payload["summaries"]["yangdo_recommendation_ux"]["pro_detail_offerings"], ["yangdo_pro_detail"])
            self.assertEqual(payload["summaries"]["yangdo_recommendation_ux"]["pro_consult_offerings"], ["yangdo_pro"])
            self.assertTrue(payload["summaries"]["yangdo_recommendation_alignment"]["alignment_ok"])
            self.assertTrue(payload["summaries"]["yangdo_service_copy"]["packet_ready"])
            self.assertEqual(payload["summaries"]["yangdo_service_copy"]["detail_explainable_offerings"], ["yangdo_pro_detail"])
            self.assertEqual(payload["summaries"]["yangdo_service_copy"]["consult_assist_offerings"], ["yangdo_pro"])
            self.assertEqual(payload["summaries"]["yangdo_service_copy"]["hero_title"], "가격 범위와 유사매물 추천을 함께 읽고, 실제 시장 확인과 상담으로 분기합니다.")
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn("Operations Packet", md_text)
            self.assertIn("Topology", md_text)
            self.assertIn("KR Platform", md_text)
            self.assertIn("Surface Stack", md_text)
            self.assertIn("WordPress Lab", md_text)
            self.assertIn("WordPress Lab Runtime", md_text)
            self.assertIn("WordPress Platform Assets", md_text)
            self.assertIn("WordPress Platform IA", md_text)
            self.assertIn("WordPress Blueprints", md_text)
            self.assertIn("WordPress Staging Apply Plan", md_text)
            self.assertIn("Yangdo Recommendation QA", md_text)
            self.assertIn("Yangdo Recommendation Diversity", md_text)
            self.assertIn("Yangdo Recommendation UX", md_text)
            self.assertIn("Yangdo Recommendation Alignment", md_text)
            self.assertIn("Widget Rental Catalog", md_text)
            self.assertIn("yangdo_recommendation_summary", md_text)
            self.assertIn("WordPress Platform Strategy", md_text)
            self.assertIn("Private Engine Proxy", md_text)
            self.assertIn("Astra Reference", md_text)
            self.assertIn("KR Reverse Proxy Cutover", md_text)
            self.assertIn("KR Traffic Gate", md_text)
            self.assertIn("Partner Checklists", md_text)
            self.assertIn("Seoul Live Checklist", md_text)
            self.assertIn("Partner Decision", md_text)

    def test_snapshot_rows_override_partner_required_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            readiness = base / "readiness.json"
            release = base / "release.json"
            risk = base / "risk.json"
            attorney = base / "attorney.json"
            onboarding = base / "onboarding.json"
            partner_flow = base / "partner_flow.json"
            partner_preview = base / "partner_preview.json"
            partner_alignment = base / "partner_alignment.json"
            partner_resolution = base / "partner_resolution.json"
            partner_snapshot = base / "partner_snapshot.json"

            readiness.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"release_ready": True}}), encoding="utf-8")
            release.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"runtime_verified": True}, "artifact_summary": {}}), encoding="utf-8")
            risk.write_text(json.dumps({"ok": True, "business_core_status": "green", "run_summary": {"ran_tests": 1, "issue_count": 0}}), encoding="utf-8")
            attorney.write_text(json.dumps({"tracks": [{}], "executive_summary": {"independent_systems": ["yangdo", "permit"]}}), encoding="utf-8")
            onboarding.write_text(json.dumps({"tenants": [{"tenant_id": "partner_yangdo_standard", "activation_ready": False, "allowed_systems": ["yangdo"], "activation_blockers": ["missing_api_key_value"]}, {"tenant_id": "partner_permit_standard", "activation_ready": False, "allowed_systems": ["permit"], "activation_blockers": ["missing_api_key_value"]}], "channels": [{"channel_id": "partner_yangdo_template", "default_tenant_id": "partner_yangdo_standard", "activation_ready": False}, {"channel_id": "partner_permit_template", "default_tenant_id": "partner_permit_standard", "activation_ready": False}]}), encoding="utf-8")
            partner_flow.write_text(json.dumps({"ok": False, "activation_blockers": ["missing_api_key_value"], "handoff": {"activation_ready": False, "remaining_required_inputs": ["partner_api_key"], "resolved_inputs": []}}), encoding="utf-8")
            partner_preview.write_text(json.dumps({"recommended_path": {"scenario": "baseline", "remaining_required_inputs": ["partner_api_key"], "next_actions": []}}), encoding="utf-8")
            partner_alignment.write_text(json.dumps({"summary": {"ok": True}}), encoding="utf-8")
            partner_resolution.write_text(json.dumps({"summary": {"ok": True}}), encoding="utf-8")
            partner_snapshot.write_text(json.dumps({"summary": {"partner_tenant_count": 2, "ready_tenant_count": 0, "scenario_counts": {"baseline": 2}}, "partners": [{"tenant_id": "partner_yangdo_standard", "resolution_remaining_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"]}, {"tenant_id": "partner_permit_standard", "resolution_remaining_required_inputs": ["partner_proof_url", "partner_api_key", "partner_data_source_approval"]}]}), encoding="utf-8")

            packet = build_operations_packet(
                readiness_path=readiness,
                release_path=release,
                risk_map_path=risk,
                attorney_path=attorney,
                onboarding_validation_path=onboarding,
                partner_flow_path=partner_flow,
                partner_preview_path=partner_preview,
                partner_preview_alignment_path=partner_alignment,
                partner_resolution_path=partner_resolution,
                partner_input_snapshot_path=partner_snapshot,
            )

            self.assertEqual(packet["required_inputs"]["partner_aggregate"]["partner_data_source_approval"], 2)
            self.assertEqual(
                packet["summaries"]["partner"]["checklists"][0]["required_inputs"],
                ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
            )
            self.assertEqual(packet["summaries"]["partner"]["checklists"][0]["input_source"], "snapshot")
            self.assertEqual(
                packet["required_inputs"]["partner_common"],
                ["partner_proof_url", "partner_api_key", "partner_data_source_approval"],
            )
            self.assertTrue(packet["decisions"]["partner_uniform_required_inputs"])

    def test_permit_alignment_summary_is_projected_when_provided(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            readiness = base / "readiness.json"
            release = base / "release.json"
            risk = base / "risk.json"
            attorney = base / "attorney.json"
            permit_alignment = base / "permit_alignment.json"

            readiness.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"release_ready": True}}), encoding="utf-8")
            release.write_text(json.dumps({"ok": True, "blocking_issues": [], "handoff": {"runtime_verified": True}, "artifact_summary": {}}), encoding="utf-8")
            risk.write_text(json.dumps({"ok": True, "business_core_status": "green", "run_summary": {"ran_tests": 1, "issue_count": 0}}), encoding="utf-8")
            attorney.write_text(json.dumps({"tracks": [{"track_id": "B"}], "executive_summary": {"independent_systems": ["yangdo", "permit"]}}, ensure_ascii=False), encoding="utf-8")
            permit_alignment.write_text(
                json.dumps(
                    {
                        "summary": {
                            "alignment_ok": True,
                            "issue_count": 0,
                            "cta_contract_ok": True,
                            "proof_point_contract_ok": True,
                            "service_story_ok": True,
                            "rental_positioning_ok": True,
                            "patent_handoff_ok": True,
                            "permit_offering_count": 3,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            packet = build_operations_packet(
                readiness_path=readiness,
                release_path=release,
                risk_map_path=risk,
                attorney_path=attorney,
                permit_service_alignment_audit_path=permit_alignment,
            )

            self.assertTrue(packet["decisions"]["permit_service_alignment_ok"])
            self.assertEqual(packet["summaries"]["permit_service_alignment"]["issue_count"], 0)
            self.assertTrue(packet["summaries"]["permit_service_alignment"]["cta_contract_ok"])
            self.assertEqual(packet["summaries"]["permit_service_alignment"]["permit_offering_count"], 3)


if __name__ == "__main__":
    unittest.main()
