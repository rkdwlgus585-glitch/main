import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_operations_packet import build_operations_packet, main


class GenerateOperationsPacketTests(unittest.TestCase):
    def test_build_operations_packet_aggregates_sources(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            paths = {name: base / f"{name}.json" for name in [
                'readiness', 'release', 'risk', 'attorney', 'platform_audit', 'surface_stack', 'private_proxy',
                'wp_lab', 'wp_runtime', 'wp_runtime_validation', 'wp_assets', 'wp_ia', 'wp_ux', 'wp_blueprints',
                'wp_apply', 'wp_strategy', 'astra_ref', 'kr_cutover', 'kr_traffic', 'kr_ready', 'kr_preview',
                'onboarding', 'partner_flow', 'partner_preview', 'partner_alignment', 'partner_resolution',
                'partner_snapshot', 'partner_simulation', 'yangdo_qa', 'yangdo_precision', 'yangdo_diversity',
                'yangdo_special_sector', 'yangdo_contract', 'yangdo_bridge', 'yangdo_ux', 'yangdo_alignment', 'yangdo_zero_display', 'yangdo_service_copy',
                'permit_service_copy', 'permit_service_alignment', 'permit_rental_lane', 'permit_service_ux',
                'permit_public_contract', 'permit_prompt_case_binding', 'permit_critical_prompt_surface', 'permit_partner_binding_parity', 'permit_partner_binding_observability', 'permit_thinking_prompt_bundle', 'permit_next_action_brainstorm', 'permit_runtime_reasoning_binding', 'permit_law_case_coverage', 'partner_input_handoff', 'partner_input_operator_flow', 'rental_catalog', 'improvement_loop', 'ai_first_principles', 'external_masterplan_alignment', 'system_split_first_principles', 'next_execution', 'yangdo_next_action_brainstorm', 'yangdo_public_language_audit', 'founder_execution_chain'
            ]}

            def write(name: str, payload: dict):
                paths[name].write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')

            write('readiness', {'ok': True, 'blocking_issues': [], 'handoff': {'release_ready': True, 'next_actions': ['release go']}})
            write('release', {'ok': False, 'blocking_issues': ['confirm_live_missing'], 'handoff': {'runtime_verified': False}, 'artifact_summary': {'runtime': {'blocking_issues': ['runtime_failed']}}})
            write('risk', {'ok': True, 'business_core_status': 'green', 'run_summary': {'ran_tests': 10, 'issue_count': 0}})
            write('attorney', {'tracks': [{}, {}], 'executive_summary': {'independent_systems': ['yangdo', 'permit'], 'claim_strategy': ['A/B split'], 'attorney_handoff': ['independent filings']}})
            write('platform_audit', {'front': {'canonical_public_host': 'seoulmna.kr', 'channel_role': 'platform_front', 'listing_market_host': 'seoulmna.co.kr', 'public_calculator_mount_base': 'https://seoulmna.kr/_calc', 'private_engine_visibility': 'reverse_proxy_hidden_origin', 'engine_origin': 'https://calc.seoulmna.co.kr', 'current_live_public_stack': 'wordpress_astra_live'}, 'completion_summary': {'front_platform_status': 'policy_ready_live_confirmation_pending'}})
            write('surface_stack', {'surfaces': {'kr': {'stack': 'wordpress_astra_live'}, 'co': {'stack': 'gnuboard_weaver_like'}}, 'wordpress': {'live_applicability': {'decision': 'wordpress_first_live'}}, 'decisions': {'plugin_theme_strategy': 'wordpress_assets_live_path'}})
            write('private_proxy', {'topology': {'main_platform_host': 'seoulmna.kr', 'listing_market_host': 'seoulmna.co.kr', 'public_mount_base': 'https://seoulmna.kr/_calc'}, 'decision': {'public_contract': 'https://seoulmna.kr/_calc/*', 'engine_visibility': 'reverse_proxy_hidden_origin'}})
            write('wp_lab', {'summary': {'package_count': 4}})
            write('wp_runtime', {'summary': {'runtime_scaffold_ready': True}, 'policy': {'localhost_url': 'http://127.0.0.1:18080'}})
            write('wp_runtime_validation', {'summary': {'runtime_scaffold_ready': True, 'runtime_ready': True, 'blockers': []}, 'handoff': {'localhost_url': 'http://127.0.0.1:18080'}})
            write('wp_assets', {'summary': {'theme_ready': True, 'plugin_ready': True}, 'theme': {'slug': 'seoulmna-platform-child'}, 'plugin': {'slug': 'seoulmna-platform-bridge', 'public_mount_host': 'seoulmna.kr'}})
            write('wp_ia', {'summary': {'page_count': 6}, 'topology': {'platform_host': 'seoulmna.kr'}})
            write('wp_ux', {'summary': {'ux_ok': True, 'service_pages_ok': True, 'market_bridge_ok': True, 'yangdo_recommendation_surface_ok': True}})
            write('wp_blueprints', {'summary': {'blueprint_count': 6}})
            write('wp_apply', {'summary': {'page_step_count': 6}})
            write('wp_strategy', {'runtime_decision': {'primary_runtime': 'wordpress_astra_live'}, 'calculator_mount_decision': {'private_engine_public_mount': 'https://seoulmna.kr/_calc/<type>?embed=1'}})
            write('astra_ref', {'decision': {'strategy': 'wordpress_child_theme_live'}})
            write('kr_cutover', {'summary': {'cutover_ready': True, 'traffic_gate_ok': True}, 'topology': {'public_mount_base': 'https://seoulmna.kr/_calc'}})
            write('kr_traffic', {'decision': {'traffic_leak_blocked': True}, 'live_probe': {'all_routes_no_iframe': True}})
            write('kr_ready', {'blocking_issues': []})
            write('kr_preview', {'handoff': {'preview_deployed': False}})
            write('onboarding', {'tenants': [{'tenant_id': 'partner_demo', 'activation_ready': False}], 'channels': [{'channel_id': 'partner_demo', 'activation_ready': False}]})
            write('partner_flow', {'ok': False, 'activation_blockers': ['missing_source_proof_url_pending', 'missing_api_key_value'], 'handoff': {'activation_ready': False, 'next_actions': ['Provide partner contract proof URL'], 'remaining_required_inputs': ['partner_proof_url', 'partner_api_key'], 'resolved_inputs': []}})
            write('partner_preview', {'recommended_path': {'scenario': 'proof_and_key', 'remaining_required_inputs': ['partner_data_source_approval']}})
            write('partner_alignment', {'summary': {'ok': True}})
            write('partner_resolution', {'summary': {'ok': True, 'matches_preview_expected_remaining': True}})
            write('partner_snapshot', {'summary': {'partner_tenant_count': 2, 'ready_tenant_count': 1, 'scenario_counts': {'baseline': 1}}})
            write('partner_simulation', {'summary': {'all_ready_after_simulation': True, 'ready_after_simulation_count': 2}})
            write('yangdo_qa', {'summary': {'qa_ok': True}})
            write('yangdo_precision', {'summary': {'precision_ok': True, 'detail_explainability_ok': True}})
            write('yangdo_diversity', {'summary': {'diversity_ok': True, 'cluster_concentration_ok': True, 'top_rank_signature_concentration_ok': True, 'price_band_concentration_ok': True}})
            write('yangdo_special_sector', {'summary': {'packet_ready': True, 'special_sector_count': 3, 'sector_ready_count': 3, 'publication_safety_ok': True, 'pricing_watch_required': True, 'precision_green': True, 'diversity_green': True, 'contract_green': True, 'expansion_candidate_count': 1, 'expansion_candidates': [{'sector': '소방', 'reorg_mode': '포괄', 'reason': 'backlog'}]}})
            write('yangdo_contract', {'summary': {'contract_ok': True}})
            write('yangdo_bridge', {'summary': {'packet_ready': True, 'service_slug': '/yangdo', 'platform_host': 'seoulmna.kr', 'listing_host': 'seoulmna.co.kr'}, 'public_summary_contract': {'primary_cta': {'label': '추천 매물 흐름 보기'}, 'secondary_cta': {'label': '상담형 상세 요청'}}, 'detail_contract': {'fields': ['precision_tier'], 'operator_only_fields': ['recommendation_score']}, 'market_bridge_policy': {'service_flow_policy': 'public_summary_then_market_or_consult'}, 'rental_packaging': {'summary_offerings': ['yangdo_standard'], 'detail_offerings': ['yangdo_pro_detail'], 'summary_policy': 'safe-summary', 'detail_policy': 'detail-explainable', 'internal_policy': 'internal-full'}})
            write('yangdo_ux', {'summary': {'packet_ready': True, 'service_surface_ready': True, 'market_bridge_ready': True, 'rental_exposure_ready': True, 'service_flow_policy': 'public_summary_then_market_or_consult'}, 'public_summary_experience': {'allowed_offerings': ['yangdo_standard'], 'cta_primary_label': '추천 매물 흐름 보기'}, 'detail_explainable_experience': {'allowed_offerings': ['yangdo_pro_detail']}, 'consult_detail_experience': {'allowed_offerings': ['yangdo_pro']}})
            write('yangdo_alignment', {'summary': {'alignment_ok': True}})
            write('yangdo_zero_display', {'summary': {'zero_display_guard_ok': True, 'zero_display_total': 3, 'selected_lane_ok': True, 'runtime_ready': True, 'contract_policy_ok': True, 'market_bridge_route_ok': True, 'consult_first_ready': True, 'zero_policy_ready': True, 'market_cta_ready': True, 'consult_lane_ready': True, 'patent_hook_ready': True}})
            write('yangdo_service_copy', {'summary': {'packet_ready': True, 'service_copy_ready': True, 'market_bridge_story_ready': True, 'market_fit_interpretation_ready': True, 'lane_stories_ready': True, 'service_slug': '/yangdo', 'platform_host': 'seoulmna.kr'}, 'hero': {'title': '양도가 산정과 유사매물 추천'}, 'cta_ladder': {'primary_market_bridge': {'label': '추천 매물 흐름 보기'}, 'secondary_consult': {'label': '상담형 상세 요청'}}, 'offering_matrix': {'summary_market_bridge': ['yangdo_standard'], 'detail_explainable': ['yangdo_pro_detail'], 'consult_assist': ['yangdo_pro'], 'internal_full': ['seoul_internal']}})
            write('permit_service_copy', {'summary': {'packet_ready': True, 'service_copy_ready': True, 'checklist_story_ready': True, 'manual_review_story_ready': True, 'document_story_ready': True, 'lane_ladder_ready': True, 'service_flow_ready': True, 'service_slug': '/permit', 'platform_host': 'seoulmna.kr'}, 'hero': {'title': 'AI 인허가 사전검토'}, 'cta_ladder': {'primary_self_check': {'label': '사전검토 시작'}, 'secondary_consult': {'label': '수동 검토 요청'}, 'supporting_knowledge': {'label': '등록기준 안내 보기'}}, 'lane_ladder': {'summary_self_check': {'offering_ids': ['permit_standard'], 'upgrade_target': 'detail_checklist'}, 'detail_checklist': {'offering_ids': ['permit_pro'], 'upgrade_target': 'manual_review_assist'}, 'manual_review_assist': {'offering_ids': ['permit_pro_assist'], 'upgrade_target': 'internal_full'}}, 'offering_matrix': {'summary_self_check': ['permit_standard'], 'detail_checklist': ['permit_pro'], 'manual_review_assist': ['permit_pro_assist'], 'internal_full': []}})
            write('permit_service_alignment', {'summary': {'alignment_ok': True, 'service_story_ok': True, 'lane_positioning_ok': True, 'rental_positioning_ok': True, 'patent_handoff_ok': True, 'permit_offering_count': 3}})
            write('permit_rental_lane', {'summary': {'packet_ready': True, 'commercial_story_ready': True, 'detail_checklist_lane_ready': True, 'manual_review_assist_lane_ready': True}, 'lane_matrix': {'summary_self_check': {'offerings': ['permit_standard']}, 'detail_checklist': {'offerings': ['permit_pro']}, 'manual_review_assist': {'offerings': ['permit_pro_assist']}}})
            write('permit_service_ux', {'summary': {'packet_ready': True, 'service_surface_ready': True, 'lane_exposure_ready': True, 'alignment_ready': True, 'service_flow_policy': 'public_summary_then_checklist_or_manual_review'}, 'public_summary_experience': {'allowed_offerings': ['permit_standard'], 'cta_primary_label': '사전검토 시작'}, 'detail_checklist_experience': {'allowed_offerings': ['permit_pro'], 'cta_primary_label': '상세 체크리스트 보기'}, 'manual_review_assist_experience': {'allowed_offerings': ['permit_pro_assist'], 'cta_primary_label': '수동 검토 요청'}})
            write('permit_public_contract', {'summary': {'contract_ok': True, 'public_summary_only_ok': True, 'detail_checklist_contract_ok': True, 'assist_contract_ok': True, 'internal_visibility_ok': True, 'offering_exposure_ok': True, 'patent_handoff_ok': True}})
            write('permit_prompt_case_binding', {'summary': {'packet_ready': True, 'lane_id': 'prompt_case_binding', 'founder_lane_match': True, 'prompt_doc_ready': True, 'preset_ready': True, 'story_ready': True, 'operator_demo_ready': True, 'operator_jump_table_ready': True, 'representative_family_total': 2, 'representative_case_total': 4, 'manual_review_case_total': 1}})
            write('permit_critical_prompt_surface', {'summary': {'packet_ready': True, 'lane_id': 'runtime_reasoning_guard', 'lane_title': 'runtime reasoning guard', 'operator_surface_ready': True, 'release_surface_ready': True, 'founder_lane_match': True, 'alignment_ok': True, 'service_copy_ready': True, 'service_ux_ready': True, 'prompt_case_binding_ready': True, 'operator_jump_table_ready': True}})
            write('permit_partner_binding_parity', {'summary': {'packet_ready': True, 'family_total': 2, 'detail_checklist_family_total': 1, 'manual_review_family_total': 1, 'public_contract_ok': True, 'offering_exposure_ok': True, 'partner_surface_ready': True}})
            write('permit_partner_binding_observability', {'summary': {'observability_ready': True, 'expected_family_total': 2, 'widget_binding_family_total': 2, 'api_binding_family_total': 2, 'partner_binding_surface_ready': True, 'widget_missing_family_total': 0, 'api_missing_family_total': 0, 'widget_extra_family_total': 0, 'api_extra_family_total': 0}})
            write('permit_thinking_prompt_bundle', {'summary': {'packet_ready': True, 'lane_id': 'runtime_reasoning_guard', 'prompt_doc_ready': True, 'runtime_target_ready': True, 'release_target_ready': True, 'operator_target_ready': True, 'founder_transition_context_ready': True}})
            write('permit_next_action_brainstorm', {'summary': {'execution_lane': 'runtime_reasoning_guard', 'parallel_lane': 'surface_drift_digest', 'prompt_doc_ready': True, 'review_reason_decision_ladder_ready': True, 'partner_binding_parity_ready': True, 'runtime_critical_prompt_surface_ready': True}, 'current_execution_lane': {'id': 'runtime_reasoning_guard'}, 'parallel_brainstorm_lane': {'id': 'surface_drift_digest'}})
            write('permit_runtime_reasoning_binding', {'summary': {'packet_ready': True, 'lane_id': 'runtime_reasoning_guard', 'expected_lane_id': 'runtime_reasoning_guard', 'runtime_binding_ok': True, 'service_binding_ok': True, 'operator_binding_ok': True, 'release_binding_ok': True, 'cta_split_ok': True, 'offering_split_ok': True, 'issue_count': 0}})
            write('permit_law_case_coverage', {'summary': {'packet_ready': True, 'law_basis_coverage_ok': True, 'criteria_coverage_ok': True, 'provenance_ok': True, 'exception_tracking_ready': True, 'case_goldset_ready': True, 'story_surface_ready': True, 'prompt_binding_ready': True, 'real_industry_total': 195, 'pending_industry_total': 0, 'manual_scope_override_total': 2, 'family_total': 6, 'case_total': 36, 'manual_review_case_total': 6, 'blocker_count': 0}})
            write('partner_input_handoff', {'summary': {'partner_count': 2, 'uniform_required_inputs': True, 'common_required_inputs': ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'], 'ready_after_recommended_injection': True, 'ready_after_recommended_injection_count': 2, 'copy_paste_ready': True}})
            write('partner_input_operator_flow', {'summary': {'packet_ready': True, 'partner_count': 2, 'copy_paste_ready': True, 'common_required_inputs': ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'], 'ready_after_recommended_injection': True, 'recommended_sequence': ['simulate_partner_input_injection', 'run_partner_onboarding_flow_dry_run', 'run_partner_onboarding_flow_apply']}})
            write('rental_catalog', {'summary': {'offering_count': 9, 'permit_offering_count': 6, 'public_platform_host': 'seoulmna.kr', 'listing_market_host': 'seoulmna.co.kr'}, 'packaging': {'partner_rental': {'widget_standard': ['yangdo_standard', 'permit_standard'], 'api_or_detail_pro': ['yangdo_pro_detail', 'yangdo_pro', 'permit_pro', 'permit_pro_assist'], 'yangdo_recommendation': {'summary_market_bridge': [], 'detail_explainable': [], 'consult_assist': []}}}})
            write('improvement_loop', {'summary': {'immediate_blocker_count': 3, 'top_action_count': 4}})
            write('ai_first_principles', {'summary': {'packet_ready': True, 'blocking_issue_count': 1, 'current_bottleneck': 'public/private publish 분기', 'next_experiment_count': 3}})
            write('external_masterplan_alignment', {'summary': {'packet_ready': True, 'alignment_ok': True, 'source_directive_count': 10, 'missing_count': 0, 'missing_keys': []}})
            write('system_split_first_principles', {'summary': {'packet_ready': True, 'platform_ready': True, 'yangdo_ready': True, 'permit_ready': True, 'prompt_count': 3}})
            write('next_execution', {'summary': {'packet_ready': True, 'selected_track': 'yangdo', 'selected_lane_id': 'zero_display_recovery_guard', 'execution_ready': True, 'founder_selected_matches_primary': False}, 'founder_mode': {'primary_system': 'permit', 'primary_lane_id': 'prompt_case_binding'}, 'selected_execution': {'bottleneck': '추천 0건 fallback 계약 고정', 'success_criteria': ['zero_display_guard_ok'], 'verification_commands': ['py -3 H:\\auto\\scripts\\generate_yangdo_zero_display_recovery_audit.py'], 'next_after_completion': ['detail lane 강화'], 'selected_focus': {'track': 'yangdo', 'lane_id': 'zero_display_recovery_guard'}}})
            write('yangdo_next_action_brainstorm', {'summary': {'all_green': True, 'execution_lane': 'prompt_loop_operationalization', 'parallel_lane': '', 'autoloop_ready': True, 'zero_display_guard_ready': True, 'public_language_ready': True, 'public_language_remaining_phrase_count': 0}, 'current_execution_lane': {'id': 'prompt_loop_operationalization'}, 'parallel_brainstorm_lane': {}})
            write('yangdo_public_language_audit', {'summary': {'packet_ready': True, 'public_language_ready': True, 'remaining_phrase_count': 0, 'jargon_total': 0}})
            write('founder_execution_chain', {'summary': {'overall_ok': True, 'focus_matches_execution': True, 'founder_successor_transition': True, 'focus_selected_track': 'permit', 'focus_selected_lane_id': 'partner_binding_parity', 'execution_selected_track': 'permit', 'execution_selected_lane_id': 'partner_binding_parity'}})

            packet = build_operations_packet(
                readiness_path=paths['readiness'],
                release_path=paths['release'],
                risk_map_path=paths['risk'],
                attorney_path=paths['attorney'],
                platform_front_audit_path=paths['platform_audit'],
                surface_stack_audit_path=paths['surface_stack'],
                private_engine_proxy_spec_path=paths['private_proxy'],
                wp_surface_lab_path=paths['wp_lab'],
                wp_surface_lab_runtime_path=paths['wp_runtime'],
                wp_surface_lab_runtime_validation_path=paths['wp_runtime_validation'],
                wp_platform_assets_path=paths['wp_assets'],
                wordpress_platform_ia_path=paths['wp_ia'],
                wordpress_platform_ux_audit_path=paths['wp_ux'],
                wp_platform_blueprints_path=paths['wp_blueprints'],
                wordpress_staging_apply_plan_path=paths['wp_apply'],
                wordpress_platform_strategy_path=paths['wp_strategy'],
                astra_design_reference_path=paths['astra_ref'],
                kr_reverse_proxy_cutover_path=paths['kr_cutover'],
                kr_traffic_gate_audit_path=paths['kr_traffic'],
                kr_deploy_readiness_path=paths['kr_ready'],
                kr_preview_deploy_path=paths['kr_preview'],
                onboarding_validation_path=paths['onboarding'],
                partner_flow_path=paths['partner_flow'],
                partner_preview_path=paths['partner_preview'],
                partner_preview_alignment_path=paths['partner_alignment'],
                partner_resolution_path=paths['partner_resolution'],
                partner_input_snapshot_path=paths['partner_snapshot'],
                partner_simulation_matrix_path=paths['partner_simulation'],
                yangdo_recommendation_qa_path=paths['yangdo_qa'],
                yangdo_recommendation_precision_matrix_path=paths['yangdo_precision'],
                yangdo_recommendation_diversity_audit_path=paths['yangdo_diversity'],
                yangdo_special_sector_packet_path=paths['yangdo_special_sector'],
                yangdo_recommendation_contract_audit_path=paths['yangdo_contract'],
                yangdo_recommendation_bridge_packet_path=paths['yangdo_bridge'],
                yangdo_recommendation_ux_packet_path=paths['yangdo_ux'],
                yangdo_recommendation_alignment_audit_path=paths['yangdo_alignment'],
                yangdo_zero_display_recovery_audit_path=paths['yangdo_zero_display'],
                yangdo_service_copy_packet_path=paths['yangdo_service_copy'],
                permit_service_copy_packet_path=paths['permit_service_copy'],
                permit_service_alignment_audit_path=paths['permit_service_alignment'],
                permit_rental_lane_packet_path=paths['permit_rental_lane'],
                permit_service_ux_packet_path=paths['permit_service_ux'],
                permit_public_contract_audit_path=paths['permit_public_contract'],
                permit_prompt_case_binding_packet_path=paths['permit_prompt_case_binding'],
                permit_critical_prompt_surface_packet_path=paths['permit_critical_prompt_surface'],
                permit_partner_binding_parity_packet_path=paths['permit_partner_binding_parity'],
                permit_partner_binding_observability_path=paths['permit_partner_binding_observability'],
                permit_thinking_prompt_bundle_packet_path=paths['permit_thinking_prompt_bundle'],
                permit_next_action_brainstorm_path=paths['permit_next_action_brainstorm'],
                permit_runtime_reasoning_binding_audit_path=paths['permit_runtime_reasoning_binding'],
                permit_law_case_coverage_packet_path=paths['permit_law_case_coverage'],
                partner_input_handoff_packet_path=paths['partner_input_handoff'],
                partner_input_operator_flow_path=paths['partner_input_operator_flow'],
                widget_rental_catalog_path=paths['rental_catalog'],
                program_improvement_loop_path=paths['improvement_loop'],
                ai_platform_first_principles_review_path=paths['ai_first_principles'],
                external_masterplan_alignment_path=paths['external_masterplan_alignment'],
                system_split_first_principles_packet_path=paths['system_split_first_principles'],
                next_execution_packet_path=paths['next_execution'],
                yangdo_next_action_brainstorm_path=paths['yangdo_next_action_brainstorm'],
                yangdo_public_language_audit_path=paths['yangdo_public_language_audit'],
                founder_execution_chain_path=paths['founder_execution_chain'],
            )

            self.assertTrue(packet['go_live']['quality_green'])
            self.assertEqual(packet['decisions']['permit_rental_lane_ready'], True)
            self.assertEqual(packet['decisions']['permit_service_ux_ready'], True)
            self.assertEqual(packet['decisions']['permit_public_contract_ok'], True)
            self.assertEqual(packet['decisions']['permit_prompt_case_binding_ready'], True)
            self.assertEqual(packet['decisions']['permit_critical_prompt_surface_ready'], True)
            self.assertEqual(packet['decisions']['permit_partner_binding_parity_ready'], True)
            self.assertEqual(packet['decisions']['permit_partner_binding_observability_ready'], True)
            self.assertEqual(packet['decisions']['permit_thinking_prompt_bundle_ready'], True)
            self.assertEqual(packet['decisions']['permit_runtime_reasoning_binding_ok'], True)
            self.assertEqual(packet['decisions']['permit_law_case_coverage_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_special_sector_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_special_sector_publication_safe'], True)
            self.assertEqual(packet['decisions']['permit_prompt_loop_execution_lane'], 'runtime_reasoning_guard')
            self.assertEqual(packet['decisions']['permit_prompt_loop_parallel_lane'], 'surface_drift_digest')
            self.assertEqual(packet['decisions']['partner_input_handoff_ready'], True)
            self.assertEqual(packet['decisions']['partner_input_operator_flow_ready'], True)
            self.assertEqual(packet['decisions']['ai_platform_first_principles_ready'], True)
            self.assertEqual(packet['decisions']['external_masterplan_alignment_ok'], True)
            self.assertEqual(packet['decisions']['system_split_first_principles_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_zero_display_guard_ok'], True)
            self.assertEqual(packet['decisions']['next_execution_packet_ready'], True)
            self.assertEqual(packet['decisions']['next_execution_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_public_language_audit_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_public_language_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_prompt_loop_ready'], True)
            self.assertEqual(packet['decisions']['yangdo_prompt_loop_execution_lane'], 'prompt_loop_operationalization')
            self.assertEqual(packet['decisions']['founder_execution_chain_ready'], True)
            self.assertEqual(packet['decisions']['founder_execution_chain_converged'], True)
            self.assertEqual(packet['summaries']['permit_rental_lane']['detail_checklist_offerings'], ['permit_pro'])
            self.assertEqual(packet['summaries']['permit_service_ux']['detail_allowed_offerings'], ['permit_pro'])
            self.assertEqual(packet['summaries']['permit_service_ux']['assist_cta'], '수동 검토 요청')
            self.assertEqual(packet['summaries']['yangdo_special_sector_packet']['packet_ready'], True)
            self.assertEqual(packet['summaries']['yangdo_special_sector_packet']['special_sector_count'], 3)
            self.assertEqual(packet['summaries']['yangdo_special_sector_packet']['sector_ready_count'], 3)
            self.assertEqual(packet['summaries']['yangdo_special_sector_packet']['publication_safety_ok'], True)
            self.assertEqual(packet['summaries']['yangdo_special_sector_packet']['expansion_candidate_count'], 1)
            self.assertEqual(packet['summaries']['yangdo_zero_display_recovery_audit']['zero_display_total'], 3)
            self.assertTrue(packet['summaries']['yangdo_zero_display_recovery_audit']['market_bridge_route_ok'])
            self.assertEqual(packet['summaries']['permit_public_contract']['contract_ok'], True)
            self.assertEqual(packet['summaries']['permit_prompt_case_binding']['packet_ready'], True)
            self.assertEqual(packet['summaries']['permit_prompt_case_binding']['lane_id'], 'prompt_case_binding')
            self.assertEqual(packet['summaries']['permit_critical_prompt_surface']['packet_ready'], True)
            self.assertEqual(packet['summaries']['permit_critical_prompt_surface']['lane_id'], 'runtime_reasoning_guard')
            self.assertEqual(packet['summaries']['permit_partner_binding_parity']['packet_ready'], True)
            self.assertEqual(packet['summaries']['permit_partner_binding_parity']['family_total'], 2)
            self.assertTrue(packet['summaries']['permit_partner_binding_parity']['partner_surface_ready'])
            self.assertTrue(packet['summaries']['permit_partner_binding_observability']['observability_ready'])
            self.assertEqual(packet['summaries']['permit_partner_binding_observability']['expected_family_total'], 2)
            self.assertEqual(packet['summaries']['permit_thinking_prompt_bundle']['lane_id'], 'runtime_reasoning_guard')
            self.assertTrue(packet['summaries']['permit_thinking_prompt_bundle']['runtime_target_ready'])
            self.assertEqual(packet['summaries']['permit_next_action_brainstorm']['execution_lane'], 'runtime_reasoning_guard')
            self.assertEqual(packet['summaries']['permit_next_action_brainstorm']['parallel_lane'], 'surface_drift_digest')
            self.assertTrue(packet['summaries']['permit_next_action_brainstorm']['review_reason_decision_ladder_ready'])
            self.assertEqual(packet['summaries']['permit_runtime_reasoning_binding']['packet_ready'], True)
            self.assertEqual(packet['summaries']['permit_runtime_reasoning_binding']['lane_id'], 'runtime_reasoning_guard')
            self.assertEqual(packet['summaries']['permit_law_case_coverage']['packet_ready'], True)
            self.assertEqual(packet['summaries']['permit_law_case_coverage']['real_industry_total'], 195)
            self.assertEqual(packet['summaries']['permit_law_case_coverage']['manual_scope_override_total'], 2)
            self.assertEqual(packet['summaries']['permit_law_case_coverage']['case_total'], 36)
            self.assertEqual(packet['summaries']['partner_input_handoff']['common_required_inputs'], ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'])
            self.assertTrue(packet['summaries']['partner_input_handoff']['copy_paste_ready'])
            self.assertEqual(packet['summaries']['ai_platform_first_principles_review']['current_bottleneck'], 'public/private publish 분기')
            self.assertEqual(packet['summaries']['external_masterplan_alignment']['alignment_ok'], True)
            self.assertEqual(packet['summaries']['next_execution']['selected_lane_id'], 'zero_display_recovery_guard')
            self.assertEqual(packet['summaries']['next_execution']['founder_selected_matches_primary'], False)
            self.assertEqual(packet['summaries']['next_execution']['founder_primary_system'], 'permit')
            self.assertEqual(packet['summaries']['next_execution']['founder_primary_lane_id'], 'prompt_case_binding')
            self.assertEqual(packet['summaries']['next_execution']['verification_command_count'], 1)
            self.assertEqual(packet['summaries']['yangdo_next_action_brainstorm']['execution_lane'], 'prompt_loop_operationalization')
            self.assertEqual(packet['summaries']['yangdo_public_language_audit']['remaining_phrase_count'], 0)
            self.assertTrue(packet['summaries']['founder_execution_chain']['focus_matches_execution'])
            self.assertEqual(packet['topology']['main_platform_host'], 'seoulmna.kr')
            self.assertIn('confirm_live_missing', packet['blockers'])
            self.assertIn('release_confirmation_required', packet['normalized_blockers'])

    def test_main_writes_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out_json = base / 'packet.json'
            out_md = base / 'packet.md'
            with patch('scripts.generate_operations_packet.build_operations_packet', return_value={'go_live': {'quality_green': True}, 'blockers': []}):
                with patch.object(sys, 'argv', ['generate_operations_packet.py', '--json', str(out_json), '--md', str(out_md)]):
                    code = main()
            self.assertEqual(code, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())


if __name__ == '__main__':
    unittest.main()
