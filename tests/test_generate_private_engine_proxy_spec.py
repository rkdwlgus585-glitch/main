import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_private_engine_proxy_spec import build_private_engine_proxy_spec


class GeneratePrivateEngineProxySpecTests(unittest.TestCase):
    def test_build_proxy_spec_uses_kr_public_mount_and_hidden_origin(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            channels = base / "channel_profiles.json"
            channels.write_text(
                json.dumps(
                    {
                        "channels": [
                            {
                                "channel_id": "seoul_web",
                                "canonical_public_host": "seoulmna.kr",
                                "legacy_content_host": "seoulmna.co.kr",
                                "public_calculator_mount_base": "https://seoulmna.kr/_calc",
                                "engine_origin": "https://calc.seoulmna.co.kr",
                                "embed_base_url": "https://calc.seoulmna.co.kr/widgets",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_private_engine_proxy_spec(channels_path=channels, channel_id="seoul_web")

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["topology"]["main_platform_host"], "seoulmna.kr")
            self.assertEqual(payload["topology"]["listing_market_host"], "seoulmna.co.kr")
            self.assertEqual(payload["topology"]["public_mount_base"], "https://seoulmna.kr/_calc")
            self.assertEqual(payload["topology"]["private_engine_origin"], "https://calc.seoulmna.co.kr")
            self.assertEqual(payload["topology"]["private_engine_upstream_widgets"], "https://calc.seoulmna.co.kr/widgets")
            self.assertEqual(payload["decision"]["public_contract"], "https://seoulmna.kr/_calc/*")
            self.assertEqual(payload["decision"]["engine_visibility"], "hidden_origin_only")
            self.assertIn("location /_calc/", payload["nginx"]["location_block"])
            self.assertIn("proxy_pass https://calc.seoulmna.co.kr/widgets/;", payload["nginx"]["location_block"])


if __name__ == "__main__":
    unittest.main()
