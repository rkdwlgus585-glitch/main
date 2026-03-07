import json
import tempfile
import unittest
from pathlib import Path

from scripts.scaffold_wp_platform_assets import build_wp_platform_assets


class ScaffoldWpPlatformAssetsTests(unittest.TestCase):
    def test_scaffold_creates_child_theme_and_lazy_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            surface = base / 'surface.json'
            astra = base / 'astra.json'
            surface.write_text(
                json.dumps({'surfaces': {'kr': {'host': 'seoulmna.kr'}, 'co': {'host': 'seoulmna.co.kr'}}}, ensure_ascii=False),
                encoding='utf-8',
            )
            astra.write_text(
                json.dumps({'astra': {'theme_name': 'Astra', 'theme_version': '4.12.3'}, 'decision': {'strategy': 'reference_only_for_next_front'}}, ensure_ascii=False),
                encoding='utf-8',
            )
            payload = build_wp_platform_assets(lab_root=base / 'lab', surface_audit_path=surface, astra_reference_path=astra)

            theme_root = base / 'lab' / 'staging' / 'wp-content' / 'themes' / 'seoulmna-platform-child'
            plugin_root = base / 'lab' / 'staging' / 'wp-content' / 'plugins' / 'seoulmna-platform-bridge'
            self.assertTrue((theme_root / 'style.css').exists())
            self.assertTrue((theme_root / 'functions.php').exists())
            self.assertTrue((theme_root / 'assets' / 'css' / 'platform.css').exists())
            self.assertTrue((plugin_root / 'seoulmna-platform-bridge.php').exists())
            self.assertTrue((plugin_root / 'assets' / 'js' / 'bridge.js').exists())
            self.assertEqual(payload['calculator_mount_policy']['homepage'], 'cta_only_no_iframe')
            self.assertEqual(payload['plugin']['public_mount_host'], 'seoulmna.kr')
            self.assertEqual(payload['plugin']['public_mount_base'], 'https://seoulmna.kr/_calc')
            self.assertEqual(payload['plugin']['listing_host'], 'seoulmna.co.kr')
            php = (plugin_root / 'seoulmna-platform-bridge.php').read_text(encoding='utf-8')
            self.assertIn("add_shortcode('seoulmna_calc_gate'", php)
            self.assertIn("data-smna-calc-launch=\"true\"", php)
            self.assertIn("https://seoulmna.kr/_calc", php)
            self.assertIn("SMNA_PLATFORM_BRIDGE_DEFAULT_PUBLIC_MOUNT_BASE", php)
            js = (plugin_root / 'assets' / 'js' / 'bridge.js').read_text(encoding='utf-8')
            self.assertIn("document.createElement('iframe')", js)
            self.assertIn("sandbox', 'allow-scripts allow-forms allow-popups'", js)


if __name__ == '__main__':
    unittest.main()
