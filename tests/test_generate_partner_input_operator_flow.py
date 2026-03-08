import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_partner_input_operator_flow import build_partner_input_operator_flow, main


class GeneratePartnerInputOperatorFlowTests(unittest.TestCase):
    def test_build_partner_input_operator_flow_exposes_simulate_and_apply_commands(self):
        with tempfile.TemporaryDirectory() as td:
            handoff = Path(td) / 'handoff.json'
            handoff.write_text(json.dumps({
                'summary': {
                    'partner_count': 2,
                    'common_required_inputs': ['partner_proof_url', 'partner_api_key', 'partner_data_source_approval'],
                    'copy_paste_ready': True,
                    'ready_after_recommended_injection': True,
                    'ready_after_recommended_injection_count': 2,
                },
                'partners': [
                    {
                        'tenant_id': 'partner_alpha',
                        'channel_id': 'channel_alpha',
                        'offering_id': 'yangdo_standard',
                        'host': 'alpha.example.com',
                        'brand_name': 'Alpha',
                        'copy_paste_packet': {
                            'proof_url_field': 'proof_url=https://alpha.example.com/contracts/partner_alpha',
                            'api_key_env_line': 'TENANT_API_KEY_PARTNER_ALPHA=<issued-secret>',
                            'source_id_line': 'source_id=partner_alpha_source',
                        },
                        'simulated_decision_after_injection': 'ready',
                    }
                ],
            }, ensure_ascii=False), encoding='utf-8')

            payload = build_partner_input_operator_flow(handoff_path=handoff)

        self.assertTrue(payload['summary']['packet_ready'])
        self.assertEqual(payload['summary']['partner_activation_decision'], 'ready_for_operator_injection')
        self.assertEqual(payload['summary']['recommended_sequence'][0], 'simulate_partner_input_injection')
        row = payload['partners'][0]
        self.assertIn('scripts/simulate_partner_input_injection.py', row['simulate_command'])
        self.assertIn('--proof-url "https://alpha.example.com/contracts/partner_alpha"', row['simulate_command'])
        self.assertIn('scripts/run_partner_onboarding_flow.py', row['dry_run_command'])
        self.assertIn('--api-key-env "TENANT_API_KEY_PARTNER_ALPHA"', row['dry_run_command'])
        self.assertIn('--apply', row['apply_command'])
        self.assertEqual(row['simulated_decision_after_injection'], 'ready')

    def test_main_writes_json_and_md(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            handoff = base / 'handoff.json'
            handoff.write_text(json.dumps({'summary': {'partner_count': 1, 'copy_paste_ready': True}, 'partners': []}), encoding='utf-8')
            out_json = base / 'flow.json'
            out_md = base / 'flow.md'
            with patch('sys.argv', ['generate_partner_input_operator_flow.py', '--handoff', str(handoff), '--json', str(out_json), '--md', str(out_md)]):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())


if __name__ == '__main__':
    unittest.main()
