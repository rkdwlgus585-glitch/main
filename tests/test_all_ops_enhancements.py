import importlib
import unittest


allmod = importlib.import_module("all")


class AllOpsEnhancementsTest(unittest.TestCase):
    def test_format_admin_price_keeps_gap_expression(self):
        self.assertEqual(
            allmod._format_admin_price_for_memo("2.1억~2.6억 / 2.6억"),
            "2.1억~2.6억 / 2.6억",
        )

    def test_validate_admin_memo_rejects_legacy_token(self):
        memo = (
            "UID 11840 토목\n"
            "시트기준 입금가/양도가: 11840 토목 2.1억~2.6억 / 2.6억\n"
            "http://www.nowmna.com/yangdo_view1.php?uid=11840&page_no=1"
        )
        ok, diag = allmod._validate_admin_memo_format(memo, require_br=True)
        self.assertFalse(ok)
        self.assertIn("legacy_token_detected", diag.get("errors", []))

    def test_detect_defer_request_reason(self):
        reason = allmod._detect_defer_request_reason("삭제 후 나중에 재등록 요청")
        self.assertTrue(bool(reason))

    def test_evaluate_listing_quality_reports_recommended_images(self):
        item = {
            "license": "civil\nbuild",
            "memo": "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8",
            "price": "2.6억",
            "source_url": "http://www.nowmna.com/yangdo_view1.php?uid=11840&page_no=1",
        }
        quality = allmod._evaluate_listing_quality(item)
        self.assertTrue(quality.get("score", 0) > 0)
        self.assertEqual(quality.get("recommended_images"), 2)


if __name__ == "__main__":
    unittest.main()

