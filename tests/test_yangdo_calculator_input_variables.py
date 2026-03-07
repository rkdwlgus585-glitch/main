import unittest

import yangdo_calculator


class YangdoCalculatorInputVariablesTest(unittest.TestCase):
    def test_price_token_to_eok_handles_core_variants(self):
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("2.3억"), 2.3, places=4)
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("2억 5000만"), 2.5, places=4)
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("7500만"), 0.75, places=4)
        self.assertIsNone(yangdo_calculator._price_token_to_eok("협의"))
        self.assertIsNone(yangdo_calculator._price_token_to_eok("0억"))

    def test_extract_price_values_deduplicates(self):
        values = yangdo_calculator._extract_price_values_eok("2.1억~2.6억 / 2.1억 / 26000만")
        self.assertEqual(values, [2.1, 2.6])

    def test_derive_display_range_uses_numeric_fallback(self):
        low, high = yangdo_calculator._derive_display_range_eok(
            current_price_text="협의",
            claim_price_text="",
            current_price_eok=1.7,
            claim_price_eok=None,
        )
        self.assertAlmostEqual(low, 1.7, places=4)
        self.assertAlmostEqual(high, 1.7, places=4)

    def test_build_training_dataset_skips_invalid_price_rows(self):
        records = [
            {
                "number": "4001",
                "uid": "90001",
                "license_text": "토목",
                "license_tokens": {"토목"},
                "years": {"y23": 3},
                "current_price_text": "2.3억",
                "current_price_eok": 2.3,
                "claim_price_text": "2.1억~2.3억",
                "claim_price_eok": 2.2,
            },
            {
                "number": "4002",
                "uid": "90002",
                "license_text": "건축",
                "license_tokens": {"건축"},
                "years": {"y23": 1},
                "current_price_text": "협의",
                "current_price_eok": None,
            },
        ]
        rows = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["seoul_no"], 4001)
        self.assertEqual(rows[0]["now_uid"], "90001")
        self.assertTrue(str(rows[0]["url"]).endswith("/mna/4001"))


if __name__ == "__main__":
    unittest.main()
