import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.build_monthly_market_report_html import build_report_html
from scripts.review_monthly_market_report import review_bundle


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


class ReviewMonthlyMarketReportTests(unittest.TestCase):
    def test_review_bundle_passes_for_deep_customer_facing_bundle(self) -> None:
        payload = _sample_payload()
        subject, body = build_report_html(
            payload,
            year=2026,
            month=3,
            run_date=date(2026, 3, 6),
            kakao_url="https://open.kakao.com/o/test",
            phone="010-9926-8661",
            bizcard_image_url="https://example.com/card.jpg",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subject_path = root / "subject.txt"
            body_path = root / "body.html"
            source_path = root / "source.json"
            subject_path.write_text(subject + "\n", encoding="utf-8")
            body_path.write_text(body, encoding="utf-8")
            source_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result = review_bundle(subject_path, body_path, "2026-03", source_snapshot_path=source_path)
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["blocking_issues"])
        self.assertGreaterEqual(result["stats"]["plain_chars"], 3200)
        self.assertGreaterEqual(result["stats"]["faq_count"], 8)
        self.assertGreaterEqual(len(result["stats"]["required_heading_hits"]), 8)
        self.assertTrue(result["stats"]["executive_identity_ok"])
        self.assertGreaterEqual(len(result["stats"]["mentioned_signal_labels"]), 4)
        self.assertFalse(result["stats"]["raw_keyword_heading_hits"])
        self.assertLessEqual(len(result["stats"]["raw_keyword_intro_hits"]), 1)

    def test_review_bundle_fails_on_internal_only_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subject_path = root / "subject.txt"
            body_path = root / "body.html"
            subject_path.write_text("[26년 3월] 테스트 리포트\n", encoding="utf-8")
            body_path.write_text(
                """
                <div>
                  <h1>테스트</h1>
                  <h2>대표님 실행 체크리스트</h2>
                  <p>실시간 건설업 키워드 snapshot 기준으로 체류시간과 CTA를 조정하는 운영 문서입니다.</p>
                  <p>안내 본 리포트는 시장 흐름과 실무 포인트를 요약한 참고 자료입니다. 최종 법무·세무 판단과 거래 조건은 계약 및 실사 이후 확정됩니다.</p>
                  <a href="tel:01099268661">전화</a>
                </div>
                """,
                encoding="utf-8",
            )
            result = review_bundle(subject_path, body_path, "2026-03")
        self.assertEqual(result["status"], "fail")
        self.assertIn("internal_only_language_detected", result["blocking_issues"])

    def test_review_bundle_fails_when_report_is_too_shallow(self) -> None:
        payload = {
            "live_snapshot": {
                "overall_ranked": [
                    {"keyword": "건설업 기업진단지침"},
                    {"keyword": "건설업 실태조사"},
                    {"keyword": "전문건설업양도양수"},
                    {"keyword": "건설업 시공능력평가"},
                ]
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subject_path = root / "subject.txt"
            body_path = root / "body.html"
            source_path = root / "source.json"
            subject_path.write_text("[26년 3월] 건설업 대표를 위한 건설업 전망 리포트 | 테스트\n", encoding="utf-8")
            body_path.write_text(
                """
                <div>
                  <h1>건설업 대표를 위한 건설업 전망 리포트</h1>
                  <h2>30초 핵심 요약</h2>
                  <h2>1. 시장 한 문장 정리</h2>
                  <h2>2. 공공 vs 민간: 돈이 도는 곳이 갈렸다</h2>
                  <h2>3. 현장 체감이 늦는 이유: 수주-착공-기성의 시간차</h2>
                  <h2>4. 2026년 상반기 변수 5가지</h2>
                  <h2>5. 대표 실무 전략 7가지</h2>
                  <h2>6. 면허/실적 전략</h2>
                  <h2>7. FAQ</h2>
                  <p>대표 상담 안내와 시장 흐름 요약입니다.</p>
                  <p>기업진단, 실태조사, 양도양수, 신규등록, 시공능력평가를 언급합니다.</p>
                  <p>최종 법무·세무 판단과 거래 조건은 계약 및 실사 이후 확정됩니다.</p>
                  <a href="tel:01099268661">전화</a>
                </div>
                """,
                encoding="utf-8",
            )
            source_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result = review_bundle(subject_path, body_path, "2026-03", source_snapshot_path=source_path)
        self.assertEqual(result["status"], "fail")
        self.assertIn("report_depth_too_low", result["blocking_issues"])
        self.assertIn("faq_depth_too_low", result["blocking_issues"])

    def test_review_bundle_fails_when_raw_keywords_are_front_loaded(self) -> None:
        payload = _sample_payload()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subject_path = root / "subject.txt"
            body_path = root / "body.html"
            source_path = root / "source.json"
            subject_path.write_text("[26년 3월] 건설업 대표를 위한 건설업 전망 리포트 | 테스트\n", encoding="utf-8")
            body_path.write_text(
                """
                <div>
                  <h1>건설업 대표를 위한 건설업 전망 리포트</h1>
                  <h2>30초 핵심 요약</h2>
                  <p>건설업 기업진단지침, 건설업 실태조사, 전문건설업양도양수, 건설업 시공능력평가를 앞부분에 그대로 반복합니다.</p>
                  <h2>1. 시장 한 문장 정리</h2>
                  <h2>2. 공공 vs 민간: 돈이 도는 곳이 갈렸다</h2>
                  <h2>3. 현장 체감이 늦는 이유: 수주-착공-기성의 시간차</h2>
                  <h2>4. 2026년 상반기 변수 5가지</h2>
                  <h2>5. 대표 실무 전략 7가지</h2>
                  <h2>6. 면허/실적 전략</h2>
                  <h2>7. FAQ</h2>
                  <p>본 리포트는 시장 흐름과 실무 포인트를 요약한 참고 자료입니다. 최종 법무·세무 판단과 거래 조건은 계약 및 실사 이후 확정됩니다.</p>
                  <a href="tel:01099268661">전화</a>
                </div>
                """,
                encoding="utf-8",
            )
            source_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result = review_bundle(subject_path, body_path, "2026-03", source_snapshot_path=source_path)
        self.assertEqual(result["status"], "fail")
        self.assertIn("raw_keyword_intro_exposure_high", result["blocking_issues"])


if __name__ == "__main__":
    unittest.main()
