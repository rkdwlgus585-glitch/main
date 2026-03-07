import importlib
import unittest
from bs4 import BeautifulSoup


allmod = importlib.import_module("all")


class AllSalesRowsAlignmentTest(unittest.TestCase):
    def test_join_lines_preserve_alignment_keeps_leading_blank(self):
        text = allmod._join_lines_preserve_alignment(["", "55", "87.4", ""])
        self.assertEqual(text, "\n55\n87.4")

    def test_preserves_blank_lines_for_row_alignment(self):
        item = {
            "license": "catA\ncatB\ncatC",
            "license_year": "2000\n\n",
            "specialty": "450\n189\n430",
            "y20": "\n55\n87.4",
            "y21": "\n28.5\n295.5",
            "y22": "\n73\n395",
            "y23": "\n95\n453",
            "y24": "\n94\n419",
            "y25": "50\n\n",
        }

        rows = allmod._build_sales_rows(item, cate2_lookup={})
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["mp_2020[]"], "")
        self.assertEqual(rows[1]["mp_2020[]"], "55")
        self.assertEqual(rows[2]["mp_2020[]"], "87.4")
        self.assertEqual(rows[0]["mp_2025[]"], "50")

    def test_skips_fully_empty_middle_rows(self):
        item = {
            "license": "catA\n\ncatB",
            "license_year": "2000\n\n",
            "specialty": "450\n\n189",
            "y20": "\n\n55",
            "y21": "\n\n28.5",
            "y22": "\n\n73",
            "y23": "\n\n95",
            "y24": "\n\n94",
            "y25": "50\n\n",
        }

        rows = allmod._build_sales_rows(item, cate2_lookup={})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["mp_2020[]"], "")
        self.assertEqual(rows[1]["mp_2020[]"], "55")

    def test_merge_blank_sales_preserves_interior_blank(self):
        updates = {"mp_2020[]": ["", "55", "87.4", ""]}
        defaults = {"mp_2020[]": ["55", "87.4", "", "legacy-tail"]}
        out = allmod._merge_blank_sales_with_existing(updates, defaults)
        self.assertEqual(out["mp_2020[]"], ["", "55", "87.4", "legacy-tail"])

    def test_merge_blank_sales_preserves_old_tail_rows(self):
        updates = {"mp_cate2[]": ["11", "22", "33", "44"]}
        defaults = {"mp_cate2[]": ["11", "22", "33", "44", "55"]}
        out = allmod._merge_blank_sales_with_existing(updates, defaults)
        self.assertEqual(out["mp_cate2[]"], ["11", "22", "33", "44", "55"])

    def test_merge_blank_sales_mp_year_fills_only_empty_and_keeps_existing_on_conflict(self):
        updates = {"mp_year[]": ["2015", "2016", "2017"]}
        defaults = {"mp_year[]": ["", "2014", "2017"]}
        out = allmod._merge_blank_sales_with_existing(updates, defaults)
        self.assertEqual(out["mp_year[]"], ["2015", "2014", "2017"])

    def test_merge_blank_sales_mp_year_uses_new_years_when_row_structure_changes(self):
        updates = {
            "mp_cate1[]": ["2", "2", "2", "2"],
            "mp_cate2[]": ["1", "18", "2", "3"],
            "mp_year[]": ["2018", "2023", "2019", "2021"],
        }
        defaults = {
            "mp_cate1[]": ["2", "2", "2"],
            "mp_cate2[]": ["1", "2", "3"],
            "mp_year[]": ["2018", "2019", "2021"],
        }
        out = allmod._merge_blank_sales_with_existing(updates, defaults)
        self.assertEqual(out["mp_year[]"], ["2018", "2023", "2019", "2021"])

    def test_extract_license_lines_from_main_check_text(self):
        memo = "주요체크사항\n토목/도장/상하/포장 가능\n추가로 철콘 가능"
        extracted = allmod._extract_license_lines_from_text(memo)
        self.assertTrue({"토목", "도장", "상하", "포장", "철콘"}.issubset(set(extracted)))

    def test_nowmna_header_mapping_uses_yearly_columns(self):
        headers = ["업종", "면허년도", "시공능력", "2020", "2021", "2022", "2023", "2024", "3년", "5년", "2025"]
        col_map = allmod._build_nowmna_sales_col_map(headers)
        self.assertEqual(col_map["license"], 0)
        self.assertEqual(col_map["year"], 1)
        self.assertEqual(col_map["specialty"], 2)
        self.assertEqual(col_map["y20"], 3)
        self.assertEqual(col_map["y25"], 10)

    def test_collect_form_defaults_select_prefers_non_empty_selected(self):
        html = (
            "<form>"
            "<select name='mp_year[]'>"
            "<option value='' selected='selected'></option>"
            "<option value='2019' selected='selected'>2019</option>"
            "</select>"
            "</form>"
        )
        form = BeautifulSoup(html, "html.parser").select_one("form")
        publisher = allmod.MnaBoardPublisher.__new__(allmod.MnaBoardPublisher)
        payload = publisher._collect_form_defaults(form)
        self.assertEqual(payload.get("mp_year[]"), "2019")

    def test_diff_sales_treats_blank_and_zero_as_equivalent(self):
        current_payload = {"mp_2020[]": ["0", "55", "87.4"]}
        target_updates = {"mp_2020[]": ["", "55", "87.4"]}
        diffs = allmod._diff_payload_updates(current_payload, target_updates)
        self.assertNotIn("mp_2020[]", diffs)

    def test_diff_sales_treats_new_as_blank_equivalent(self):
        current_payload = {"mp_2025[]": ["0", "50"]}
        target_updates = {"mp_2025[]": ["\uC2E0\uADDC", "50"]}
        diffs = allmod._diff_payload_updates(current_payload, target_updates)
        self.assertNotIn("mp_2025[]", diffs)

    def test_diff_sales_treats_plus_as_blank_equivalent(self):
        current_payload = {"mp_2020[]": ["0", "55"]}
        target_updates = {"mp_2020[]": ["+", "55"]}
        diffs = allmod._diff_payload_updates(current_payload, target_updates)
        self.assertNotIn("mp_2020[]", diffs)

    def test_diff_mp_money_treats_half_rounding_as_equivalent(self):
        current_payload = {"mp_money[]": ["20", "15"]}
        target_updates = {"mp_money[]": ["19.5", "14.5"]}
        diffs = allmod._diff_payload_updates(current_payload, target_updates)
        self.assertNotIn("mp_money[]", diffs)

    def test_merge_sheet_memo_preserves_credit_line_from_old(self):
        old_memo = "\uAE30\uC220\uC790 \uC720\uC9C0\n\uC678\uBD80\uC2E0\uC6A9\uB4F1\uAE09 A- \uBCF4\uC720"
        new_memo = "\uD589\uC815\uCC98\uBD84 \uC5C6\uC74C"
        merged = allmod._merge_sheet_memo_preserve_credit(old_memo, new_memo)
        self.assertIn("\uD589\uC815\uCC98\uBD84 \uC5C6\uC74C", merged)
        self.assertIn("\uC678\uBD80\uC2E0\uC6A9\uB4F1\uAE09 A- \uBCF4\uC720", merged)

    def test_merge_sheet_memo_keeps_new_credit_line(self):
        old_memo = "\uC678\uBD80\uC2E0\uC6A9\uB4F1\uAE09 A- \uBCF4\uC720"
        new_memo = "\uC2E0\uC6A9\uB4F1\uAE09 AA+ \uC720\uC9C0"
        merged = allmod._merge_sheet_memo_preserve_credit(old_memo, new_memo)
        self.assertEqual(merged, "\uC2E0\uC6A9\uB4F1\uAE09 AA+ \uC720\uC9C0")

    def test_memo_typo_review_alert_only_keeps_original(self):
        allmod._configure_memo_typo_runtime(check=True, fix=False, approve_all=False, approved_uids="")
        src = "\uAE09\uC5EC\uC774\uCC44 \uC788\uC74C"
        out = allmod._review_memo_typo_for_sheet("10001", src)
        self.assertEqual(out, src)

    def test_memo_typo_review_applies_when_uid_preapproved(self):
        allmod._configure_memo_typo_runtime(check=True, fix=True, approve_all=False, approved_uids="10002")
        src = "\uAE09\uC5EC\uC774\uCC44 \uC788\uC74C"
        out = allmod._review_memo_typo_for_sheet("10002", src)
        self.assertEqual(out, "\uAE09\uC5EC\uC774\uCCB4 \uC788\uC74C")

    def test_extract_license_lines_ignores_transition_or_exclusion_phrases(self):
        memo = "시설물에서 건축전환함\n조경식재제외 전문건설 업종선택"
        extracted = allmod._extract_license_lines_from_text(memo)
        self.assertEqual(extracted, [])

    def test_extract_nowmna_sales_rows_keeps_sparse_license_rows(self):
        body = (
            "최근년도 매출실적\n"
            "업종 면허년도 2020년 2021년 2022년 2023년 2024년 3년합계 5년합계 2025년 시공능력 평가액\n"
            "포장 2021 - 3.9 4 1 0.1 5.1억 9억 0.8 11\n"
            "상하수도 2.5 2 3.3 2.7 2.3 8.3억 12.8억 1.7 12\n"
            "기계설비 2023 2.8 2.8억 2.8억 3 9\n"
            "기타 2023 신규\n"
            "재무제표\n"
        )
        rows = allmod._extract_nowmna_sales_rows_from_body_text(body)
        self.assertEqual([row["license"] for row in rows], ["포장", "상하", "기계설비", "기타"])
        self.assertEqual(rows[1]["year"], "")
        self.assertEqual(rows[2]["year"], "2023")
        self.assertEqual(rows[2]["specialty"], "9")
        self.assertEqual(rows[3]["specialty"], "")

    def test_build_sales_rows_skips_generic_license_rows(self):
        item = {
            "license": "기타",
            "license_year": "2023",
            "specialty": "",
            "y20": "",
            "y21": "",
            "y22": "",
            "y23": "",
            "y24": "",
            "y25": "",
        }
        rows = allmod._build_sales_rows(item, cate2_lookup={})
        self.assertEqual(rows, [])

    def test_build_mna_payload_updates_clears_sales_arrays_for_generic_only_license(self):
        html = "<form></form>"
        form = BeautifulSoup(html, "html.parser").select_one("form")
        item = {
            "uid": "11876",
            "license": "기타",
            "license_year": "2023",
            "specialty": "",
            "y20": "",
            "y21": "",
            "y22": "",
            "y23": "",
            "y24": "",
            "y25": "",
            "claim_price": "",
            "source_url": "",
        }
        updates = allmod._build_mna_payload_updates(item, form, html, defaults={})
        for key in allmod.SALES_ARRAY_KEYS:
            self.assertIn(key, updates)
            self.assertEqual(updates[key], [])

    def test_build_sheet_row_clears_license_columns_for_generic_only_license(self):
        item = {
            "uid": "11876",
            "license": "기타",
            "license_year": "2023",
            "specialty": "9",
            "y20": "1",
            "y21": "2",
            "y22": "3",
            "y23": "4",
            "y24": "5",
            "y25": "6",
        }
        row = allmod._build_sheet_row(item, 1)
        self.assertEqual(row[2], "기타")
        self.assertEqual(row[3], "")
        self.assertEqual(row[4], "")
        self.assertEqual(row[5], "")
        self.assertEqual(row[12], "")

    def test_build_sheet_row_normalizes_claim_header_to_current_licenses(self):
        item = {
            "uid": "11871",
            "license": "토공\n포장\n상하\n철콘",
            "claim_price": "11871 토공 포장 상하\n1.5억~1.7억",
        }
        row = allmod._build_sheet_row(item, 1)
        self.assertEqual(row[18], "협의")
        self.assertEqual(row[33], "11871 토공, 포장, 상하, 철콘\n1.5억~1.7억")

    def test_claim_price_line_does_not_treat_uid_header_with_slash_as_price(self):
        self.assertFalse(allmod._looks_like_claim_price_line("11864식재 / 시설"))


if __name__ == "__main__":
    unittest.main()
