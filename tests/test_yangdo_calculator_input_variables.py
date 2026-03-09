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


    def _build_minimal_training_context(self):
        records = [
            {
                "number": "5001",
                "uid": "91001",
                "license_text": "전기공사업",
                "license_tokens": {"전기"},
                "years": {"y23": 3, "y24": 4, "y25": 5},
                "specialty": 1.2,
                "sales3_eok": 4.5,
                "sales5_eok": 5.1,
                "capital_eok": 1.5,
                "surplus_eok": 0.2,
                "balance_eok": 0.1,
                "debt_ratio": 90.0,
                "liq_ratio": 140.0,
                "current_price_text": "1억 3000만",
                "current_price_eok": 1.3,
                "claim_price_text": "1억",
                "claim_price_eok": 1.0,
            }
        ]
        train_dataset = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")
        meta = yangdo_calculator.build_meta(records, train_dataset)
        return records, train_dataset, meta

    def test_price_token_edge_cases(self):
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("10억"), 10.0, places=4)
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("0.5억"), 0.5, places=4)
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("500만"), 0.05, places=4)
        self.assertAlmostEqual(yangdo_calculator._price_token_to_eok("1억 3000만"), 1.3, places=4)
        self.assertIsNone(yangdo_calculator._price_token_to_eok(""))
        self.assertIsNone(yangdo_calculator._price_token_to_eok(None))
        self.assertIsNone(yangdo_calculator._price_token_to_eok("비공개"))
        self.assertIsNone(yangdo_calculator._price_token_to_eok("문의"))

    def test_build_meta_returns_required_keys(self):
        records, train_dataset, meta = self._build_minimal_training_context()
        self.assertEqual(len(records), 1)
        self.assertEqual(len(train_dataset), 1)
        self.assertIn("all_record_count", meta)
        self.assertIn("train_count", meta)
        self.assertIn("priced_ratio", meta)
        self.assertGreaterEqual(meta["priced_ratio"], 0.0)
        self.assertLessEqual(meta["priced_ratio"], 100.0)

    def test_build_page_html_contains_section_tag(self):
        _, train_dataset, meta = self._build_minimal_training_context()
        customer_html = yangdo_calculator.build_page_html(train_dataset, meta, view_mode="customer")
        owner_html = yangdo_calculator.build_page_html(train_dataset, meta, view_mode="owner")

        self.assertIn('id="seoulmna-yangdo-calculator"', customer_html)
        self.assertIn("--smna-primary", customer_html)
        self.assertIn('id="seoulmna-yangdo-calculator"', owner_html)
        self.assertIn("--smna-primary", owner_html)

    def test_build_page_html_has_special_balance_policies(self):
        _, train_dataset, meta = self._build_minimal_training_context()
        html = yangdo_calculator.build_page_html(train_dataset, meta, view_mode="customer")

        self.assertIn("SPECIAL_BALANCE_AUTO_POLICIES", html)
        self.assertIn("전기", html)
        self.assertIn("정보통신", html)
        self.assertIn("소방", html)

    def test_build_training_dataset_includes_special_sectors(self):
        records = [
            {
                "number": "6001",
                "uid": "92001",
                "license_text": "전기공사업",
                "license_tokens": {"전기"},
                "years": {"y23": 1},
                "current_price_text": "1억",
                "current_price_eok": 1.0,
            },
            {
                "number": "6002",
                "uid": "92002",
                "license_text": "정보통신공사업",
                "license_tokens": {"정보통신"},
                "years": {"y23": 2},
                "current_price_text": "1억 2000만",
                "current_price_eok": 1.2,
            },
            {
                "number": "6003",
                "uid": "92003",
                "license_text": "소방시설공사업",
                "license_tokens": {"소방"},
                "years": {"y23": 3},
                "current_price_text": "8000만",
                "current_price_eok": 0.8,
            },
        ]

        rows = yangdo_calculator.build_training_dataset(records, site_url="https://seoulmna.kr")

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {row["license_text"] for row in rows},
            {
                "전기공사업",
                "정보통신공사업",
                "소방시설공사업",
            },
        )

    def test_build_page_html_customer_vs_owner_both_work(self):
        _, train_dataset, meta = self._build_minimal_training_context()
        customer_html = yangdo_calculator.build_page_html(train_dataset, meta, view_mode="customer")
        owner_html = yangdo_calculator.build_page_html(train_dataset, meta, view_mode="owner")

        self.assertTrue(customer_html)
        self.assertIn("</section>", customer_html)
        self.assertTrue(owner_html)
        self.assertIn("</section>", owner_html)


if __name__ == "__main__":
    unittest.main()
