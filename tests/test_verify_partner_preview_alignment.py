import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_partner_preview_alignment import build_alignment, main


class VerifyPartnerPreviewAlignmentTests(unittest.TestCase):
    def test_build_alignment_matches_current_and_preview(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            flow = base / 'flow.json'
            preview = base / 'preview.json'
            flow.write_text(json.dumps({
                'offering_id': 'permit_standard',
                'tenant_id': 'partner_demo',
                'channel_id': 'partner_demo',
                'host': 'permit-demo.example.com',
                'handoff': {
                    'remaining_required_inputs': ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'],
                    'resolved_inputs': [],
                },
            }), encoding='utf-8')
            preview.write_text(json.dumps({
                'offering_id': 'permit_standard',
                'tenant_id': 'partner_demo',
                'channel_id': 'partner_demo',
                'host': 'permit-demo.example.com',
                'scenarios': [
                    {
                        'scenario': 'baseline',
                        'remaining_required_inputs': ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'],
                        'resolved_inputs': [],
                    },
                    {
                        'scenario': 'proof_key_and_approval',
                        'remaining_required_inputs': [],
                        'resolved_inputs': ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'],
                    },
                ],
                'recommended_path': {
                    'scenario': 'proof_key_and_approval',
                    'remaining_required_inputs': [],
                },
            }), encoding='utf-8')

            payload = build_alignment(partner_flow_path=flow, partner_preview_path=preview)
            self.assertTrue(payload['summary']['ok'])
            self.assertTrue(payload['summary']['baseline_matches_current'])
            self.assertTrue(payload['summary']['recommended_reduces_current'])
            self.assertTrue(payload['summary']['recommended_clears_current'])
            self.assertEqual(payload['preview']['removed_inputs_vs_current'], ['partner_api_key', 'partner_data_source_approval', 'partner_proof_url'])

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            flow = base / 'flow.json'
            preview = base / 'preview.json'
            json_path = base / 'alignment.json'
            md_path = base / 'alignment.md'
            flow.write_text(json.dumps({'handoff': {'remaining_required_inputs': ['partner_proof_url'], 'resolved_inputs': []}}), encoding='utf-8')
            preview.write_text(json.dumps({
                'scenarios': [{'scenario': 'baseline', 'remaining_required_inputs': ['partner_proof_url']}],
                'recommended_path': {'scenario': 'baseline', 'remaining_required_inputs': ['partner_proof_url']},
            }), encoding='utf-8')
            argv = [
                'verify_partner_preview_alignment.py',
                '--partner-flow', str(flow),
                '--partner-preview', str(preview),
                '--json', str(json_path),
                '--md', str(md_path),
            ]
            with patch('sys.argv', argv):
                code = main()
            self.assertEqual(code, 0)
            payload = json.loads(json_path.read_text(encoding='utf-8'))
            self.assertTrue(payload['summary']['ok'])
            self.assertIn('Partner Preview Alignment', md_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
