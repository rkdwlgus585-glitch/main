import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.install_wp_surface_lab_php_fallback import build_wp_surface_lab_php_install


class InstallWpSurfaceLabPhpFallbackTests(unittest.TestCase):
    def test_marks_korean_already_installed_as_success(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            runtime = base / "runtime.json"
            php_fallback = base / "php_fallback.json"
            runtime_root = base / "runtime"
            runtime_root.mkdir(parents=True, exist_ok=True)
            (runtime_root / ".env.local").write_text(
                "\n".join(
                    [
                        "WP_ADMIN_USER=admin",
                        "WP_ADMIN_PASSWORD=change-me-before-sharing",
                        "WP_ADMIN_EMAIL=lab@example.com",
                        "WP_SITE_TITLE=Lab",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            runtime.write_text(json.dumps({"runtime_root": str(runtime_root)}, ensure_ascii=False), encoding="utf-8")
            php_fallback.write_text(
                json.dumps(
                    {"site_url": "http://127.0.0.1:18081", "commands": {"install_url": "http://127.0.0.1:18081/wp-admin/install.php"}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch(
                "scripts.install_wp_surface_lab_php_fallback._http_open",
                return_value="<html><body><h1>이미 설치됨</h1><a href='/wp-login.php'>로그인</a></body></html>",
            ):
                payload = build_wp_surface_lab_php_install(runtime_path=runtime, php_fallback_path=php_fallback)

            self.assertFalse(payload["summary"]["attempted"])
            self.assertTrue(payload["summary"]["already_installed"])
            self.assertTrue(payload["summary"]["install_ok"])
            self.assertEqual(payload["credentials"]["admin_password"], "Codex!Lab2026#Ready")


if __name__ == "__main__":
    unittest.main()
