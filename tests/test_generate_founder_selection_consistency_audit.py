import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_founder_selection_consistency_audit import build_payload


class GenerateFounderSelectionConsistencyAuditTests(unittest.TestCase):
    def test_thinking_bundle_lane_is_consistent_when_operations_and_focus_match(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            operations = base / 'operations.json'
            founder = base / 'founder.json'
            focus = base / 'focus.json'
            execution = base / 'execution.json'
            chain = base / 'chain.json'
            permit_thinking = base / 'permit_thinking.json'

            operations.write_text(json.dumps({'decisions': {'permit_thinking_prompt_bundle_ready': True, 'next_execution_ready': True}}, ensure_ascii=False), encoding='utf-8')
            founder.write_text(json.dumps({'summary': {'primary_system': 'permit', 'primary_lane_id': 'thinking_prompt_bundle_lock'}}, ensure_ascii=False), encoding='utf-8')
            focus.write_text(json.dumps({'summary': {'selected_track': 'permit', 'selected_lane_id': 'thinking_prompt_bundle_lock', 'founder_primary_ready': True, 'selected_matches_founder': True, 'selection_policy': 'founder_primary_ready_now'}}, ensure_ascii=False), encoding='utf-8')
            execution.write_text(json.dumps({'summary': {'selected_track': 'permit', 'selected_lane_id': 'thinking_prompt_bundle_lock'}}, ensure_ascii=False), encoding='utf-8')
            chain.write_text(json.dumps({'summary': {'focus_matches_execution': True}}, ensure_ascii=False), encoding='utf-8')
            permit_thinking.write_text(json.dumps({'summary': {'packet_ready': True}}, ensure_ascii=False), encoding='utf-8')

            payload = build_payload(
                operations_path=operations,
                founder_path=founder,
                focus_path=focus,
                execution_path=execution,
                chain_path=chain,
                permit_thinking_path=permit_thinking,
            )

            self.assertTrue(payload['summary']['audit_ok'])
            self.assertEqual(payload['summary']['issue_count'], 0)


if __name__ == '__main__':
    unittest.main()
