import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_wp_surface_lab import build_wp_surface_lab


PLUGIN_RESPONSES = {
    'astra-sites': {
        'name': 'Starter Templates',
        'slug': 'astra-sites',
        'version': '4.4.22',
        'download_link': 'https://downloads.wordpress.org/plugin/astra-sites.4.4.22.zip',
    },
    'ultimate-addons-for-gutenberg': {
        'name': 'Spectra',
        'slug': 'ultimate-addons-for-gutenberg',
        'version': '2.19.8',
        'download_link': 'https://downloads.wordpress.org/plugin/ultimate-addons-for-gutenberg.2.19.8.zip',
    },
    'wordpress-seo': {
        'name': 'Yoast SEO',
        'slug': 'wordpress-seo',
        'version': '27.1.1',
        'download_link': 'https://downloads.wordpress.org/plugin/wordpress-seo.27.1.1.zip',
    },
    'seo-by-rank-math': {
        'name': 'Rank Math SEO',
        'slug': 'seo-by-rank-math',
        'version': '1.0.265',
        'download_link': 'https://downloads.wordpress.org/plugin/seo-by-rank-math.1.0.265.zip',
    },
    'sqlite-database-integration': {
        'name': 'SQLite Database Integration',
        'slug': 'sqlite-database-integration',
        'version': '2.1.14',
        'download_link': 'https://downloads.wordpress.org/plugin/sqlite-database-integration.2.1.14.zip',
    },
}


def _zip_bytes(name: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(f'{name}/readme.txt', 'ok')
    return buffer.getvalue()


class _MockResponse:
    def __init__(self, *, json_payload=None, content=b'', status_code=200):
        self._json = json_payload
        self._content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'http_{self.status_code}')

    def json(self):
        return self._json

    def iter_content(self, chunk_size=8192):
        yield self._content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PrepareWpSurfaceLabTests(unittest.TestCase):
    @patch('scripts.prepare_wp_surface_lab.shutil.which')
    @patch('scripts.prepare_wp_surface_lab.requests.get')
    def test_build_lab_downloads_and_extracts_official_packages(self, mock_get, mock_which):
        mock_which.return_value = None

        def fake_get(url, *args, **kwargs):
            params = kwargs.get('params') or {}
            if 'version-check' in url:
                return _MockResponse(
                    json_payload={
                        'offers': [
                            {
                                'version': '6.9.1',
                                'packages': {'full': 'https://downloads.wordpress.org/release/wordpress-6.9.1.zip'},
                            }
                        ]
                    }
                )
            if 'themes/info' in url:
                return _MockResponse(
                    json_payload={
                        'name': 'Astra',
                        'slug': 'astra',
                        'version': '4.12.3',
                        'download_link': 'https://downloads.wordpress.org/theme/astra.4.12.3.zip',
                    }
                )
            if 'plugins/info' in url:
                slug = params.get('request[slug]')
                if slug in PLUGIN_RESPONSES:
                    return _MockResponse(json_payload=PLUGIN_RESPONSES[slug])
            if url.endswith('wordpress-6.9.1.zip'):
                return _MockResponse(content=_zip_bytes('wordpress'))
            if url.endswith('astra.4.12.3.zip'):
                return _MockResponse(content=_zip_bytes('astra'))
            for slug, payload in PLUGIN_RESPONSES.items():
                if url.endswith(f"{slug}.{payload['version']}.zip"):
                    return _MockResponse(content=_zip_bytes(slug))
            raise AssertionError(url)

        mock_get.side_effect = fake_get

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            surface_audit = base / 'surface_audit.json'
            surface_audit.write_text(
                json.dumps({'surfaces': {'kr': {'host': 'seoulmna.kr'}, 'co': {'host': 'seoulmna.co.kr'}}}, ensure_ascii=False),
                encoding='utf-8',
            )
            out = build_wp_surface_lab(
                lab_root=base / 'wp_surface_lab',
                surface_audit_path=surface_audit,
                timeout_sec=5,
                download_packages=True,
            )

            self.assertEqual(out['summary']['package_count'], 7)
            self.assertEqual(out['summary']['downloaded_count'], 7)
            self.assertEqual(out['summary']['staging_ready_count'], 7)
            self.assertFalse(out['summary']['runtime_ready'])
            self.assertIn('php_missing', out['summary']['runtime_blockers'])
            self.assertTrue((base / 'wp_surface_lab' / 'README.md').exists())
            self.assertTrue((base / 'wp_surface_lab' / 'manifests' / 'packages.json').exists())
            self.assertTrue((base / 'wp_surface_lab' / 'staging' / 'wp-content' / 'themes' / 'astra').exists())
            self.assertTrue((base / 'wp_surface_lab' / 'staging' / 'wp-content' / 'plugins' / 'astra-sites').exists())
            self.assertTrue((base / 'wp_surface_lab' / 'staging' / 'wp-content' / 'plugins' / 'ultimate-addons-for-gutenberg').exists())


if __name__ == '__main__':
    unittest.main()
