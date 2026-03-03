import importlib
import unittest


allmod = importlib.import_module("all")


class AllSheetAnchorTest(unittest.TestCase):
    def test_analyze_sheet_rows_ignores_trace_only_tail_rows(self):
        header = [""] * 41
        listing = [""] * 41
        listing[0] = "7736"
        listing[2] = "build"
        listing[34] = "11845"

        trace_only = [""] * 41
        trace_only[36] = "raw"
        trace_only[37] = "primary_consult"
        trace_only[38] = "raw"
        trace_only[39] = "low"
        trace_only[40] = "N"

        ctx = allmod._analyze_sheet_rows([header, listing, trace_only])
        self.assertEqual(ctx["real_last_row"], 2)
        self.assertEqual(ctx["last_my_number"], 7736)
        self.assertEqual(ctx["existing_web_ids"].get("11845"), 2)

    def test_build_price_trace_updates_keeps_trace_only_row_unchanged(self):
        header = [""] * 41
        listing = [""] * 41
        listing[18] = "consult"

        trace_only = [""] * 41
        trace_only[36] = "raw"
        trace_only[37] = "primary_consult"
        trace_only[38] = "raw"
        trace_only[39] = "low"
        trace_only[40] = "N"

        payload = allmod._build_price_trace_updates([header, listing, trace_only])
        self.assertEqual(payload["total_rows"], 2)
        self.assertEqual(payload["changed_rows"], 1)
        self.assertEqual(payload["trace_values"][1], ["raw", "primary_consult", "raw", "low", "N"])
        self.assertEqual(payload["price_values"][1], [""])

    def test_detect_sheet_row_jump_reports_orphans(self):
        header = [""] * 41
        row_1 = [""] * 41
        row_1[0] = "1001"
        row_1[34] = "90001"

        orphan_1 = [""] * 41
        orphan_1[36] = "raw"
        orphan_1[37] = "primary_consult"

        orphan_2 = [""] * 41
        orphan_2[20] = "possible"

        row_2 = [""] * 41
        row_2[0] = "1002"
        row_2[34] = "90002"

        report = allmod._detect_sheet_row_jump([header, row_1, orphan_1, orphan_2, row_2])
        self.assertTrue(report["has_risk"])
        self.assertEqual(report["anchor_count"], 3)
        self.assertGreaterEqual(report["orphan_count"], 1)
        self.assertGreaterEqual(report["max_gap"], 1)


if __name__ == "__main__":
    unittest.main()

