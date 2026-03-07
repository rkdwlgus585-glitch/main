import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_partner_activation_resolution import build_resolution_report, main


class VerifyPartnerActivationResolutionTests(unittest.TestCase):
    @patch('scripts.verify_partner_activation_resolution._build_flow_for_inputs')
    @patch('scripts.verify_partner_activation_resolution._build_preview_for_scope')
    def test_build_resolution_report_matches_selected_scenario(self, mock_preview, mock_flow):
        mock_preview.return_value = {
            'scenarios': [
                {'scenario': 'baseline', 'remaining_required_inputs': ['partner_proof_url', 'partner_api_key'], 'resolved_inputs': []},
                {'scenario': 'proof_and_key', 'remaining_required_inputs': ['partner_data_source_approval'], 'resolved_inputs': ['partner_proof_url', 'partner_api_key']},
            ],
            'recommended_path': {'scenario': 'proof_and_key', 'remaining_required_inputs': ['partner_data_source_approval']},
        }
        mock_flow.return_value = {
            'handoff': {
                'remaining_required_inputs': ['partner_data_source_approval'],
                'resolved_inputs': ['partner_proof_url', 'partner_api_key'],
            },
            'steps': [
                {'name': 'activate_partner_tenant'},
            ],
            '_command_ok': False,
        }

        payload = build_resolution_report(
            offering_id='permit_standard',
            tenant_id='partner_demo',
            channel_id='partner_demo',
            host='permit-demo.example.com',
            brand_name='Permit Demo',
            scenario='proof_and_key',
            proof_url='https://example.com/contract',
            api_key_value='secret',
        )
        self.assertTrue(payload['summary']['ok'])
        self.assertTrue(payload['summary']['preview_ok'])
        self.assertTrue(payload['summary']['selected_found'])
        self.assertTrue(payload['summary']['activation_step_found'])
        self.assertTrue(payload['summary']['matches_preview_expected_remaining'])
        self.assertEqual(payload['scenario']['selected'], 'proof_and_key')
        self.assertEqual(payload['actual']['remaining_required_inputs'], ['partner_data_source_approval'])

    @patch('scripts.verify_partner_activation_resolution._build_flow_for_inputs')
    @patch('scripts.verify_partner_activation_resolution._build_preview_for_scope')
    def test_build_resolution_report_fails_when_activation_step_missing(self, mock_preview, mock_flow):
        mock_preview.return_value = {
            'scenarios': [
                {'scenario': 'baseline', 'remaining_required_inputs': ['partner_proof_url'], 'resolved_inputs': []},
            ],
            'recommended_path': {'scenario': 'baseline', 'remaining_required_inputs': ['partner_proof_url']},
        }
        mock_flow.return_value = {
            'handoff': {
                'remaining_required_inputs': ['partner_proof_url'],
                'resolved_inputs': [],
            },
            'steps': [
                {'name': 'scaffold_partner_offering'},
            ],
            '_command_ok': False,
        }

        payload = build_resolution_report(
            offering_id='permit_standard',
            tenant_id='partner_demo',
            channel_id='partner_demo',
            host='permit-demo.example.com',
            brand_name='Permit Demo',
            scenario='baseline',
            proof_url='',
            api_key_value='',
        )
        self.assertFalse(payload['summary']['ok'])
        self.assertTrue(payload['summary']['preview_ok'])
        self.assertTrue(payload['summary']['selected_found'])
        self.assertFalse(payload['summary']['activation_step_found'])

    @patch('scripts.verify_partner_activation_resolution.build_resolution_report')
    def test_cli_writes_outputs(self, mock_build):
        mock_build.return_value = {
            'scope': {'tenant_id': 'partner_demo'},
            'scenario': {'selected': 'proof_key_and_approval', 'preview_expected_remaining_required_inputs': [], 'preview_expected_resolved_inputs': ['partner_proof_url']},
            'actual': {'remaining_required_inputs': [], 'resolved_inputs': ['partner_proof_url'], 'command_ok': True},
            'summary': {'ok': True, 'matches_preview_expected_remaining': True, 'missing_vs_preview': [], 'extra_vs_preview': []},
        }
        with tempfile.TemporaryDirectory() as td:
            json_path = Path(td) / 'resolution.json'
            md_path = Path(td) / 'resolution.md'
            argv = [
                'verify_partner_activation_resolution.py',
                '--offering-id', 'permit_standard',
                '--tenant-id', 'partner_demo',
                '--channel-id', 'partner_demo',
                '--host', 'permit-demo.example.com',
                '--brand-name', 'Permit Demo',
                '--json', str(json_path),
                '--md', str(md_path),
            ]
            with patch('sys.argv', argv):
                code = main()
            self.assertEqual(code, 0)
            payload = json.loads(json_path.read_text(encoding='utf-8'))
            self.assertTrue(payload['summary']['ok'])
            self.assertIn('Partner Activation Resolution Verification', md_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
