import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import publish_monthly_market_report as market_publish


class PublishMonthlyMarketReportTests(unittest.TestCase):
    def test_previous_month_key_rolls_over_year_boundary(self) -> None:
        self.assertEqual(market_publish._previous_month_key("2026-03"), "2026-02")
        self.assertEqual(market_publish._previous_month_key("2026-01"), "2025-12")

    def test_month_subject_tokens_include_short_and_full_year(self) -> None:
        tokens = market_publish._month_subject_tokens("2026-03")
        self.assertIn("26년 3월", tokens)
        self.assertIn("2026년 03월", tokens)

    def test_main_blocks_publish_when_review_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            month_dir = root / "output" / "2026_03"
            month_dir.mkdir(parents=True, exist_ok=True)
            (month_dir / "market_report_2026_03_subject.txt").write_text("[26년 3월] 테스트 리포트\n", encoding="utf-8")
            (month_dir / "market_report_2026_03_body.html").write_text("<div>body</div>", encoding="utf-8")
            state_file = root / "state.json"
            report_json = root / "review.json"
            report_md = root / "review.md"
            review_result = {
                "month_key": "2026-03",
                "status": "fail",
                "blocking_issues": ["internal_only_language_detected"],
                "warnings": [],
                "stats": {},
            }
            review_report = {"ok": False, "result": review_result}
            argv = [
                "publish_monthly_market_report.py",
                "--year",
                "2026",
                "--month",
                "3",
                "--output-dir",
                str(root / "output"),
                "--state-file",
                str(state_file),
                "--review-report-json",
                str(report_json),
                "--review-report-md",
                str(report_md),
            ]
            with mock.patch.object(sys, "argv", argv):
                with mock.patch.object(market_publish.market_review, "review_bundle", return_value=review_result):
                    with mock.patch.object(market_publish.market_review, "build_review_report", return_value=review_report):
                        with mock.patch.object(market_publish.market_review, "write_review_report") as write_review:
                            with mock.patch.object(market_publish.listing_ops, "MnaBoardPublisher") as publisher_cls:
                                rc = market_publish.main()
            self.assertEqual(rc, 1)
            write_review.assert_called_once()
            publisher_cls.assert_not_called()

    def test_main_skips_publish_when_content_hash_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            month_dir = root / "output" / "2026_03"
            month_dir.mkdir(parents=True, exist_ok=True)
            subject = "[26년 3월] 테스트 리포트"
            body = "<div>body</div>"
            (month_dir / "market_report_2026_03_subject.txt").write_text(subject + "\n", encoding="utf-8")
            (month_dir / "market_report_2026_03_body.html").write_text(body, encoding="utf-8")
            digest = market_publish._content_hash(subject, body)
            state_file = root / "state.json"
            state_file.write_text(
                json.dumps(
                    {
                        "months": {
                            "2026-03": {
                                "wr_id": 363,
                                "url": "https://seoulmna.co.kr/notice/363",
                                "content_hash": digest,
                                "notice_enabled": True,
                            }
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            report_json = root / "review.json"
            report_md = root / "review.md"
            review_result = {
                "month_key": "2026-03",
                "status": "pass",
                "blocking_issues": [],
                "warnings": [],
                "stats": {},
            }
            review_report = {"ok": True, "result": review_result}
            argv = [
                "publish_monthly_market_report.py",
                "--year",
                "2026",
                "--month",
                "3",
                "--output-dir",
                str(root / "output"),
                "--state-file",
                str(state_file),
                "--review-report-json",
                str(report_json),
                "--review-report-md",
                str(report_md),
            ]
            with mock.patch.object(sys, "argv", argv):
                with mock.patch.object(market_publish.market_review, "review_bundle", return_value=review_result):
                    with mock.patch.object(market_publish.market_review, "build_review_report", return_value=review_report):
                        with mock.patch.object(market_publish.market_review, "write_review_report") as write_review:
                            with mock.patch.object(market_publish.listing_ops, "MnaBoardPublisher") as publisher_cls:
                                rc = market_publish.main()
            self.assertEqual(rc, 0)
            write_review.assert_called_once()
            publisher_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
