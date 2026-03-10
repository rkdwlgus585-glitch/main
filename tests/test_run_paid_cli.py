import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class RunPaidCliTest(unittest.TestCase):
    def test_help_includes_paid_commands(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "ALL" / "paid_ops" / "run.py"), "help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        out = proc.stdout
        self.assertIn("gabji-report", out)
        self.assertIn("gb2-audit", out)
        self.assertIn("verify-split", out)


if __name__ == "__main__":
    unittest.main()
