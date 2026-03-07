import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.scaffold_wp_surface_lab_runtime import build_wp_surface_lab_runtime
from scripts.validate_wp_surface_lab_runtime import build_wp_surface_lab_runtime_validation


class ValidateWpSurfaceLabRuntimeTests(unittest.TestCase):
    @patch("scripts.validate_wp_surface_lab_runtime._docker_compose_available")
    @patch("scripts.validate_wp_surface_lab_runtime.shutil.which")
    @patch("scripts.scaffold_wp_surface_lab_runtime.shutil.which")
    def test_validation_marks_scaffold_ready_when_docker_missing(self, scaffold_which, validate_which, mock_compose):
        scaffold_which.return_value = None
        validate_which.return_value = None
        mock_compose.return_value = False

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            wp_lab = base / "wp_lab.json"
            wp_assets = base / "wp_assets.json"
            runtime_json = base / "runtime.json"
            php_runtime = base / "php_runtime.json"
            php_fallback = base / "php_fallback.json"
            wp_lab.write_text(
                json.dumps({"summary": {"staging_ready_count": 6}}, ensure_ascii=False),
                encoding="utf-8",
            )
            wp_assets.write_text(
                json.dumps(
                    {
                        "theme": {"slug": "seoulmna-platform-child", "ready": True},
                        "plugin": {"slug": "seoulmna-platform-bridge", "ready": True, "public_mount_base": "https://seoulmna.kr/_calc"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            runtime_payload = build_wp_surface_lab_runtime(
                lab_root=base / "wp_surface_lab",
                wp_lab_path=wp_lab,
                wp_assets_path=wp_assets,
            )
            runtime_json.write_text(json.dumps(runtime_payload, ensure_ascii=False), encoding="utf-8")
            php_runtime.write_text(json.dumps({"summary": {"runtime_ready": False}}, ensure_ascii=False), encoding="utf-8")
            php_fallback.write_text(json.dumps({"summary": {"bootstrap_ready": False}}, ensure_ascii=False), encoding="utf-8")

            payload = build_wp_surface_lab_runtime_validation(
                runtime_path=runtime_json,
                wp_lab_path=wp_lab,
                wp_assets_path=wp_assets,
                php_runtime_path=php_runtime,
                php_fallback_path=php_fallback,
            )

            self.assertTrue(payload["summary"]["runtime_scaffold_ready"])
            self.assertFalse(payload["summary"]["runtime_ready"])
            self.assertFalse(payload["summary"]["runtime_running"])
            self.assertIn("docker_missing", payload["summary"]["blockers"])
            self.assertTrue(payload["checks"]["local_bind_only"])
            self.assertIn("Install Docker Desktop", payload["handoff"]["next_actions"][0])


if __name__ == "__main__":
    unittest.main()
