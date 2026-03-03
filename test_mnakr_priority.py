import unittest
from collections import Counter
from unittest.mock import patch

import mnakr


class MnakrPriorityTest(unittest.TestCase):
    def test_business_keyword_filter_is_not_limited_to_transfer_registration(self):
        self.assertTrue(mnakr.is_conversion_keyword("건설업 기업진단 기준"))
        self.assertTrue(mnakr.is_conversion_keyword("건설업 실질자본금 인정 항목"))
        self.assertFalse(mnakr.is_conversion_keyword("오늘의 점심 메뉴"))

    def test_slug_builder_covers_business_tokens(self):
        slug = mnakr.build_slug_from_keyword("건설업 기업진단 실질자본금 체크")
        self.assertIn("corporate-diagnosis", slug)
        self.assertIn("substantial-capital", slug)

    def test_radar_duplicate_filter_blocks_similar_titles(self):
        radar = mnakr.BusinessKeywordRadar()
        radar._existing_norm_titles = {mnakr._normalize_topic("건설업 기업진단 기준")}
        radar._existing_norm_slugs = set()
        radar._existing_title_list = list(radar._existing_norm_titles)
        self.assertFalse(radar.is_new_keyword("건설업 기업진단 기준"))
        self.assertFalse(radar.is_new_keyword("건설업 기업진단 기준 안내"))

    def test_radar_uses_site_topics_for_priority(self):
        def fake_fetch(self):
            self._index_existing_posts([])
            return []

        with patch.object(mnakr.BusinessKeywordRadar, "_fetch_existing_posts", fake_fetch), patch.object(
            mnakr.BusinessKeywordRadar,
            "_discover_site_topics",
            return_value=Counter({"기업진단": 8, "실질자본금": 4}),
        ):
            radar = mnakr.BusinessKeywordRadar()
            keywords = radar.get_top_keywords(5)

        self.assertTrue(keywords)
        self.assertTrue(any("기업진단" in kw for kw in keywords))


if __name__ == "__main__":
    unittest.main()
