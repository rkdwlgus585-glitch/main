import importlib
import unittest


allmod = importlib.import_module("all")


class AllPriceTraceTest(unittest.TestCase):
    def test_resolve_trace_primary_numeric(self):
        out = allmod.resolve_yangdo_price_trace("2.5억~2.7억", "", "")
        self.assertEqual(out["price"], "2.7억")
        self.assertEqual(out["source"], "primary")
        self.assertEqual(out["confidence"], "high")
        self.assertEqual(out["fallback_used"], "N")

    def test_resolve_trace_claim_fallback(self):
        out = allmod.resolve_yangdo_price_trace("협의", "0.9억~1억", "")
        self.assertEqual(out["price"], "1억")
        self.assertEqual(out["source"], "claim")
        self.assertEqual(out["confidence"], "high")
        self.assertEqual(out["fallback_used"], "Y")

    def test_resolve_trace_memo_fallback(self):
        out = allmod.resolve_yangdo_price_trace("협의", "", "청구 양도가 3.1억~3.3억")
        self.assertEqual(out["price"], "3.3억")
        self.assertEqual(out["source"], "memo")
        self.assertEqual(out["confidence"], "medium")
        self.assertEqual(out["fallback_used"], "Y")

    def test_resolve_trace_ignores_uid_like_claim_text(self):
        out = allmod.resolve_yangdo_price_trace("협의", "10004 토공", "")
        self.assertEqual(out["price"], "협의")
        self.assertIn(out["source"], {"primary_consult", "claim_consult"})

    def test_build_sheet_row_appends_price_trace_columns(self):
        item = {
            "license": "전기",
            "claim_price": "0.9억~1억",
            "uid": "12345",
            "price_raw": "협의",
            "price_source": "claim",
            "price_evidence": "0.9억~1억",
            "price_confidence": "high",
            "price_fallback": "Y",
        }
        row = allmod._build_sheet_row(item, 1)
        self.assertEqual(row[33], "0.9억~1억")
        self.assertEqual(row[34], "12345")
        self.assertEqual(row[-5:], ["협의", "claim", "0.9억~1억", "high", "Y"])

    def test_col_to_a1(self):
        self.assertEqual(allmod._col_to_a1(1), "A")
        self.assertEqual(allmod._col_to_a1(26), "Z")
        self.assertEqual(allmod._col_to_a1(27), "AA")
        self.assertEqual(allmod._col_to_a1(37), "AK")

    def test_build_price_trace_updates_counts_recovered(self):
        header = [""] * 41
        row = [""] * 41
        row[18] = "협의"      # C19
        row[33] = "0.9억~1억"  # C34

        out = allmod._build_price_trace_updates([header, row])
        self.assertEqual(out["total_rows"], 1)
        self.assertEqual(out["changed_rows"], 1)
        self.assertEqual(out["recovered_rows"], 1)
        self.assertEqual(out["price_values"][0][0], "1억")
        self.assertEqual(out["trace_values"][0][1], "claim")
        self.assertEqual(out["trace_values"][0][3], "high")
        self.assertEqual(out["trace_values"][0][4], "Y")

    def test_build_price_trace_updates_no_change_when_already_synced(self):
        header = [""] * 41
        row = [""] * 41
        row[18] = "1억"
        row[36] = "1억"
        row[37] = "primary"
        row[38] = "1억"
        row[39] = "high"
        row[40] = "N"
        row[33] = "0.9억~1억"

        out = allmod._build_price_trace_updates([header, row])
        self.assertEqual(out["total_rows"], 1)
        self.assertEqual(out["changed_rows"], 0)
        self.assertEqual(out["recovered_rows"], 0)

    def test_collect_low_confidence_rows_from_trace_columns(self):
        header = [""] * 41
        row = [""] * 41
        row[0] = "100"
        row[18] = "협의"
        row[31] = "비고"
        row[33] = ""
        row[36] = "협의"
        row[37] = "primary_consult"
        row[38] = "협의"
        row[39] = "low"
        row[40] = "N"

        rows = allmod._collect_low_confidence_rows([header, row], limit=0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["row"], 2)
        self.assertEqual(rows[0]["번호"], "100")
        self.assertEqual(rows[0]["가격신뢰도"], "low")
        self.assertEqual(rows[0]["검수우선순위"], "P1")

    def test_collect_low_confidence_rows_respects_limit(self):
        header = [""] * 41
        r1 = [""] * 41
        r2 = [""] * 41
        r1[39] = "low"
        r2[39] = "low"

        rows = allmod._collect_low_confidence_rows([header, r1, r2], limit=1)
        self.assertEqual(len(rows), 1)

    def test_collect_low_confidence_rows_limit_after_priority_sort(self):
        header = [""] * 41
        r1 = [""] * 41
        r2 = [""] * 41
        r1[0] = "100"
        r2[0] = "101"
        r1[39] = "low"
        r2[39] = "low"
        r1[37] = "primary_text"      # P2
        r2[37] = "primary_consult"   # P1

        rows = allmod._collect_low_confidence_rows([header, r1, r2], limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["번호"], "101")
        self.assertEqual(rows[0]["검수우선순위"], "P1")

    def test_collect_low_confidence_rows_with_recent_rows_filter(self):
        header = [""] * 41
        r1 = [""] * 41
        r2 = [""] * 41
        r3 = [""] * 41
        r1[39] = "low"
        r2[39] = "low"
        r3[39] = "low"

        rows = allmod._collect_low_confidence_rows([header, r1, r2, r3], recent_rows=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["row"], 4)

    def test_collect_low_confidence_rows_with_recent_numbers_filter(self):
        header = [""] * 41
        r1 = [""] * 41
        r2 = [""] * 41
        r3 = [""] * 41
        r1[0] = "100"
        r2[0] = "101"
        r3[0] = "102"
        r1[39] = "low"
        r2[39] = "low"
        r3[39] = "low"

        rows = allmod._collect_low_confidence_rows([header, r1, r2, r3], recent_numbers=2)
        self.assertEqual(len(rows), 2)
        self.assertEqual({x["번호"] for x in rows}, {"101", "102"})

    def test_sort_low_confidence_rows_by_priority_and_number(self):
        rows = [
            {"검수우선순위": "P3", "번호": "108", "row": 8},
            {"검수우선순위": "P1", "번호": "109", "row": 9},
            {"검수우선순위": "P2", "번호": "103", "row": 3},
            {"검수우선순위": "P1", "번호": "105", "row": 5},
        ]
        sorted_rows = allmod._sort_low_confidence_rows(rows)
        self.assertEqual([x["번호"] for x in sorted_rows], ["109", "105", "103", "108"])

    def test_merge_low_confidence_manual_fields_preserves_existing_values(self):
        rows = [
            {
                "row": 3,
                "검수우선순위": "P1",
                "번호": "100",
                "양도가": "협의",
                "가격원문": "협의",
                "가격추출소스": "primary_consult",
                "가격추출근거": "협의",
                "가격신뢰도": "low",
                "가격fallback": "N",
                "청구양도가": "",
                "비고": "",
            },
            {
                "row": 7,
                "검수우선순위": "P2",
                "번호": "",
                "양도가": "협의",
                "가격원문": "협의",
                "가격추출소스": "claim_consult",
                "가격추출근거": "협의",
                "가격신뢰도": "low",
                "가격fallback": "Y",
                "청구양도가": "",
                "비고": "",
            },
        ]
        existing_values = [
            ["번호", "row", "검수완료", "검수메모", "검수수정양도가", "검수시각"],
            ["100", "999", "Y", "번호기준 보존", "1억", "2026-02-22 20:00:00"],
            ["", "7", "", "행기준 보존", "", "2026-02-22 20:05:00"],
        ]

        merged = allmod._merge_low_confidence_manual_fields(rows, existing_values)
        self.assertEqual(merged[0]["검수완료"], "Y")
        self.assertEqual(merged[0]["검수메모"], "번호기준 보존")
        self.assertEqual(merged[0]["검수수정양도가"], "1억")
        self.assertEqual(merged[1]["검수메모"], "행기준 보존")
        self.assertEqual(merged[1]["검수시각"], "2026-02-22 20:05:00")

    def test_merge_low_confidence_manual_fields_collision_prefers_review_done(self):
        rows = [{"row": 3, "번호": "100"}]
        existing_values = [
            ["번호", "검수완료", "검수메모", "검수시각"],
            ["100", "", "초안", "2026-02-22 20:00:00"],
            ["100", "Y", "최종확정", "2026-02-22 20:10:00"],
        ]

        merged = allmod._merge_low_confidence_manual_fields(rows, existing_values)
        self.assertEqual(merged[0]["검수완료"], "Y")
        self.assertEqual(merged[0]["검수메모"], "최종확정")
        self.assertEqual(merged[0]["검수시각"], "2026-02-22 20:10:00")

    def test_exclude_reviewed_low_confidence_rows(self):
        rows = [
            {"번호": "100", "검수완료": "Y"},
            {"번호": "101", "검수완료": "완료"},
            {"번호": "102", "검수완료": "true"},
            {"번호": "103", "검수완료": ""},
            {"번호": "104", "검수완료": "N"},
        ]
        kept, skipped = allmod._exclude_reviewed_low_confidence_rows(rows)
        self.assertEqual(skipped, 3)
        self.assertEqual([x["번호"] for x in kept], ["103", "104"])

    def test_autofill_reviewed_timestamp_only_for_done_and_empty(self):
        rows = [
            {"번호": "100", "검수완료": "Y", "검수시각": ""},
            {"번호": "101", "검수완료": "완료", "검수시각": "2026-02-22 19:00:00"},
            {"번호": "102", "검수완료": "", "검수시각": ""},
        ]
        out, filled = allmod._autofill_reviewed_timestamp(rows, now_text="2026-02-22 19:30:00")
        self.assertEqual(filled, 1)
        self.assertEqual(out[0]["검수시각"], "2026-02-22 19:30:00")
        self.assertEqual(out[1]["검수시각"], "2026-02-22 19:00:00")
        self.assertEqual(out[2]["검수시각"], "")

    def test_finalize_low_confidence_rows_applies_skip_then_limit(self):
        rows = [
            {"번호": "200", "row": 2, "검수우선순위": "P1"},
            {"번호": "199", "row": 3, "검수우선순위": "P1"},
            {"번호": "198", "row": 4, "검수우선순위": "P2"},
        ]
        existing_values = [
            ["번호", "검수완료", "검수메모"],
            ["200", "Y", "완료건"],
        ]

        finalized, stats = allmod._finalize_low_confidence_rows(
            rows, existing_values=existing_values, limit=1, skip_reviewed=True
        )
        self.assertEqual(len(finalized), 1)
        self.assertEqual(finalized[0]["번호"], "199")
        self.assertEqual(stats["skipped_reviewed"], 1)
        self.assertEqual(stats["limited_out"], 1)

    def test_build_low_confidence_sheet_values_has_header_and_rows(self):
        rows = [
            {
                "row": 2,
                "검수우선순위": "P1",
                "번호": "100",
                "양도가": "협의",
                "가격원문": "협의",
                "가격추출소스": "primary_consult",
                "가격추출근거": "협의",
                "가격신뢰도": "low",
                "가격fallback": "N",
                "청구양도가": "",
                "비고": "memo",
                "검수완료": "Y",
                "검수메모": "검수 완료",
                "검수수정양도가": "1.5억",
                "검수시각": "2026-02-22 19:10:00",
            }
        ]
        values = allmod._build_low_confidence_sheet_values(rows, generated_at="2026-02-22 19:00:00")
        self.assertEqual(values[0], allmod.LOW_CONF_SHEET_HEADERS)
        self.assertEqual(values[1][0], "2026-02-22 19:00:00")
        self.assertEqual(values[1][1], "P1")
        self.assertEqual(values[1][3], "100")
        self.assertEqual(values[1][8], "low")
        self.assertEqual(values[1][12], "Y")
        self.assertEqual(values[1][13], "검수 완료")
        self.assertEqual(values[1][14], "1.5억")
        self.assertEqual(values[1][15], "2026-02-22 19:10:00")

    def test_build_low_confidence_sheet_values_header_only_when_empty(self):
        values = allmod._build_low_confidence_sheet_values([], generated_at="2026-02-22 19:00:00")
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0], allmod.LOW_CONF_SHEET_HEADERS)


if __name__ == "__main__":
    unittest.main()
