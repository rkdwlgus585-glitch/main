import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_kr_reverse_proxy_cutover import build_kr_reverse_proxy_cutover


class GenerateKrReverseProxyCutoverTests(unittest.TestCase):
    def test_build_cutover_combines_proxy_assets_and_ia(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            proxy_spec = base / "proxy.json"
            wp_assets = base / "wp_assets.json"
            wp_ia = base / "wp_ia.json"
            traffic = base / "traffic.json"
            proxy_spec.write_text(
                json.dumps(
                    {
                        "topology": {
                            "main_platform_host": "seoulmna.kr",
                            "listing_market_host": "seoulmna.co.kr",
                            "public_mount_base": "https://seoulmna.kr/_calc",
                            "private_engine_origin": "https://calc.seoulmna.co.kr",
                        },
                        "decision": {"public_contract": "https://seoulmna.kr/_calc/*"},
                        "nginx": {"location_block": "location /_calc/ { proxy_pass https://calc.seoulmna.co.kr/widgets/; }"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wp_assets.write_text(
                json.dumps({"summary": {"theme_ready": True, "plugin_ready": True}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_ia.write_text(
                json.dumps(
                    {
                        "pages": [
                            {"slug": "/yangdo", "calculator_policy": "lazy_gate_shortcode"},
                            {"slug": "/permit", "calculator_policy": "lazy_gate_shortcode"},
                            {"slug": "/", "calculator_policy": "cta_only_no_iframe"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            traffic.write_text(
                json.dumps({"decision": {"traffic_leak_blocked": True}}, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = build_kr_reverse_proxy_cutover(
                proxy_spec_path=proxy_spec,
                wp_assets_path=wp_assets,
                wp_ia_path=wp_ia,
                traffic_path=traffic,
            )

            self.assertTrue(payload["summary"]["cutover_ready"])
            self.assertEqual(payload["summary"]["service_page_count"], 2)
            self.assertTrue(payload["summary"]["traffic_gate_ok"])
            self.assertIn("Install the reverse proxy block", payload["server_changes"][0])
            self.assertEqual(payload["topology"]["public_mount_base"], "https://seoulmna.kr/_calc")


if __name__ == "__main__":
    unittest.main()
