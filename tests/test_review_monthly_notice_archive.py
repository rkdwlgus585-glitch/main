import tempfile
import unittest
from pathlib import Path

from scripts import review_monthly_notice_archive as review_notice


class ReviewMonthlyNoticeArchiveTest(unittest.TestCase):
    def _write_bundle(self, subject: str, body: str) -> tuple[Path, Path]:
        temp_dir = Path(tempfile.mkdtemp(prefix="notice-review-"))
        subject_path = temp_dir / "subject.txt"
        body_path = temp_dir / "body.html"
        subject_path.write_text(subject, encoding="utf-8")
        body_path.write_text(body, encoding="utf-8")
        return subject_path, body_path

    def test_missing_legal_notice_fails_review(self) -> None:
        subject_path, body_path = self._write_bundle(
            "[26년 3월] 건설업 양도양수 신규 매물 2선 - 서울건설정보 엄선",
            """
            <div>
              <h1>3월 신규 매물</h1>
              <p>아래 매물 제목을 클릭하면 상세 페이지로 바로 이동합니다.</p>
              <p><strong>핵심 요약</strong> 요약 문구</p>
              <ul>
                <li><a href="https://seoulmna.co.kr/mna/1">[매물 1 | 건축 양도 | 양도가 1억]</a></li>
                <li><a href="https://seoulmna.co.kr/mna/2">[매물 2 | 토목 양도 | 양도가 2억]</a></li>
              </ul>
              <a href="https://open.kakao.com/o/test">카카오톡 1:1 상담</a>
              <a href="tel:01012345678">전화 바로 연결</a>
              <img src="https://example.com/a.jpg" alt="대표 이미지">
            </div>
            """,
        )
        row = review_notice._review_month(
            {"month_key": "2026-03", "count": 2, "subject": str(subject_path), "body": str(body_path)}
        )

        self.assertEqual(row["status"], "fail")
        self.assertIn("legal_notice_missing", row["blocking_issues"])

    def test_compliant_body_passes_review(self) -> None:
        subject_path, body_path = self._write_bundle(
            "[26년 3월] 건설업 양도양수 신규 매물 2선 - 서울건설정보 엄선",
            """
            <div>
              <h1>3월 신규 매물</h1>
              <h2>핵심 요약</h2>
              <p>아래 매물 제목을 클릭하면 상세 페이지로 바로 이동합니다.</p>
              <p>건설업 양도양수 신규 매물 요약입니다.</p>
              <p>안내: 최종 거래 조건과 양도가, 법무·세무 판단은 계약 및 실사 이후 확정됩니다.</p>
              <p>원하는 조건의 비공개 매물도 1:1 상담으로 안내합니다.</p>
              <ul>
                <li><a href="https://seoulmna.co.kr/mna/1">[매물 1 | 건축 양도 | 양도가 1억]</a></li>
                <li><a href="https://seoulmna.co.kr/mna/2">[매물 2 | 토목 양도 | 양도가 2억]</a></li>
              </ul>
              <a href="https://open.kakao.com/o/test">카카오톡 1:1 상담</a>
              <a href="tel:01012345678">전화 바로 연결</a>
              <img src="https://example.com/a.jpg" alt="대표 이미지">
            </div>
            """,
        )
        row = review_notice._review_month(
            {"month_key": "2026-03", "count": 2, "subject": str(subject_path), "body": str(body_path)}
        )

        self.assertEqual(row["status"], "pass")
        self.assertEqual(row["blocking_issues"], [])

    def test_listing_count_mismatch_fails_review(self) -> None:
        subject_path, body_path = self._write_bundle(
            "[26년 3월] 건설업 양도양수 신규 매물 3선 - 서울건설정보 엄선",
            """
            <div>
              <h1>3월 신규 매물</h1>
              <h2>핵심 요약</h2>
              <p>아래 매물 제목을 클릭하면 상세 페이지로 바로 이동합니다.</p>
              <p>안내: 최종 거래 조건과 양도가, 법무·세무 판단은 계약 및 실사 이후 확정됩니다.</p>
              <ul>
                <li><a href="https://seoulmna.co.kr/mna/1">[매물 1 | 건축 양도 | 양도가 1억]</a></li>
                <li><a href="https://seoulmna.co.kr/mna/2">[매물 2 | 토목 양도 | 양도가 2억]</a></li>
              </ul>
              <a href="https://open.kakao.com/o/test">카카오톡 1:1 상담</a>
              <a href="tel:01012345678">전화 바로 연결</a>
            </div>
            """,
        )
        row = review_notice._review_month(
            {"month_key": "2026-03", "count": 3, "subject": str(subject_path), "body": str(body_path)}
        )

        self.assertEqual(row["status"], "fail")
        self.assertIn("quality_score_below_threshold", row["blocking_issues"])
        self.assertIn("listing_link_coverage_ok", row["warnings"])

    def test_missing_business_label_adds_warning(self) -> None:
        subject_path, body_path = self._write_bundle(
            "[26년 3월] 건설업 양도양수 신규 매물 1선 - 서울건설정보 엄선",
            """
            <div>
              <h1>3월 신규 매물</h1>
              <h2>핵심 요약</h2>
              <p>아래 매물 제목을 클릭하면 상세 페이지로 바로 이동합니다.</p>
              <p>안내: 최종 거래 조건과 양도가, 법무·세무 판단은 계약 및 실사 이후 확정됩니다.</p>
              <p>원하는 조건의 비공개 매물도 1:1 상담으로 안내합니다.</p>
              <ul>
                <li><a href="https://seoulmna.co.kr/mna/1">[매물 1 | 면허년도 2023 | 양도가 협의 | 지방]</a></li>
              </ul>
              <a href="https://open.kakao.com/o/test">카카오톡 1:1 상담</a>
              <a href="tel:01012345678">전화 바로 연결</a>
            </div>
            """,
        )
        row = review_notice._review_month(
            {"month_key": "2026-03", "count": 1, "subject": str(subject_path), "body": str(body_path)}
        )

        self.assertEqual(row["status"], "pass")
        self.assertIn("listing_titles_without_business_label", row["warnings"])

    def test_quality_relaxation_allows_one_non_legal_gap_after_10pct_drop(self) -> None:
        subject_path, body_path = self._write_bundle(
            "[26년 3월] 건설업 양도양수 신규 매물 2선 - 서울건설정보 엄선",
            """
            <div>
              <h1>3월 신규 매물</h1>
              <h2>핵심 요약</h2>
              <p>건설업 양도양수 신규 매물 요약입니다.</p>
              <p>안내: 최종 거래 조건과 양도가, 법무·세무 판단은 계약 및 실사 이후 확정됩니다.</p>
              <p>원하는 조건의 비공개 매물도 1:1 상담으로 안내합니다.</p>
              <ul>
                <li><a href="https://seoulmna.co.kr/mna/1">[매물 1 | 건축 양도 | 양도가 1억]</a></li>
                <li><a href="https://seoulmna.co.kr/mna/2">[매물 2 | 토목 양도 | 양도가 2억]</a></li>
              </ul>
              <a href="https://open.kakao.com/o/test">카카오톡 1:1 상담</a>
              <a href="tel:01012345678">전화 바로 연결</a>
            </div>
            """,
        )

        strict_row = review_notice._review_month(
            {"month_key": "2026-03", "count": 2, "subject": str(subject_path), "body": str(body_path)}
        )
        relaxed_row = review_notice._review_month(
            {"month_key": "2026-03", "count": 2, "subject": str(subject_path), "body": str(body_path)},
            quality_relax_pct=0.10,
        )

        self.assertEqual(strict_row["status"], "fail")
        self.assertIn("quality_score_below_threshold", strict_row["blocking_issues"])
        self.assertEqual(relaxed_row["status"], "pass")


if __name__ == "__main__":
    unittest.main()
