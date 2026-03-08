import json
import tempfile
import unittest
from pathlib import Path

from scripts import generate_next_batch_focus_packet


class GenerateNextBatchFocusPacketTests(unittest.TestCase):
    def test_prefers_yangdo_when_live_and_partner_are_externally_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / 'operations.json'
            system_split = root / 'split.json'
            yangdo = root / 'yangdo.json'
            permit = root / 'permit.json'

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
                'current_execution_lane': {'id': 'operator_demo_surface', 'title': 'permit execution'},
                'parallel_brainstorm_lane': {'id': 'partner_demo_surface', 'title': 'permit parallel'},
            }, ensure_ascii=False), encoding='utf-8')

            payload = generate_next_batch_focus_packet.build_packet(
                operations_path=operations,
                system_split_path=system_split,
                yangdo_path=yangdo,
                permit_path=permit,
            )

            self.assertTrue(payload['summary']['packet_ready'])
            self.assertEqual(payload['selected_focus']['track'], 'yangdo')
            self.assertEqual(payload['selected_focus']['lane_id'], 'zero_display_recovery_guard')
            self.assertEqual(payload['selected_focus']['execution_prompt'], 'yangdo prompt')
            self.assertEqual(len(payload['parallel_candidates']), 1)
            deferred_tracks = [item['track'] for item in payload['deferred_candidates']]
            self.assertIn('platform', deferred_tracks)
            self.assertIn('partner', deferred_tracks)


if __name__ == '__main__':
    unittest.main()
