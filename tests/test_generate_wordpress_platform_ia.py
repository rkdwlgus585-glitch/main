import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_wordpress_platform_ia import build_wordpress_platform_ia


class GenerateWordpressPlatformIATests(unittest.TestCase):
    def test_build_wordpress_platform_ia_generates_service_split(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            strategy = base / "strategy.json"
            surface = base / "surface.json"
            wp_assets = base / "wp_assets.json"
            strategy.write_text(
                json.dumps(
                    {
                        "current_live_stack": {"kr_host": "seoulmna.kr", "co_host": "seoulmna.co.kr"},
                        "calculator_mount_decision": {"private_engine_public_mount": "https://seoulmna.kr/_calc/<type>?embed=1"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            surface.write_text(
                json.dumps({"surfaces": {"kr": {"host": "seoulmna.kr"}, "co": {"host": "seoulmna.co.kr"}}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_assets.write_text(
                json.dumps(
                    {
                        "theme": {"slug": "seoulmna-platform-child"},
                        "plugin": {"slug": "seoulmna-platform-bridge"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_wordpress_platform_ia(
                strategy_path=strategy,
                surface_audit_path=surface,
                wp_assets_path=wp_assets,
            )

            self.assertEqual(payload["summary"]["page_count"], 6)
            self.assertEqual(payload["summary"]["lazy_gate_pages_count"], 2)
            self.assertIn("yangdo", payload["summary"]["lazy_gate_pages"])
            self.assertIn("knowledge", payload["summary"]["cta_only_pages"])
            self.assertEqual(payload["topology"]["platform_host"], "seoulmna.kr")
            self.assertEqual(payload["topology"]["bridge_plugin_slug"], "seoulmna-platform-bridge")
            self.assertEqual(payload["pages"][1]["page_id"], "yangdo")
            self.assertEqual(payload["pages"][1]["title"], "AI 양도가 산정 · 유사매물 추천")
            self.assertIn("recommendation_precision_strip", payload["pages"][1]["sections"])
            self.assertEqual(payload["pages"][1]["calculator_policy"], "lazy_gate_shortcode")


if __name__ == "__main__":
    unittest.main()
