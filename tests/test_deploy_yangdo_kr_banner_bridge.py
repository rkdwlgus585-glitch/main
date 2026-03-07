import base64
import gzip
import tempfile
import unittest
from pathlib import Path

from scripts import deploy_yangdo_kr_banner_bridge as bridge


class DeployYangdoKrBannerBridgeTests(unittest.TestCase):
    def test_write_gzip_copy_and_base64_payload_page(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "payload.json"
            target = root / "payload.json.gz"
            source.write_text('{"hello":"world"}', encoding="utf-8")

            bridge._write_gzip_copy(source, target)
            raw = gzip.decompress(target.read_bytes()).decode("utf-8")
            self.assertEqual(raw, '{"hello":"world"}')

            encoded = bridge._gzip_file_to_base64(target)
            self.assertEqual(base64.b64decode(encoded), target.read_bytes())

            html = bridge._build_payload_page_html(encoded, canonical_url="https://seoulmna.kr/ai-license-acquisition-calculator-2/")
            self.assertIn('id="smna-permit-payload"', html)
            self.assertIn(encoded, html)
            self.assertIn("noindex,nofollow,noarchive", html)
            self.assertIn("https://seoulmna.kr/ai-license-acquisition-calculator-2/", html)

    def test_build_payload_rest_data_url(self):
        url = bridge._build_payload_rest_data_url("https://seoulmna.kr/wp-json/wp/v2", 1810)
        self.assertEqual(
            url,
            "https://seoulmna.kr/wp-json/wp/v2/pages/1810?_fields=content.rendered,modified&context=view",
        )

    def test_build_payload_rest_data_url_for_posts(self):
        url = bridge._build_payload_rest_data_url(
            "https://seoulmna.kr/wp-json/wp/v2",
            1827,
            collection="posts",
        )
        self.assertEqual(
            url,
            "https://seoulmna.kr/wp-json/wp/v2/posts/1827?_fields=content.rendered,modified&context=view",
        )


if __name__ == "__main__":
    unittest.main()
