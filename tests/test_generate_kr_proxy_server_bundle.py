import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_kr_proxy_server_bundle import build_kr_proxy_server_bundle


class GenerateKrProxyServerBundleTests(unittest.TestCase):
    def test_build_bundle_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            matrix = base / "matrix.json"
            checklist = base / "checklist.json"
            out = base / "bundle"

            matrix.write_text(
                json.dumps(
                    {
                        "summary": {
                            "matrix_ready": True,
                            "public_mount_path": "/_calc",
                            "upstream_origin": "https://calc.seoulmna.co.kr",
                            "cutover_ready": True,
                        },
                        "nginx": {"snippet": "location /_calc/ {}"},
                        "apache": {"snippet": 'ProxyPass "/_calc/" "https://calc.seoulmna.co.kr/widgets/"'},
                        "cloudflare": {"cache_rules": [{"match": "*", "action": "bypass_cache"}]},
                        "wordpress_cache": {"notes": ["Exclude /_calc/* from cache."]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            checklist.write_text(
                json.dumps(
                    {
                        "validation": [
                            {"description": "Confirm iframe src stays on .kr/_calc/*."},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_kr_proxy_server_bundle(matrix_path=matrix, checklist_path=checklist, output_dir=out)

            self.assertTrue(payload["summary"]["bundle_ready"])
            self.assertEqual(len(payload["files"]), 4)
            self.assertTrue((out / "nginx-calc-proxy.conf").exists())
            self.assertTrue((out / "apache-calc-proxy.conf").exists())
            self.assertTrue((out / "cloudflare-cache-rules.json").exists())
            self.assertTrue((out / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
