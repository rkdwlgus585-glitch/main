import json
import tempfile
import unittest
from pathlib import Path

from scripts.bootstrap_wp_surface_lab_php_fallback import build_wp_surface_lab_php_fallback


class BootstrapWpSurfaceLabPhpFallbackTests(unittest.TestCase):
    def test_bootstrap_builds_site_root_and_sqlite_dropin(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            lab_root = base / "wp_surface_lab"
            wordpress_root = lab_root / "staging" / "wordpress"
            wp_content_root = lab_root / "staging" / "wp-content"
            (wordpress_root / "wp-admin").mkdir(parents=True, exist_ok=True)
            (wordpress_root / "index.php").write_text("<?php echo 'ok';", encoding="utf-8")
            sqlite_plugin = wp_content_root / "plugins" / "sqlite-database-integration"
            sqlite_plugin.mkdir(parents=True, exist_ok=True)
            (sqlite_plugin / "db.copy").write_text(
                "plugin={SQLITE_PLUGIN}\npath={SQLITE_IMPLEMENTATION_FOLDER_PATH}\n",
                encoding="utf-8",
            )
            existing_database = lab_root / "runtime" / "php_fallback" / "site" / "wp-content" / "database"
            existing_database.mkdir(parents=True, exist_ok=True)
            (existing_database / "lab.sqlite").write_text("keep", encoding="utf-8")
            wp_lab = base / "wp_lab.json"
            php_runtime = base / "php_runtime.json"
            wp_lab.write_text(json.dumps({"summary": {"staging_ready_count": 7}}, ensure_ascii=False), encoding="utf-8")
            php_runtime.write_text(
                json.dumps(
                    {
                        "summary": {"runtime_ready": True},
                        "runtime": {"localhost_url": "http://127.0.0.1:18081"},
                        "paths": {
                            "php_executable": str((lab_root / "runtime" / "php_fallback" / "php" / "php.exe").resolve()),
                            "php_ini": str((lab_root / "runtime" / "php_fallback" / "php" / "php.ini").resolve()),
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_wp_surface_lab_php_fallback(
                lab_root=lab_root,
                wp_lab_path=wp_lab,
                php_runtime_path=php_runtime,
            )

            self.assertTrue(payload["summary"]["bootstrap_ready"])
            db_dropin = Path(payload["paths"]["db_dropin"])
            wp_config = Path(payload["paths"]["wp_config"])
            self.assertTrue(db_dropin.exists())
            self.assertTrue(wp_config.exists())
            self.assertIn("sqlite-database-integration/load.php", db_dropin.read_text(encoding="utf-8"))
            self.assertIn("WP_HOME", wp_config.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["preserved_database"])
            self.assertTrue((Path(payload["paths"]["site_root"]) / "wp-content" / "database" / "lab.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
