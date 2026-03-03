import unittest
from unittest.mock import patch

import premium_auto


class PremiumAutoSequenceTest(unittest.TestCase):
    def setUp(self):
        self.crawler = premium_auto.PremiumCrawler(driver=None)

    def test_extract_number_from_title_patterns(self):
        self.assertEqual(
            premium_auto.PremiumCrawler._extract_number_from_text("철근콘크리트공사업 양도 (매물 7618)"),
            7618,
        )
        self.assertEqual(
            premium_auto.PremiumCrawler._extract_number_from_text("프리미엄 매물 요약 : 제 7620호"),
            7620,
        )
        self.assertIsNone(premium_auto.PremiumCrawler._extract_number_from_text("번호 없는 제목"))

    def test_next_target_prefers_next_after_last_published(self):
        existing = {7610, 7611, 7612, 7614, 7615, 7616, 7618}
        mna_numbers = set(range(7611, 7631))

        with patch.object(
            premium_auto.PremiumCrawler,
            "get_existing_premium_numbers",
            return_value=existing,
        ), patch.object(
            premium_auto.PremiumCrawler,
            "get_all_mna_numbers",
            return_value=mna_numbers,
        ), patch.object(
            premium_auto.PremiumCrawler,
            "get_latest_premium_post_info",
            return_value={"number": 7618, "title": "철근콘크리트공사업 양도 (매물 7618)"},
        ):
            target = self.crawler.get_next_target_number(start_from=7611)

        self.assertEqual(target, 7619)

    def test_next_target_skips_missing_number_and_chooses_next_available(self):
        existing = {7618}
        mna_numbers = {7620, 7621, 7622}

        with patch.object(
            premium_auto.PremiumCrawler,
            "get_existing_premium_numbers",
            return_value=existing,
        ), patch.object(
            premium_auto.PremiumCrawler,
            "get_all_mna_numbers",
            return_value=mna_numbers,
        ), patch.object(
            premium_auto.PremiumCrawler,
            "get_latest_premium_post_info",
            return_value={"number": 7618, "title": "철근콘크리트공사업 양도 (매물 7618)"},
        ):
            target = self.crawler.get_next_target_number(start_from=7611)

        self.assertEqual(target, 7620)


if __name__ == "__main__":
    unittest.main()
