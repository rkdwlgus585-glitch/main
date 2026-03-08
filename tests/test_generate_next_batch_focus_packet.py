import json
import tempfile
import unittest
from pathlib import Path

from scripts import generate_next_batch_focus_packet


class GenerateNextBatchFocusPacketTests(unittest.TestCase):
    def test_prefers_founder_primary_when_still_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'
            founder_bundle = root / 'founder_bundle.json'

            operations.write_text(json.dumps({
                'decisions': {
                    'seoul_live_decision': 'awaiting_live_confirmation',
                    'partner_activation_decision': 'awaiting_partner_inputs',
                }
            }, ensure_ascii=False), encoding='utf-8')
            system_split.write_text(json.dumps({
                'tracks': {
                    'platform': {'current_bottleneck': 'platform_publish_gate', 'next_move': 'lock publish gate'},
                    'yangdo': {'current_bottleneck': 'zero_display_recovery_guard', 'next_move': 'refine yangdo explainability'},
                    'permit': {'current_bottleneck': 'operator_demo_surface', 'next_move': 'separate permit lanes'},
                }
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'execution_prompt': 'yangdo prompt',
                'current_execution_lane': {'id': 'zero_display_recovery_guard', 'title': 'yangdo execution'},
                'parallel_brainstorm_lane': {'id': 'public_language_normalization', 'title': 'yangdo parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'execution_prompt': 'permit prompt',
                'current_execution_lane': {'id': 'critical_prompt_surface_lock', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'partner_demo_surface', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            founder_bundle.write_text(json.dumps({
                'summary': {
                    'primary_system': 'permit',
                    'primary_lane_id': 'critical_prompt_surface_lock',
                    'parallel_system': 'yangdo',
                    'parallel_lane_id': 'zero_display_recovery_guard',
                }
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
                founder_bundle_path=founder_bundle,
            )

            self.assertTrue(payload['summary']['packet_ready'])
            self.assertEqual(payload['selected_focus']['track'], 'permit')
            self.assertEqual(payload['selected_focus']['lane_id'], 'critical_prompt_surface_lock')
            self.assertEqual(payload['selected_focus']['execution_prompt'], 'permit prompt')
            self.assertEqual(payload['summary']['selection_policy'], 'founder_primary_in_progress')
            self.assertEqual(payload['summary']['founder_primary_system'], 'permit')
            self.assertEqual(payload['summary']['founder_primary_lane_id'], 'critical_prompt_surface_lock')
            self.assertTrue(payload['summary']['selected_matches_founder'])
            self.assertFalse(payload['summary']['founder_primary_ready'])
            self.assertTrue(payload['founder_contract']['selected_matches_founder'])
            self.assertEqual(len(payload['parallel_candidates']), 2)
            self.assertEqual(payload['parallel_candidates'][0]['track'], 'yangdo')
            self.assertEqual(payload['parallel_candidates'][1]['track'], 'permit')
            deferred_tracks = [item['track'] for item in payload['deferred_candidates']]
            self.assertIn('platform', deferred_tracks)
            self.assertIn('partner', deferred_tracks)

    def test_prefers_founder_successor_when_primary_is_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'
            founder_bundle = root / 'founder_bundle.json'

            operations.write_text(json.dumps({
                'decisions': {
                    'seoul_live_decision': 'awaiting_live_confirmation',
                    'partner_activation_decision': 'awaiting_partner_inputs',
                    'permit_prompt_case_binding_ready': True,
                    'permit_critical_prompt_surface_ready': True,
                }
            }, ensure_ascii=False), encoding='utf-8')
            system_split.write_text(json.dumps({
                'tracks': {
                    'platform': {'current_bottleneck': 'platform_publish_gate', 'next_move': 'lock publish gate'},
                    'yangdo': {'current_bottleneck': 'public_language_normalization', 'next_move': 'refine yangdo explainability'},
                    'permit': {'current_bottleneck': 'partner_binding_parity', 'next_move': 'publish partner-safe prompt binding'},
                }
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'execution_prompt': 'yangdo prompt',
                'current_execution_lane': {'id': 'public_language_normalization', 'title': 'yangdo execution'},
                'parallel_brainstorm_lane': {'id': 'focus_signature_concentration', 'title': 'yangdo parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'execution_prompt': 'permit prompt',
                'current_execution_lane': {'id': 'partner_binding_parity', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'review_reason_decision_ladder', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            founder_bundle.write_text(json.dumps({
                'summary': {
                    'primary_system': 'permit',
                    'primary_lane_id': 'prompt_case_binding',
                    'parallel_system': 'yangdo',
                    'parallel_lane_id': 'zero_display_recovery_guard',
                }
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
                founder_bundle_path=founder_bundle,
            )

            self.assertTrue(payload['summary']['packet_ready'])
            self.assertEqual(payload['selected_focus']['track'], 'permit')
            self.assertEqual(payload['selected_focus']['lane_id'], 'partner_binding_parity')
            self.assertEqual(payload['summary']['selection_policy'], 'founder_successor_ready_now')
            self.assertTrue(payload['summary']['founder_primary_ready'])
            self.assertTrue(payload['summary']['founder_successor_selected'])
            self.assertFalse(payload['summary']['selected_matches_founder'])

    def test_advances_from_green_partner_binding_to_parallel_review_reason_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'
            founder_bundle = root / 'founder_bundle.json'

            operations.write_text(json.dumps({
                'decisions': {
                    'seoul_live_decision': 'awaiting_live_confirmation',
                    'partner_activation_decision': 'awaiting_partner_inputs',
                    'permit_partner_binding_parity_ready': True,
                    'permit_service_alignment_ok': True,
                    'permit_service_ux_ready': True,
                }
            }, ensure_ascii=False), encoding='utf-8')
            system_split.write_text(json.dumps({
                'tracks': {
                    'platform': {'current_bottleneck': 'platform_publish_gate', 'next_move': 'lock publish gate'},
                    'yangdo': {'current_bottleneck': 'public_language_normalization', 'next_move': 'refine yangdo explainability'},
                    'permit': {'current_bottleneck': 'partner_binding_parity', 'next_move': 'compress review reasons into a decision ladder'},
                }
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'execution_prompt': 'yangdo prompt',
                'current_execution_lane': {'id': 'public_language_normalization', 'title': 'yangdo execution'},
                'parallel_brainstorm_lane': {'id': 'prompt_loop_operationalization', 'title': 'yangdo parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'execution_prompt': 'permit prompt',
                'current_execution_lane': {'id': 'partner_binding_parity', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'review_reason_decision_ladder', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            founder_bundle.write_text(json.dumps({
                'summary': {
                    'primary_system': 'permit',
                    'primary_lane_id': 'partner_binding_parity',
                    'parallel_system': 'yangdo',
                    'parallel_lane_id': 'public_language_normalization',
                }
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
                founder_bundle_path=founder_bundle,
            )

            self.assertTrue(payload['summary']['packet_ready'])
            self.assertTrue(payload['summary']['founder_primary_ready'])
            self.assertTrue(payload['summary']['founder_successor_selected'])
            self.assertEqual(payload['summary']['selection_policy'], 'founder_successor_ready_now')
            self.assertEqual(payload['selected_focus']['track'], 'permit')
            self.assertEqual(payload['selected_focus']['lane_id'], 'review_reason_decision_ladder')
            self.assertFalse(payload['summary']['selected_matches_founder'])

    def test_marks_permit_thinking_bundle_lane_as_founder_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'
            founder_bundle = root / 'founder_bundle.json'

            operations.write_text(json.dumps({
                'decisions': {
                    'seoul_live_decision': 'awaiting_live_confirmation',
                    'partner_activation_decision': 'awaiting_partner_inputs',
                    'permit_thinking_prompt_bundle_ready': True,
                }
            }, ensure_ascii=False), encoding='utf-8')
            system_split.write_text(json.dumps({
                'tracks': {
                    'platform': {'current_bottleneck': 'platform_publish_gate', 'next_move': 'lock publish gate'},
                    'yangdo': {'current_bottleneck': 'public_language_normalization', 'next_move': 'refine yangdo explainability'},
                    'permit': {'current_bottleneck': 'thinking_prompt_bundle_lock', 'next_move': 'separate detail and manual review CTA copy'},
                }
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'execution_prompt': 'yangdo prompt',
                'current_execution_lane': {'id': 'public_language_normalization', 'title': 'yangdo execution'},
                'parallel_brainstorm_lane': {'id': 'prompt_loop_operationalization', 'title': 'yangdo parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'execution_prompt': 'permit prompt',
                'current_execution_lane': {'id': 'thinking_prompt_bundle_lock', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'review_reason_decision_ladder', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            founder_bundle.write_text(json.dumps({
                'summary': {
                    'primary_system': 'permit',
                    'primary_lane_id': 'thinking_prompt_bundle_lock',
                    'parallel_system': 'yangdo',
                    'parallel_lane_id': 'public_language_normalization',
                }
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
                founder_bundle_path=founder_bundle,
            )

            self.assertTrue(payload['summary']['founder_primary_ready'])
            self.assertEqual(payload['summary']['selection_policy'], 'founder_successor_ready_now')
            self.assertEqual(payload['selected_focus']['lane_id'], 'review_reason_decision_ladder')

    def test_marks_founder_primary_in_progress_when_selected_before_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'
            founder_bundle = root / 'founder_bundle.json'

            operations.write_text(json.dumps({
                'decisions': {
                    'seoul_live_decision': 'awaiting_live_confirmation',
                    'partner_activation_decision': 'awaiting_partner_inputs',
                    'permit_service_alignment_ok': True,
                    'permit_service_ux_ready': True,
                }
            }, ensure_ascii=False), encoding='utf-8')
            system_split.write_text(json.dumps({
                'tracks': {
                    'platform': {'current_bottleneck': 'platform_publish_gate', 'next_move': 'lock publish gate'},
                    'yangdo': {'current_bottleneck': 'prompt_loop_operationalization', 'next_move': 'refine yangdo explainability'},
                    'permit': {'current_bottleneck': 'runtime_reasoning_guard', 'next_move': 'tighten release and runtime reasoning guard'},
                }
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'execution_prompt': 'yangdo prompt',
                'current_execution_lane': {'id': 'prompt_loop_operationalization', 'title': 'yangdo execution'},
                'parallel_brainstorm_lane': {'id': '', 'title': ''},
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'execution_prompt': 'permit prompt',
                'current_execution_lane': {'id': 'runtime_reasoning_guard', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'surface_drift_digest', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            founder_bundle.write_text(json.dumps({
                'summary': {
                    'primary_system': 'permit',
                    'primary_lane_id': 'runtime_reasoning_guard',
                    'parallel_system': 'yangdo',
                    'parallel_lane_id': 'prompt_loop_operationalization',
                }
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
                founder_bundle_path=founder_bundle,
            )

            self.assertFalse(payload['summary']['founder_primary_ready'])
            self.assertEqual(payload['selected_focus']['track'], 'permit')
            self.assertEqual(payload['selected_focus']['lane_id'], 'runtime_reasoning_guard')
            self.assertEqual(payload['summary']['selection_policy'], 'founder_primary_in_progress')
            self.assertTrue(payload['summary']['selected_matches_founder'])

    def test_keeps_yangdo_special_sector_guard_available_when_founder_primary_is_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'
            founder_bundle = root / 'founder_bundle.json'

            operations.write_text(json.dumps({
                'decisions': {
                    'seoul_live_decision': 'awaiting_live_confirmation',
                    'partner_activation_decision': 'awaiting_partner_inputs',
                    'permit_prompt_case_binding_ready': True,
                    'permit_critical_prompt_surface_ready': True,
                }
            }, ensure_ascii=False), encoding='utf-8')
            system_split.write_text(json.dumps({
                'tracks': {
                    'platform': {'current_bottleneck': 'platform_publish_gate', 'next_move': 'lock publish gate'},
                    'yangdo': {'current_bottleneck': 'special_sector_publication_guard', 'next_move': 'tighten telecom publication policy'},
                    'permit': {'current_bottleneck': 'prompt_case_binding', 'next_move': 'stabilize permit reasoning binding'},
                }
            }, ensure_ascii=False), encoding='utf-8')
            yangdo.write_text(json.dumps({
                'execution_prompt': 'yangdo prompt',
                'current_execution_lane': {'id': 'special_sector_publication_guard', 'title': 'yangdo telecom publication guard'},
                'parallel_brainstorm_lane': {'id': 'public_language_normalization', 'title': 'yangdo parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            permit.write_text(json.dumps({
                'execution_prompt': 'permit prompt',
                'current_execution_lane': {'id': 'prompt_case_binding', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'capital_registration_logic_brainstorm', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')
            founder_bundle.write_text(json.dumps({
                'summary': {
                    'primary_system': 'permit',
                    'primary_lane_id': 'prompt_case_binding',
                    'parallel_system': 'yangdo',
                    'parallel_lane_id': 'special_sector_publication_guard',
                }
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
                founder_bundle_path=founder_bundle,
            )

            self.assertTrue(payload['summary']['founder_primary_ready'])
            ready_lanes = {(item['track'], item['lane_id']) for item in payload['parallel_candidates']}
            self.assertIn(('yangdo', 'special_sector_publication_guard'), ready_lanes)


if __name__ == '__main__':
    unittest.main()
