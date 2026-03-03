import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "tistory_ops" / "verify_tistory_split.py"
SPEC = importlib.util.spec_from_file_location("verify_tistory_split", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class TistoryVerifySplitTest(unittest.TestCase):
    def test_run_checks_ok(self):
        result = MOD.run_checks()
        self.assertIn("ok", result)
        self.assertTrue(result["ok"], msg=result)


if __name__ == "__main__":
    unittest.main()

