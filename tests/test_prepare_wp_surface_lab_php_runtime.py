import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_wp_surface_lab_php_runtime import build_wp_surface_lab_php_runtime


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class PrepareWpSurfaceLabPhpRuntimeTests(unittest.TestCase):
    @patch("scripts.prepare_wp_surface_lab_php_runtime._run_php_command")
    @patch("scripts.prepare_wp_surface_lab_php_runtime.requests.get")
    def test_build_php_runtime_uses_official_windows_release_metadata(self, mock_get, mock_run_php):
        releases = {
            "8.3": {
                "nts-vs16-x64": {
                    "mtime": "2025-12-17T13:50:25+01:00",
                    "zip": {
                        "path": "php-8.3.29-nts-Win32-vs16-x64.zip",
                        "sha256": "abc123",
                    },
                }
            }
        }
        mock_get.return_value = _Response(releases)
        mock_run_php.side_effect = [
            {"ok": True, "stdout": "PHP 8.3.29", "stderr": "", "returncode": 0},
            {"ok": True, "stdout": "pdo_sqlite\nsqlite3\nopenssl", "stderr": "", "returncode": 0},
        ]

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            lab_root = base / "wp_surface_lab"
            wp_lab = base / "wp_lab.json"
            wp_lab.write_text(json.dumps({"summary": {"staging_ready_count": 7}}, ensure_ascii=False), encoding="utf-8")
            extract_root = lab_root / "runtime" / "php_fallback" / "php"
            extract_root.mkdir(parents=True, exist_ok=True)
            (extract_root / "php.exe").write_text("", encoding="utf-8")
            (extract_root / "php.ini-production").write_text("; base", encoding="utf-8")

            payload = build_wp_surface_lab_php_runtime(
                lab_root=lab_root,
                wp_lab_path=wp_lab,
                timeout_sec=10,
                download_runtime=False,
            )

            self.assertEqual(payload["package"]["archive_name"], "php-8.3.29-nts-Win32-vs16-x64.zip")
            self.assertTrue(payload["summary"]["php_binary_ready"])
            self.assertTrue(payload["summary"]["php_module_ready"])
            self.assertEqual(payload["runtime"]["localhost_url"], "http://127.0.0.1:18081")

    @patch("scripts.prepare_wp_surface_lab_php_runtime._extract")
    @patch("scripts.prepare_wp_surface_lab_php_runtime._download")
    @patch("scripts.prepare_wp_surface_lab_php_runtime._run_php_command")
    @patch("scripts.prepare_wp_surface_lab_php_runtime.requests.get")
    def test_skips_reextract_when_php_runtime_already_exists(self, mock_get, mock_run_php, mock_download, mock_extract):
        releases = {
            "8.3": {
                "nts-vs16-x64": {
                    "mtime": "2025-12-17T13:50:25+01:00",
                    "zip": {
                        "path": "php-8.3.29-nts-Win32-vs16-x64.zip",
                        "sha256": "abc123",
                    },
                }
            }
        }
        mock_get.return_value = _Response(releases)
        mock_run_php.side_effect = [
            {"ok": True, "stdout": "PHP 8.3.29", "stderr": "", "returncode": 0},
            {"ok": True, "stdout": "pdo_sqlite\nsqlite3\nopenssl", "stderr": "", "returncode": 0},
        ]

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            lab_root = base / "wp_surface_lab"
            wp_lab = base / "wp_lab.json"
            wp_lab.write_text(json.dumps({"summary": {"staging_ready_count": 7}}, ensure_ascii=False), encoding="utf-8")
            extract_root = lab_root / "runtime" / "php_fallback" / "php"
            extract_root.mkdir(parents=True, exist_ok=True)
            (extract_root / "php.exe").write_text("", encoding="utf-8")
            (extract_root / "php.ini-production").write_text("; base", encoding="utf-8")

            payload = build_wp_surface_lab_php_runtime(
                lab_root=lab_root,
                wp_lab_path=wp_lab,
                timeout_sec=10,
                download_runtime=True,
                refresh_existing_runtime=False,
            )

            mock_download.assert_not_called()
            mock_extract.assert_not_called()
            self.assertTrue(payload["summary"]["skipped_extract"])


if __name__ == "__main__":
    unittest.main()
