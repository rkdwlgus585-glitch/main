import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_platform_front_audit import _extract_meta_signals, build_platform_front_audit


class GeneratePlatformFrontAuditTests(unittest.TestCase):
    def test_extract_meta_signals_detects_vercel_and_next(self):
        html = (
            '<html><head>'
            '<title>AI 플랫폼</title>'
            '<meta name="description" content="통합 플랫폼"/>'
            '<meta property="og:title" content="OG 제목"/>'
            '<meta property="og:description" content="OG 설명"/>'
            '<script src="/_next/static/chunks/main.js"></script>'
            '</head></html>'
        )
        out = _extract_meta_signals(html, {'server': 'Vercel'}, 'https://example.com')
        self.assertTrue(out['is_vercel'])
        self.assertTrue(out['is_nextjs_like'])
        self.assertEqual(out['live_stack'], 'nextjs_like_live')
        self.assertEqual(out['title'], 'AI 플랫폼')
        self.assertEqual(out['description'], '통합 플랫폼')

    @patch('scripts.generate_platform_front_audit.fetch_site_signal')
    def test_build_platform_front_audit_uses_channel_policy_and_operations(self, mock_fetch):
        mock_fetch.side_effect = [
            {
                'url': 'https://admini.kr',
                'ok': True,
                'server': 'Vercel',
                'is_vercel': True,
                'is_nextjs_like': True,
                'title': 'Admini',
            },
            {'url': 'https://seoulmna.co.kr', 'ok': True, 'server': 'nginx', 'title': 'Seoul co', 'live_stack': 'gnuboard_weaver_like'},
            {'url': 'https://seoulmna.kr', 'ok': True, 'server': 'openresty', 'title': 'Seoul kr', 'live_stack': 'wordpress_astra_live', 'wordpress_markers': ['/wp-content/'], 'astra_markers': ['astra-theme-css']},
        ]
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            channels = base / 'channel_profiles.json'
            manifest = base / 'manifest.json'
            operations = base / 'operations.json'
            attorney = base / 'attorney.json'
            channels.write_text(
                json.dumps(
                    {
                        'channels': [
                            {
                                'channel_id': 'seoul_web',
                                'channel_role': 'platform_front',
                                'engine_origin': 'https://calc.seoulmna.co.kr',
                                'embed_base_url': 'https://calc.seoulmna.co.kr/widgets',
                                'channel_hosts': ['seoulmna.kr'],
                                'canonical_public_host': 'seoulmna.kr',
                                'public_host_policy': 'kr_main_platform',
                                'platform_front_host': 'seoulmna.kr',
                                'legacy_content_host': 'seoulmna.co.kr',
                                'public_calculator_mount_base': 'https://seoulmna.kr/_calc',
                                'private_engine_visibility': 'reverse_proxy_hidden_origin',
                                'internal_widget_channel_id': 'seoul_widget_internal',
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            manifest.write_text(
                json.dumps(
                    {
                        'host': 'seoulmna.co.kr',
                        'widgets': [
                            {'widget': 'yangdo', 'ok': True},
                            {'widget': 'permit', 'ok': True},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            operations.write_text(
                json.dumps(
                    {
                        'go_live': {'quality_green': True},
                        'decisions': {'seoul_live_decision': 'awaiting_live_confirmation'},
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            attorney.write_text(
                json.dumps(
                    {
                        'tracks': [
                            {'track_id': 'A', 'claim_sentence_draft': {'independent': 'x'}},
                            {'track_id': 'B', 'claim_sentence_draft': {'independent': 'y'}},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )
            out = build_platform_front_audit(
                benchmark_url='https://admini.kr',
                public_urls=['https://seoulmna.co.kr', 'https://seoulmna.kr'],
                channel_id='seoul_web',
                channels_path=channels,
                manifest_path=manifest,
                operations_path=operations,
                attorney_path=attorney,
                front_app_path=base / 'kr_platform_front',
            )
            self.assertEqual(out['front']['canonical_public_host'], 'seoulmna.kr')
            self.assertEqual(out['front']['public_host_policy'], 'kr_main_platform')
            self.assertEqual(out['front']['target_platform_front_host'], 'seoulmna.kr')
            self.assertEqual(out['front']['current_live_public_stack'], 'wordpress_astra_live')
            self.assertEqual(out['front']['listing_market_host'], 'seoulmna.co.kr')
            self.assertEqual(out['front']['public_calculator_mount_base'], 'https://seoulmna.kr/_calc')
            self.assertEqual(out['front']['private_engine_visibility'], 'reverse_proxy_hidden_origin')
            self.assertTrue(out['calculators']['yangdo_widget_ready'])
            self.assertTrue(out['calculators']['permit_widget_ready'])
            self.assertTrue(out['calculators']['live_confirmation_pending'])
            self.assertTrue(out['patent']['track_a_claim_sentence_ready'])
            self.assertEqual(out['local_truth']['seoul_live_decision'], 'awaiting_live_confirmation')
            self.assertEqual(out['completion_summary']['calculator_status'], 'engine_complete_live_front_pending')
            self.assertIn('kr_live_wordpress_cutover_pending', out['front']['platform_front_gap'])
            self.assertEqual(out['completion_summary']['front_platform_status'], 'front_policy_and_live_pending')

    @patch('scripts.generate_platform_front_audit.fetch_site_signal')
    def test_build_platform_front_audit_detects_front_app_build_readiness(self, mock_fetch):
        mock_fetch.side_effect = [
            {'url': 'https://admini.kr', 'ok': True, 'server': 'Vercel', 'is_vercel': True, 'is_nextjs_like': True, 'title': 'Admini'},
            {'url': 'https://seoulmna.co.kr', 'ok': True, 'server': 'nginx', 'title': 'Seoul co', 'live_stack': 'gnuboard_weaver_like'},
            {'url': 'https://seoulmna.kr', 'ok': True, 'server': 'openresty', 'title': 'Seoul kr', 'live_stack': 'wordpress_astra_live', 'wordpress_markers': ['/wp-content/'], 'astra_markers': ['astra-theme-css']},
        ]
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            channels = base / 'channel_profiles.json'
            manifest = base / 'manifest.json'
            operations = base / 'operations.json'
            attorney = base / 'attorney.json'
            front_app = base / 'kr_platform_front'
            (front_app / '.next').mkdir(parents=True)
            (front_app / '.next' / 'build-manifest.json').write_text('{}', encoding='utf-8')
            (front_app / 'node_modules').mkdir()
            (front_app / 'app' / 'api' / 'platform-status').mkdir(parents=True)
            (front_app / 'app' / 'yangdo').mkdir(parents=True)
            (front_app / 'app' / 'permit').mkdir(parents=True)
            (front_app / 'app' / 'page.tsx').write_text('export default function Page(){return null}', encoding='utf-8')
            (front_app / 'app' / 'yangdo' / 'page.tsx').write_text('export default function Page(){return null}', encoding='utf-8')
            (front_app / 'app' / 'permit' / 'page.tsx').write_text('export default function Page(){return null}', encoding='utf-8')
            (front_app / 'app' / 'api' / 'platform-status' / 'route.ts').write_text('export function GET(){}', encoding='utf-8')
            (front_app / 'package.json').write_text(json.dumps({'dependencies': {'next': '16.1.6', 'react': '19.2.4'}, 'scripts': {'build': 'next build', 'dev': 'next dev'}}), encoding='utf-8')
            (front_app / 'README.md').write_text('# x\n', encoding='utf-8')
            (front_app / '.env.example').write_text('NEXT_PUBLIC_TENANT_ID=x\n', encoding='utf-8')
            (front_app / 'vercel.json').write_text('{"framework":"nextjs"}', encoding='utf-8')
            channels.write_text(json.dumps({'channels': [{'channel_id': 'seoul_web', 'channel_role': 'platform_front', 'engine_origin': 'https://calc.seoulmna.co.kr', 'embed_base_url': 'https://calc.seoulmna.co.kr/widgets', 'channel_hosts': ['seoulmna.kr'], 'canonical_public_host': 'seoulmna.kr', 'public_host_policy': 'kr_main_platform', 'platform_front_host': 'seoulmna.kr', 'legacy_content_host': 'seoulmna.co.kr', 'public_calculator_mount_base': 'https://seoulmna.kr/_calc', 'private_engine_visibility': 'reverse_proxy_hidden_origin', 'internal_widget_channel_id': 'seoul_widget_internal'}]}, ensure_ascii=False), encoding='utf-8')
            manifest.write_text(json.dumps({'host': 'seoulmna.co.kr', 'widgets': [{'widget': 'yangdo', 'ok': True}, {'widget': 'permit', 'ok': True}]}, ensure_ascii=False), encoding='utf-8')
            operations.write_text(json.dumps({'go_live': {'quality_green': True}, 'decisions': {'seoul_live_decision': 'awaiting_live_confirmation'}}, ensure_ascii=False), encoding='utf-8')
            attorney.write_text(json.dumps({'tracks': [{'track_id': 'A', 'claim_sentence_draft': {'independent': 'x'}}, {'track_id': 'B', 'claim_sentence_draft': {'independent': 'y'}}]}, ensure_ascii=False), encoding='utf-8')
            out = build_platform_front_audit(
                benchmark_url='https://admini.kr',
                public_urls=['https://seoulmna.co.kr', 'https://seoulmna.kr'],
                channel_id='seoul_web',
                channels_path=channels,
                manifest_path=manifest,
                operations_path=operations,
                attorney_path=attorney,
                front_app_path=front_app,
            )
            self.assertTrue(out['front_app']['build_artifacts_ready'])
            self.assertTrue(out['front_app']['vercel_config_ready'])
            self.assertEqual(out['completion_summary']['front_platform_status'], 'kr_wordpress_live_next_cutover_pending')


if __name__ == '__main__':
    unittest.main()
