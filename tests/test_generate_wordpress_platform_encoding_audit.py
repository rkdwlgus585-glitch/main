import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_wordpress_platform_encoding_audit import (
    REQUIRED_PHRASES_BY_NAME,
    build_encoding_audit,
)


class GenerateWordpressPlatformEncodingAuditTests(unittest.TestCase):
    def test_build_encoding_audit_accepts_clean_korean_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            home = base / 'home.html'
            navigation = base / 'navigation.json'
            apply = base / 'wp_surface_lab_apply_latest.json'

            home_phrases = REQUIRED_PHRASES_BY_NAME[home.name]
            navigation_phrases = REQUIRED_PHRASES_BY_NAME[navigation.name]
            apply_phrases = REQUIRED_PHRASES_BY_NAME[apply.name]

            home.write_text(
                '<h1>{}</h1><div>{}</div><button>{}</button>'.format(*home_phrases),
                encoding='utf-8',
            )
            navigation.write_text(
                json.dumps({'primary': [{'label': phrase} for phrase in navigation_phrases]}, ensure_ascii=False),
                encoding='utf-8',
            )
            apply.write_text(
                json.dumps(
                    {
                        'manifest': {
                            'menu': {'name': apply_phrases[0]},
                            'pages': [{'title': phrase} for phrase in apply_phrases[1:]],
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )

            payload = build_encoding_audit([home, navigation, apply])

            self.assertEqual(payload['summary']['checked_file_count'], 3)
            self.assertEqual(payload['summary']['issue_file_count'], 0)
            self.assertTrue(payload['summary']['encoding_ok'])

    def test_build_encoding_audit_detects_mojibake_and_missing_phrases(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            suspicious = base / 'wp_surface_lab_apply_latest.json'
            suspicious.write_text(
                '{"manifest":{"menu":{"name":"??戮곕뮲濾곌쑬?삭땻?筌먲퐢沅???????"},"pages":[{"title":"AI ??얜Ŧ利꿩뤆?쎛 ??⑥ъ젧"}]}}',
                encoding='utf-8',
            )

            payload = build_encoding_audit([suspicious])

            self.assertEqual(payload['summary']['checked_file_count'], 1)
            self.assertEqual(payload['summary']['issue_file_count'], 1)
            self.assertFalse(payload['summary']['encoding_ok'])
            bad = payload['files'][0]
            kinds = {issue['kind'] for issue in bad['issues']}
            self.assertIn('required_phrase_missing', kinds)
            self.assertTrue('known_mojibake_token_present' in kinds or 'single_question_hangul_sequence' in kinds)


if __name__ == '__main__':
    unittest.main()
