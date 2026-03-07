import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_wp_surface_lab_blueprints import build_wp_surface_lab_apply_bundle


class ApplyWpSurfaceLabBlueprintsTests(unittest.TestCase):
    def test_build_bundle_generates_manifest_and_php_eval_file(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            blueprints = base / "blueprints.json"
            runtime = base / "runtime.json"
            runtime_validation = base / "runtime_validation.json"
            php_runtime = base / "php_runtime.json"
            php_fallback = base / "php_fallback.json"
            wp_assets = base / "wp_assets.json"
            cutover = base / "cutover.json"

            ia.write_text(
                json.dumps(
                    {
                        "summary": {"front_page_id": "home", "front_page_slug": "home"},
                        "navigation": {
                            "primary": [
                                {"label": "플랫폼 소개", "href": "/"},
                                {"label": "양도가", "href": "/yangdo"},
                            ]
                        },
                        "pages": [
                            {
                                "page_id": "home",
                                "slug": "/",
                                "wordpress_page_slug": "home",
                                "title": "메인",
                                "calculator_policy": "cta_only_no_iframe",
                            },
                            {
                                "page_id": "yangdo",
                                "slug": "/yangdo",
                                "wordpress_page_slug": "yangdo",
                                "title": "양도가",
                                "calculator_policy": "lazy_gate_shortcode",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            blueprints.write_text(
                json.dumps(
                    {
                        "blueprint_root": str(base / "staging" / "wp-content" / "themes" / "seoulmna-platform-child" / "blueprints"),
                        "pages": [
                            {"page_id": "home", "blueprint_file": str(base / "home.html")},
                            {"page_id": "yangdo", "blueprint_file": str(base / "yangdo.html")},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_root = base / "runtime"
            runtime_root.mkdir(parents=True, exist_ok=True)
            (runtime_root / ".env.local").write_text(
                "WP_SITE_URL=http://127.0.0.1:18080\nWP_SITE_TITLE=Lab\nWP_ADMIN_USER=admin\nWP_ADMIN_PASSWORD=secret\nWP_ADMIN_EMAIL=lab@example.com\n",
                encoding="utf-8",
            )
            runtime.write_text(
                json.dumps(
                    {
                        "runtime_root": str(runtime_root),
                        "runtime_probe": {"docker_available": False},
                        "commands": {
                            "start": "docker compose --env-file .env.local up -d",
                            "activate_theme": "docker compose run --rm wpcli theme activate seoulmna-platform-child",
                            "activate_bridge_plugin": "docker compose run --rm wpcli plugin activate seoulmna-platform-bridge",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_validation.write_text(
                json.dumps(
                    {
                        "summary": {
                            "runtime_scaffold_ready": True,
                            "runtime_ready": False,
                            "runtime_mode": "none",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            php_runtime.write_text(
                json.dumps(
                    {
                        "summary": {"php_binary_ready": True},
                        "paths": {
                            "php_executable": str(base / "php" / "php.exe"),
                            "php_ini": str(base / "php" / "php.ini"),
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            php_fallback.write_text(
                json.dumps(
                    {
                        "summary": {"bootstrap_ready": False},
                        "paths": {"site_root": str(base / "site_root")},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wp_assets.write_text(
                json.dumps(
                    {"theme": {"slug": "seoulmna-platform-child"}, "plugin": {"slug": "seoulmna-platform-bridge"}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            cutover.write_text(json.dumps({"summary": {"cutover_ready": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_wp_surface_lab_apply_bundle(
                ia_path=ia,
                blueprints_path=blueprints,
                runtime_path=runtime,
                runtime_validation_path=runtime_validation,
                php_runtime_path=php_runtime,
                php_fallback_path=php_fallback,
                wp_assets_path=wp_assets,
                cutover_path=cutover,
            )

            manifest_file = Path(payload["artifacts"]["manifest_file"])
            php_bundle_file = Path(payload["artifacts"]["php_bundle_file"])
            standalone_php_bundle_file = Path(payload["artifacts"]["standalone_php_bundle_file"])
            self.assertTrue(manifest_file.exists())
            self.assertTrue(php_bundle_file.exists())
            self.assertTrue(standalone_php_bundle_file.exists())
            self.assertTrue(payload["summary"]["bundle_ready"])
            self.assertEqual(payload["summary"]["front_page_slug"], "home")
            self.assertEqual(payload["summary"]["runtime_mode"], "none")
            self.assertEqual(payload["manifest"]["pages"][0]["wordpress_page_slug"], "home")
            self.assertIn("wp eval-file", payload["commands"]["apply"])
            self.assertIn("apply-platform-blueprints-standalone.php", payload["commands"]["apply_php_fallback"])
            self.assertIn("home", manifest_file.read_text(encoding="utf-8"))
            self.assertIn("page_results", php_bundle_file.read_text(encoding="utf-8"))
            self.assertIn("permalink_structure", php_bundle_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
