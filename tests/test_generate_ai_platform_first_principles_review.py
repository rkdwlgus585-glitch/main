import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_ai_platform_first_principles_review import build_review_payload, main


class GenerateAiPlatformFirstPrinciplesReviewTests(unittest.TestCase):
    def test_build_review_payload_contains_core_sections(self):
        with patch(
            'scripts.generate_ai_platform_first_principles_review._read_json',
            side_effect=[
                {
                    'one_line_summary': {'text': 'CHECK | green'},
                    'partner_api_contract_smoke': {'ok': True},
                    'browser_smoke': {'ok': True},
                    'secure_stack': {'ok': True},
                    'permit_integrity': {'ok': True},
                },
                {'blocking_issues': ['confirm_live_missing']},
                {},
                {},
                {},
            ],
        ), patch(
            'scripts.generate_ai_platform_first_principles_review._lines',
            return_value=['## Next Candidates', '1. tighten publish gate', '2. reduce operator branches'],
        ):
            payload = build_review_payload()

        self.assertTrue(payload['summary']['packet_ready'])
        self.assertEqual(payload['summary']['blocking_issue_count'], 1)
        self.assertEqual(payload['current_state']['current_bottleneck'], 'regression blocking issue: confirm_live_missing')
        self.assertGreaterEqual(len(payload['musk_style_questions']), 5)
        self.assertEqual(payload['next_experiments'][0], '1. tighten publish gate')

    def test_main_writes_json_and_md(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out_json = base / 'first_principles.json'
            out_md = base / 'first_principles.md'
            with patch('sys.argv', ['generate_ai_platform_first_principles_review.py', '--json', str(out_json), '--md', str(out_md)]):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())


if __name__ == '__main__':
    unittest.main()
