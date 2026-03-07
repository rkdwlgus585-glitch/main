import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_system_risk_map import main, parse_discover_output


SAMPLE_OUTPUT = """
....................FF..E
======================================================================
FAIL: test_build_price_trace_updates_no_change_when_already_synced (test_all_price_trace.AllPriceTraceTest.test_build_price_trace_updates_no_change_when_already_synced)
----------------------------------------------------------------------
trace

======================================================================
FAIL: test_run_checks_ok (test_tistory_verify_split.TistoryVerifySplitTest.test_run_checks_ok)
----------------------------------------------------------------------
trace

======================================================================
ERROR: test_daily_once_picks_7540_then_updates_state_on_success (test_tistory_daily_publish.TistoryDailyPublishTest.test_daily_once_picks_7540_then_updates_state_on_success)
----------------------------------------------------------------------
trace

----------------------------------------------------------------------
Ran 314 tests in 9.173s

FAILED (failures=2, errors=1)
""".strip()


class GenerateSystemRiskMapTests(unittest.TestCase):
    def test_parse_discover_output_classifies_groups(self):
        payload = parse_discover_output(SAMPLE_OUTPUT, 1)
        self.assertEqual(payload["run_summary"]["ran_tests"], 314)
        self.assertEqual(payload["run_summary"]["failures"], 2)
        self.assertEqual(payload["run_summary"]["errors"], 1)
        self.assertEqual(payload["group_summary"]["listing_support_pipeline"]["issue_count"], 1)
        self.assertEqual(payload["group_summary"]["legacy_blog_tistory"]["issue_count"], 2)
        self.assertEqual(payload["business_core_status"], "green")

    def test_cli_writes_outputs_from_input_file(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "discover.txt"
            src.write_text(SAMPLE_OUTPUT, encoding="utf-8")
            json_path = Path(td) / "risk.json"
            md_path = Path(td) / "risk.md"
            argv = [
                "generate_system_risk_map.py",
                "--input-file",
                str(src),
                "--json",
                str(json_path),
                "--md",
                str(md_path),
            ]
            with patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_summary"]["issue_count"], 3)
            self.assertIn("legacy_blog_tistory", payload["group_summary"])
            self.assertIn("System Risk Map", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
