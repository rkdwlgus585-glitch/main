import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.scaffold_wp_surface_lab_runtime import build_wp_surface_lab_runtime


class ScaffoldWpSurfaceLabRuntimeTests(unittest.TestCase):
    @patch("scripts.scaffold_wp_surface_lab_runtime.shutil.which")
    def test_scaffold_creates_local_only_docker_runtime(self, mock_which):
        mock_which.return_value = None
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            wp_lab = base / "wp_lab.json"
            wp_assets = base / "wp_assets.json"
            wp_lab.write_text(
                json.dumps({"summary": {"staging_ready_count": 6}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_assets.write_text(
                json.dumps(
                    {
                        "theme": {"slug": "seoulmna-platform-child"},
                        "plugin": {"slug": "seoulmna-platform-bridge", "public_mount_base": "https://seoulmna.kr/_calc"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_wp_surface_lab_runtime(
                lab_root=base / "wp_surface_lab",
                wp_lab_path=wp_lab,
                wp_assets_path=wp_assets,
            )

            runtime_root = base / "wp_surface_lab" / "runtime"
            compose_path = runtime_root / "docker-compose.yml"
            self.assertTrue(compose_path.exists())
            self.assertTrue((runtime_root / ".env.local").exists())
            self.assertTrue((runtime_root / "README.md").exists())
            compose_text = compose_path.read_text(encoding="utf-8")
            self.assertIn('127.0.0.1:${WP_HTTP_PORT}:80', compose_text)
            self.assertIn("../staging/wordpress:/var/www/html", compose_text)
            self.assertIn("../staging/wp-content:/var/www/html/wp-content", compose_text)
            self.assertIn("\n  wpcli:\n", compose_text)
            env_text = (runtime_root / ".env.local").read_text(encoding="utf-8")
            self.assertIn("WP_PHP_FALLBACK_SITE_URL=http://127.0.0.1:18081", env_text)
            self.assertIn("WP_ACTIVE_RUNTIME=php_fallback", env_text)
            self.assertTrue(payload["summary"]["runtime_scaffold_ready"])
            self.assertFalse(payload["summary"]["docker_available"])
            self.assertEqual(payload["policy"]["public_mount_base"], "https://seoulmna.kr/_calc")
            self.assertEqual(payload["policy"]["php_fallback_localhost_url"], "http://127.0.0.1:18081")


if __name__ == "__main__":
    unittest.main()
