import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_wordpress_platform_strategy import build_wordpress_platform_strategy


class GenerateWordpressPlatformStrategyTests(unittest.TestCase):
    @patch('scripts.generate_wordpress_platform_strategy._fetch_site_signal')
    def test_strategy_prefers_wordpress_runtime_and_lazy_gate(self, mock_fetch_site_signal):
        mock_fetch_site_signal.return_value = {
            'url': 'https://admini.kr',
            'status_code': 200,
            'server': 'Vercel',
            'signals': ['/_next/', 'vercel'],
        }
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            surface = base / 'surface.json'
            wp_lab = base / 'wp_lab.json'
            wp_assets = base / 'wp_assets.json'
            surface.write_text(
                json.dumps({'surfaces': {'kr': {'host': 'seoulmna.kr', 'stack': 'wordpress_astra_live'}, 'co': {'host': 'seoulmna.co.kr'}}}, ensure_ascii=False),
                encoding='utf-8',
            )
            wp_lab.write_text(json.dumps({'summary': {'package_count': 6}}, ensure_ascii=False), encoding='utf-8')
            wp_assets.write_text(json.dumps({'summary': {'theme_ready': True, 'plugin_ready': True}}, ensure_ascii=False), encoding='utf-8')

            payload = build_wordpress_platform_strategy(
                surface_audit_path=surface,
                wp_lab_path=wp_lab,
                wp_assets_path=wp_assets,
            )

            self.assertEqual(payload['runtime_decision']['primary_runtime'], 'wordpress_astra_live')
            self.assertEqual(payload['runtime_decision']['support_runtime'], 'private_engine_behind_kr_reverse_proxy')
            self.assertEqual(payload['calculator_mount_decision']['recommended_pattern'], 'cta_on_home_lazy_gate_on_service_page_private_runtime_on_kr')
            self.assertIn('rank-math', payload['plugin_stack']['keep_live'])
            self.assertIn('wordpress-seo', payload['plugin_stack']['avoid_live_duplication'])
            self.assertTrue(payload['objective_inputs']['wp_assets_ready'])
            self.assertEqual(payload['current_live_stack']['co_role'], 'listing_market_site')
            self.assertEqual(payload['calculator_mount_decision']['recommended_by_page']['public_runtime'], 'https://seoulmna.kr/_calc/<type>?embed=1')


if __name__ == '__main__':
    unittest.main()
