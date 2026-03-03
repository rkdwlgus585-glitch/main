import unittest

import listing_matcher as lm


class ListingPricePriorityTest(unittest.TestCase):
    def test_extract_final_price_uses_last_range_value(self):
        self.assertEqual(lm._extract_final_price("2.1억~2.4억"), "2.4억")

    def test_resolve_listing_price_prefers_numeric_claim_over_consult(self):
        self.assertEqual(lm._resolve_listing_price("협의", "0.9억~1억"), "1억")

    def test_resolve_listing_price_keeps_primary_when_primary_is_numeric(self):
        self.assertEqual(lm._resolve_listing_price("1.7억", "0.9억~1억"), "1.7억")

    def test_resolve_listing_price_falls_back_to_consult_when_no_number(self):
        self.assertEqual(lm._resolve_listing_price("협의", ""), "협의")


if __name__ == "__main__":
    unittest.main()
