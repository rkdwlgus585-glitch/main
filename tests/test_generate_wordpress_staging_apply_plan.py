import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_wordpress_staging_apply_plan import build_wordpress_staging_apply_plan


class GenerateWordpressStagingApplyPlanTests(unittest.TestCase):
    def test_build_apply_plan_maps_pages_to_blueprints(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            blueprints = base / "blueprints.json"
            cutover = base / "cutover.json"
            runtime = base / "runtime.json"
            runtime_validation = base / "runtime_validation.json"
            php_runtime = base / "php_runtime.json"
            php_fallback = base / "php_fallback.json"
            wp_apply = base / "wp_apply.json"
            ia.write_text(
                json.dumps(
                    {
                        "pages": [
                            {"page_id": "home", "slug": "/", "wordpress_page_slug": "home", "title": "홈", "calculator_policy": "cta_only_no_iframe"},
                            {"page_id": "yangdo", "slug": "/yangdo", "wordpress_page_slug": "yangdo", "title": "양도가", "calculator_policy": "lazy_gate_shortcode"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            blueprints.write_text(
                json.dumps(
                    {
                        "pages": [
                            {"page_id": "home", "blueprint_file": "home.html"},
                            {"page_id": "yangdo", "blueprint_file": "yangdo.html"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            cutover.write_text(
                json.dumps({"summary": {"cutover_ready": True}, "verification": ["check"], "rollback": {"trigger": "x"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            runtime.write_text(
                json.dumps(
                    {
                        "commands": {
                            "start": "docker compose --env-file .env.local up -d",
                            "bootstrap_core": "wp core install",
                            "activate_theme": "wp theme activate seoulmna-platform-child",
                            "activate_bridge_plugin": "wp plugin activate seoulmna-platform-bridge",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_validation.write_text(
                json.dumps(
                    {
                        "summary": {"runtime_scaffold_ready": True, "runtime_ready": False, "runtime_running": False, "runtime_mode": "none"},
                        "handoff": {"localhost_url": "http://127.0.0.1:18080", "next_actions": ["Install Docker Desktop"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            php_runtime.write_text(json.dumps({"commands": {"start_server": "powershell -File start-php.ps1"}}, ensure_ascii=False), encoding="utf-8")
            php_fallback.write_text(json.dumps({"commands": {"install_url": "http://127.0.0.1:18081/wp-admin/install.php", "admin_url": "http://127.0.0.1:18081/wp-admin/"}}, ensure_ascii=False), encoding="utf-8")
            wp_apply.write_text(
                json.dumps(
                    {
                        "summary": {"bundle_ready": True},
                        "commands": {"dry_run": "py -3 scripts/apply_wp_surface_lab_blueprints.py", "apply": "docker compose run --rm wpcli eval-file"},
                        "artifacts": {"manifest_file": "manifest.json", "php_bundle_file": "apply-platform-blueprints.php"},
                        "next_actions": ["Run dry-run before apply"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_wordpress_staging_apply_plan(
                ia_path=ia,
                blueprints_path=blueprints,
                cutover_path=cutover,
                runtime_path=runtime,
                runtime_validation_path=runtime_validation,
                php_runtime_path=php_runtime,
                php_fallback_path=php_fallback,
                wp_apply_path=wp_apply,
            )

            self.assertEqual(payload["summary"]["page_step_count"], 2)
            self.assertTrue(payload["summary"]["cutover_ready"])
            self.assertTrue(payload["summary"]["runtime_scaffold_ready"])
            self.assertEqual(payload["page_steps"][0]["blueprint_file"], "home.html")
            self.assertEqual(payload["page_steps"][0]["wordpress_page_slug"], "home")
            self.assertIn("lazy gate shortcode", payload["page_steps"][1]["required_step"])
            self.assertEqual(payload["runtime_bootstrap"]["localhost_url"], "http://127.0.0.1:18080")
            self.assertEqual(payload["runtime_bootstrap"]["runtime_mode"], "none")
            self.assertEqual(payload["runtime_bootstrap"]["activation_mode"], "pending_runtime_selection")
            self.assertTrue(payload["wpcli_apply"]["bundle_ready"])
            self.assertEqual(payload["wpcli_apply"]["manifest_file"], "manifest.json")
            self.assertIn("apply_wp_surface_lab_blueprints.py", payload["wpcli_apply"]["dry_run_command"])

    def test_prefers_php_fallback_commands_when_runtime_mode_is_php_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            ia = base / "ia.json"
            blueprints = base / "blueprints.json"
            cutover = base / "cutover.json"
            runtime = base / "runtime.json"
            runtime_validation = base / "runtime_validation.json"
            php_runtime = base / "php_runtime.json"
            php_fallback = base / "php_fallback.json"
            wp_apply = base / "wp_apply.json"
            ia.write_text(json.dumps({"pages": []}, ensure_ascii=False), encoding="utf-8")
            blueprints.write_text(json.dumps({"pages": []}, ensure_ascii=False), encoding="utf-8")
            cutover.write_text(json.dumps({"summary": {"cutover_ready": True}}, ensure_ascii=False), encoding="utf-8")
            runtime.write_text(json.dumps({"commands": {"start": "docker up", "bootstrap_core": "docker install", "activate_theme": "docker theme", "activate_bridge_plugin": "docker plugin"}}, ensure_ascii=False), encoding="utf-8")
            runtime_validation.write_text(
                json.dumps(
                    {
                        "summary": {"runtime_scaffold_ready": True, "runtime_ready": True, "runtime_running": True, "runtime_mode": "php_fallback"},
                        "handoff": {"localhost_url": "http://127.0.0.1:18081", "next_actions": []},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            php_runtime.write_text(json.dumps({"commands": {"start_server": "powershell -File start-php.ps1"}}, ensure_ascii=False), encoding="utf-8")
            php_fallback.write_text(
                json.dumps(
                    {"commands": {"start_server": "powershell -File start-fallback.ps1", "install_url": "http://127.0.0.1:18081/wp-admin/install.php", "admin_url": "http://127.0.0.1:18081/wp-admin/"}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wp_apply.write_text(
                json.dumps(
                    {
                        "summary": {"bundle_ready": True},
                        "commands": {"dry_run": "py -3 scripts/apply_wp_surface_lab_blueprints.py", "apply": "docker apply", "apply_php_fallback": "php apply.php"},
                        "artifacts": {"manifest_file": "manifest.json", "php_bundle_file": "apply.php", "standalone_php_bundle_file": "apply-standalone.php"},
                        "next_actions": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_wordpress_staging_apply_plan(
                ia_path=ia,
                blueprints_path=blueprints,
                cutover_path=cutover,
                runtime_path=runtime,
                runtime_validation_path=runtime_validation,
                php_runtime_path=php_runtime,
                php_fallback_path=php_fallback,
                wp_apply_path=wp_apply,
            )

            self.assertEqual(payload["runtime_bootstrap"]["runtime_mode"], "php_fallback")
            self.assertEqual(payload["runtime_bootstrap"]["activation_mode"], "wp_admin_manual_activation")
            self.assertEqual(payload["runtime_bootstrap"]["start_command"], "powershell -File start-fallback.ps1")
            self.assertEqual(payload["runtime_bootstrap"]["bootstrap_core_command"], "http://127.0.0.1:18081/wp-admin/install.php")
            self.assertEqual(payload["runtime_bootstrap"]["activate_theme_command"], "http://127.0.0.1:18081/wp-admin/")
            self.assertEqual(payload["wpcli_apply"]["apply_command"], "php apply.php")
            self.assertEqual(payload["wpcli_apply"]["apply_mode"], "php_fallback")
            self.assertEqual(payload["wpcli_apply"]["standalone_php_bundle_file"], "apply-standalone.php")


if __name__ == "__main__":
    unittest.main()
