import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class TistoryRunCliTest(unittest.TestCase):
    def test_help_includes_commands(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tistory_ops" / "run.py"), "help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        out = proc.stdout
        self.assertIn("publish-listing", out)
        self.assertIn("daily-once", out)
        self.assertIn("publish-listing-api", out)
        self.assertIn("categories-api", out)
        self.assertIn("oauth", out)
        self.assertIn("verify-split", out)


if __name__ == "__main__":
    unittest.main()
