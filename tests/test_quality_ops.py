import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class QualityOpsTest(unittest.TestCase):
    def test_batch_smoke_check_strict(self):
        cmd = [sys.executable, "scripts/batch_smoke_check.py", "--strict"]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=output)
        self.assertIn("[batch-smoke] summary: ok=True", output)

    def test_cmd_smoke_check_strict(self):
        cmd = [sys.executable, "scripts/cmd_smoke_check.py", "--strict"]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=output)
        self.assertIn("[cmd-smoke] summary: ok=True", output)

    def test_show_entrypoints_json_contains_role_sections(self):
        cmd = [sys.executable, "scripts/show_entrypoints.py", "--json"]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=output)
        payload = json.loads(proc.stdout)
        self.assertIn("root_shims", payload)
        self.assertIn("real_launchers", payload)
        self.assertIn("ops_runners", payload)
        self.assertIn("unclassified_entrypoints", payload)
        self.assertEqual(payload.get("unclassified_entrypoints"), [])

    def test_show_entrypoints_strict_has_no_unclassified(self):
        cmd = [sys.executable, "scripts/show_entrypoints.py", "--strict"]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=output)
        self.assertIn("unclassified=0", output)

    def test_quality_trend_report_detects_new_fail_and_repeat_warning(self):
        with tempfile.TemporaryDirectory() as td:
            log_dir = Path(td)
            base_time = datetime.now() - timedelta(days=1)

            prev_report = {
                "started_at": (base_time - timedelta(hours=3)).isoformat(),
                "ok": True,
                "results": [
                    {
                        "automation": "mnakr",
                        "contract_file": "quality_contracts/mnakr.contract.json",
                        "checks": [
                            {"id": "warn_old", "type": "json_report", "required": False, "ok": False},
                        ],
                    }
                ],
            }
            latest_report = {
                "started_at": base_time.isoformat(),
                "ok": False,
                "results": [
                    {
                        "automation": "mnakr",
                        "contract_file": "quality_contracts/mnakr.contract.json",
                        "checks": [
                            {"id": "fail_new", "type": "command", "required": True, "ok": False},
                            {"id": "warn_old", "type": "json_report", "required": False, "ok": False},
                        ],
                    }
                ],
            }

            (log_dir / "quality_daily_20260220_100000.json").write_text(
                json.dumps(prev_report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (log_dir / "quality_daily_20260220_130000.json").write_text(
                json.dumps(latest_report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                "scripts/quality_trend_report.py",
                "--logs-dir",
                str(log_dir),
                "--window-days",
                "7",
                "--quiet",
            ]
            proc = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            self.assertEqual(proc.returncode, 0, msg=output)

            trend_latest = log_dir / "quality_trend_latest.json"
            self.assertTrue(trend_latest.exists(), msg=output)
            trend = json.loads(trend_latest.read_text(encoding="utf-8"))

            new_fail_keys = {f"{x.get('automation')}:{x.get('check_id')}" for x in trend.get("new_failures", [])}
            repeat_warn_keys = {f"{x.get('automation')}:{x.get('check_id')}" for x in trend.get("repeated_warnings", [])}
            self.assertIn("mnakr:fail_new", new_fail_keys)
            self.assertIn("mnakr:warn_old", repeat_warn_keys)
            self.assertEqual(trend.get("summary", {}).get("new_failure_count"), 1)
            self.assertEqual(trend.get("summary", {}).get("repeated_warning_count"), 1)


if __name__ == "__main__":
    unittest.main()
