import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1].parent / "ALL" / "paid_ops" / "verify_paid_legacy_split.py"
SPEC = importlib.util.spec_from_file_location("verify_paid_legacy_split", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class VerifyPaidLegacySplitTest(unittest.TestCase):
    def test_run_py_has_no_paid_commands(self):
        row = MOD._check_run_py_legacy()
        self.assertTrue(row["ok"], msg=row)

    def test_legacy_launchers_do_not_call_paid(self):
        row = MOD._check_no_paid_tokens_in_legacy_launchers()
        self.assertTrue(row["ok"], msg=row)

    def test_run_checks(self):
        result = MOD.run_checks()
        self.assertIn("ok", result)
        self.assertTrue(result["ok"], msg=result)


if __name__ == "__main__":
    unittest.main()
