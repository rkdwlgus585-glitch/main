import unittest

from scripts.build_notice_keyword_report import (
    _keyword_matches_theme,
    _serialize_ranked_entries,
    _verify_notice_positioning,
)


class BuildNoticeKeywordReportTests(unittest.TestCase):
    def test_verify_notice_positioning_accepts_feb_market_report(self):
        result = _verify_notice_positioning(
            "2026년 2월 건설업 시장 리포트｜수주는 움직이는데 왜 현장은 체감이 없을까?",
            "이번 리포트는 양도양수 신규등록 분할합병 선택지를 비교합니다.",
        )
        self.assertTrue(result["verified"])
        self.assertTrue(result["checks"]["title_market_report"])
        self.assertTrue(result["checks"]["problem_statement"])

    def test_theme_matching_rejects_non_construction_noise(self):
        self.assertFalse(_keyword_matches_theme("자동차 신규등록", "new_registration"))
        self.assertFalse(_keyword_matches_theme("올림픽수영장 신규등록", "new_registration"))
        self.assertTrue(_keyword_matches_theme("건설업 신규등록", "new_registration"))
        self.assertTrue(_keyword_matches_theme("전문건설업 양도양수", "license_transfer"))

    def test_ranked_entries_prefer_broader_live_signal(self):
        bucket = {
            "건설업 신규등록": {
                "channels": {"google", "naver"},
                "seed_hits": {"건설업 신규등록", "건설업 등록기준"},
                "hit_count": 3,
            },
            "건설업 기술인력": {
                "channels": {"google"},
                "seed_hits": {"건설업 기술인력"},
                "hit_count": 1,
            },
        }
        ranked = _serialize_ranked_entries("new_registration", bucket)
        self.assertEqual(ranked[0]["keyword"], "건설업 신규등록")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])


if __name__ == "__main__":
    unittest.main()
