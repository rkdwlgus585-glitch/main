import unittest

from bs4 import BeautifulSoup

import gabji


def _blank_row(size=45):
    return [""] * size


class GabjiSumMergePolicyTest(unittest.TestCase):
    def _make_lookup(self):
        lookup = gabji.ListingSheetLookup()
        lookup._rows_cache = [_blank_row(), _blank_row()]
        lookup._header_index_cache = {}
        return lookup

    def test_live_parser_maps_year_and_sipyeong_by_header_name(self):
        html = """
        <table>
          <tr>
            <td>업종</td><td>면허년도</td><td>2023년</td><td>시공능력 평가액</td>
            <td>2021년</td><td>5년합계</td><td>2024년</td><td>2022년</td>
            <td>3년합계</td><td>2020년</td><td>2025년</td>
          </tr>
          <tr>
            <td>토목공사업</td><td>2003</td><td>25</td><td>60</td>
            <td>13</td><td>106억</td><td>12</td><td>56</td>
            <td>37억</td><td>1</td><td>-</td>
          </tr>
        </table>
        """
        lookup = self._make_lookup()
        rows = lookup._parse_live_industry_rows(BeautifulSoup(html, "html.parser"))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.get("시공능력평가액"), "60")
        self.assertEqual(row.get("매출", {}).get("2020년"), "1")
        self.assertEqual(row.get("매출", {}).get("2021년"), "13")
        self.assertEqual(row.get("매출", {}).get("2022년"), "56")
        self.assertEqual(row.get("매출", {}).get("2023년"), "25")
        self.assertEqual(row.get("매출", {}).get("2024년"), "12")
        self.assertEqual(row.get("5년합계"), "106억")
        self.assertEqual(row.get("3년합계"), "37억")

    def test_merge_live_detail_does_not_overwrite_balance_when_base_exists(self):
        lookup = self._make_lookup()
        merged = lookup._merge_live_detail(
            {"공제조합잔액": "1,200만원"},
            {"공제조합잔액": "2,000만원"},
        )
        self.assertEqual(merged.get("공제조합잔액"), "1,200만원")

    def test_merge_live_detail_applies_balance_when_base_missing(self):
        lookup = self._make_lookup()
        merged = lookup._merge_live_detail(
            {"공제조합잔액": "-"},
            {"공제조합잔액": "2,000만원"},
        )
        self.assertEqual(merged.get("공제조합잔액"), "2,000만원")

    def test_row_to_gabji_data_uses_sheet_sum_columns_for_5year(self):
        lookup = self._make_lookup()
        row = _blank_row()
        row[gabji.ListingSheetLookup.COL_SEQ] = "11835"
        row[gabji.ListingSheetLookup.COL_LICENSE] = "토목"
        row[gabji.ListingSheetLookup.COL_LICENSE_YEAR] = "2003"
        row[gabji.ListingSheetLookup.COL_SIPYEONG] = "40"
        row[gabji.ListingSheetLookup.COL_Y20] = "11"
        row[gabji.ListingSheetLookup.COL_Y21] = "7"
        row[gabji.ListingSheetLookup.COL_Y22] = "0.5"
        row[gabji.ListingSheetLookup.COL_Y23] = "0.5"
        row[gabji.ListingSheetLookup.COL_Y24] = "0.5"
        row[gabji.ListingSheetLookup.COL_SUM3] = "1억"
        row[gabji.ListingSheetLookup.COL_SUM5] = "8억"
        row[gabji.ListingSheetLookup.COL_Y25] = "-"

        data = lookup._row_to_gabji_data("11835", 2, row)
        info = data.get("업종정보", [])[0]
        self.assertEqual(info.get("3년합계"), "1억")
        self.assertEqual(info.get("5년합계"), "8억")


if __name__ == "__main__":
    unittest.main()

