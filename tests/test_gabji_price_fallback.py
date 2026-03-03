import unittest

import gabji


def _blank_row(size=36):
    return [""] * size


class GabjiPriceFallbackTest(unittest.TestCase):
    def _make_lookup(self, header, row):
        lookup = gabji.ListingSheetLookup()
        lookup._rows_cache = [header, row]
        lookup._header_index_cache = {}
        return lookup

    def test_extract_final_yangdo_price_uses_last_range_value(self):
        self.assertEqual(gabji.extract_final_yangdo_price("청구 양도가 2.5억~2.7억"), "2.7억")

    def test_resolve_price_prefers_numeric_fallback_over_consult(self):
        header = _blank_row()
        row = _blank_row()
        header[18] = "양도가"
        header[31] = "비고"
        row[18] = "협의"
        row[31] = "청구 양도가 2.5억 ~ 2.7억"
        lookup = self._make_lookup(header, row)

        self.assertEqual(lookup._resolve_yangdo_price(row), "2.7억")

    def test_resolve_price_reads_claim_range_header_column(self):
        header = _blank_row()
        row = _blank_row()
        header[26] = "청구 양도가/범위값"
        row[26] = "2.1억-2.4억"
        lookup = self._make_lookup(header, row)

        self.assertEqual(lookup._resolve_yangdo_price(row), "2.4억")

    def test_resolve_price_row_hint_scan_works_without_header(self):
        header = _blank_row()
        row = _blank_row()
        row[18] = "협의"
        row[29] = "청구 양도가: 3.1억~3.3억"
        lookup = self._make_lookup(header, row)

        self.assertEqual(lookup._resolve_yangdo_price(row), "3.3억")

    def test_resolve_price_returns_consult_when_only_consult_exists(self):
        header = _blank_row()
        row = _blank_row()
        header[18] = "양도가"
        row[18] = "협의"
        lookup = self._make_lookup(header, row)

        self.assertEqual(lookup._resolve_yangdo_price(row), "협의")


if __name__ == "__main__":
    unittest.main()
