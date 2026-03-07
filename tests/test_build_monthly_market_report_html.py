import unittest
from datetime import date

from scripts.build_monthly_market_report_html import build_report_html


def _sample_payload() -> dict:
    return {
        "notice_title": "2026년 2월 건설업 시장 리포트",
        "live_snapshot": {
            "overall_ranked": [
                {"keyword": "건설업 기업진단지침", "themes": ["기업진단 / 실질자본금"]},
                {"keyword": "건설업 실태조사", "themes": ["준법 / 행정처분 / 유지 리스크"]},
                {"keyword": "전문건설업양도양수", "themes": ["양도양수 / 실사 / 빠른 진입"]},
                {"keyword": "건설업 시공능력평가", "themes": ["입찰 / 시공능력평가"]},
            ],
            "theme_rankings": {
                "market_report": [{"keyword": "건설업 경기 전망"}],
                "license_transfer": [{"keyword": "전문건설업양도양수"}],
                "new_registration": [{"keyword": "건설업 신규등록"}],
                "capital_diagnosis": [{"keyword": "건설업 기업진단지침"}],
                "performance_bidding": [{"keyword": "건설업 시공능력평가"}],
                "compliance_risk": [{"keyword": "건설업 실태조사"}],
            },
        },
        "monthly_plan": [
            {
                "month": "2026-03",
                "theme_key": "market_report",
                "theme_label": "시장 리포트 / 경기 전망",
                "current_live_primary_candidate": "건설업 경기 전망",
                "current_live_supporting_candidates": ["건설업 시장 리포트", "건설업 상반기 전망"],
            }
        ],
    }


class BuildMonthlyMarketReportHtmlTests(unittest.TestCase):
    def test_build_report_html_contains_346_style_structure(self) -> None:
        subject, body = build_report_html(
            _sample_payload(),
            year=2026,
            month=3,
            run_date=date(2026, 3, 6),
            kakao_url="https://open.kakao.com/o/test",
            phone="010-9926-8661",
            bizcard_image_url="https://example.com/card.jpg",
        )
        self.assertIn("건설업 대표를 위한 건설업 전망 리포트", subject)
        self.assertIn("왜 대표 결정은 더 늦어질까?", subject)
        self.assertIn("30초 핵심 요약", body)
        self.assertIn("공공 vs 민간: 돈이 도는 곳이 갈렸다", body)
        self.assertIn("현장 체감이 늦는 이유: 수주-착공-기성의 시간차", body)
        self.assertIn("2026년 상반기 변수 5가지", body)
        self.assertIn("대표 실무 전략 7가지", body)
        self.assertIn("면허/실적 전략: 양도양수·신규등록·분할합병 선택 기준", body)
        self.assertIn("FAQ : 대표님들이 가장 많이 묻는 질문 10선", body)
        self.assertIn("공공(관급)", body)
        self.assertIn("민간(주택·개발)", body)
        self.assertIn("기업진단·실질자본금", body)
        self.assertIn("실태조사·행정 리스크", body)
        self.assertIn("양도양수", body)
        self.assertIn("신규등록", body)
        self.assertIn("시공능력평가", body)
        self.assertIn("본 리포트는 시장 흐름과 실무 포인트를 요약한 참고 자료입니다", body)
        self.assertNotIn("건설업 기업진단지침", body)
        self.assertNotIn("전문건설업양도양수", body)
        self.assertNotIn("color:#ffffff; margin:0 0 12px 0;", body)
        self.assertNotIn("color:#eff6ff; margin:0 0 20px 0;", body)
        self.assertNotIn("snapshot 기준", body)
        self.assertNotIn("운영 문서", body)


if __name__ == "__main__":
    unittest.main()
