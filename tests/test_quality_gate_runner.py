import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _run_runner(contract_dir: Path, contracts: str):
    cmd = [
        sys.executable,
        "scripts/quality_gate_runner.py",
        "--contract-dir",
        str(contract_dir),
        "--contracts",
        contracts,
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
    match = re.search(r"report:\s+([^\s]+)", output)
    report_path = None
    if match:
        report_path = ROOT / match.group(1)
    return proc, report_path, output


class QualityGateRunnerTest(unittest.TestCase):
    def test_command_string_check_runs_with_shell_default(self):
        with tempfile.TemporaryDirectory() as td:
            contract_dir = Path(td)
            contract = {
                "automation": "echo_contract",
                "checks": [
                    {
                        "id": "echo_string_command",
                        "type": "command",
                        "command": "echo quality-ok"
                    }
                ],
            }
            (contract_dir / "echo_contract.contract.json").write_text(
                json.dumps(contract, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            proc, report_path, output = _run_runner(contract_dir, "echo_contract")
            self.assertEqual(proc.returncode, 0, msg=output)
            self.assertIsNotNone(report_path, msg=output)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])

    def test_invalid_contract_shape_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            contract_dir = Path(td)
            contract = {
                "automation": "invalid_shape",
                "checks": [
                    {
                        "id": "bad_json_report",
                        "type": "json_report",
                        "glob": "logs/qa_report_*.json",
                        "must_have_keys": "pass_gate"
                    }
                ],
            }
            (contract_dir / "invalid_shape.contract.json").write_text(
                json.dumps(contract, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            proc, report_path, output = _run_runner(contract_dir, "invalid_shape")
            self.assertNotEqual(proc.returncode, 0, msg=output)
            self.assertIsNotNone(report_path, msg=output)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            result = report["results"][0]
            self.assertFalse(result["ok"])
            issues = result.get("validation_issues", [])
            self.assertTrue(any("must_have_keys" in issue for issue in issues))

    def test_keep_days_zero_disables_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            contract_dir = Path(td)
            contract = {
                "automation": "cleanup_off",
                "checks": [
                    {
                        "id": "exists_check",
                        "type": "file_exists",
                        "paths": ["utils.py"]
                    }
                ],
            }
            (contract_dir / "cleanup_off.contract.json").write_text(
                json.dumps(contract, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            cmd = [
                sys.executable,
                "scripts/quality_gate_runner.py",
                "--contract-dir",
                str(contract_dir),
                "--contracts",
                "cleanup_off",
                "--keep-days",
                "0",
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
            match = re.search(r"report:\s+([^\s]+)", output)
            self.assertIsNotNone(match, msg=output)
            report_path = ROOT / match.group(1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report.get("cleanup", {}).get("enabled"), False)


if __name__ == "__main__":
    unittest.main()
