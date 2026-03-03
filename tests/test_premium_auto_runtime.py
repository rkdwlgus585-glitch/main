import unittest
from unittest.mock import patch

import premium_auto


class _FakeCrawler:
    def __init__(self, driver=None):
        self.driver = driver

    def get_next_target_number(self, start_from=7611):
        return 7619

    def fetch_mna_data(self, mna_number):
        return {"번호": int(mna_number), "업종": "건축공사업"}

    def is_number_in_latest_premium(self, number, limit=30):
        return True, {"number": int(number), "title": f"매물 {number}"}, []


class _FakeGenerator:
    def generate_article(self, data):
        return {"summary_points": ["요약"], "analysis": [], "faq": [], "title": "테스트 제목"}

    def render_html(self, data, ai_content):
        return "<p>content</p>", "테스트 제목"


class _FakeThumbnail:
    def create_summary_image(self, data, ai_content, output_path="summary_thumb.png"):
        return "summary_thumb.jpg"


class _FakePublisherSessionRetry:
    instance_count = 0

    def __init__(self, headless=False):
        _FakePublisherSessionRetry.instance_count += 1
        self.instance_id = _FakePublisherSessionRetry.instance_count
        self.last_error_kind = ""
        self.driver = object()

    def login(self):
        return True

    def open_write_page(self):
        if self.instance_id == 1:
            self.last_error_kind = "session"
            return False
        return True

    def set_title(self, title):
        return True

    def set_content_smarteditor(self, html_content):
        return True

    def upload_image(self, image_path):
        return True

    def close(self):
        return None


class _FakePublisherOperationFail:
    instance_count = 0

    def __init__(self, headless=False):
        _FakePublisherOperationFail.instance_count += 1
        self.last_error_kind = ""
        self.driver = object()

    def login(self):
        return True

    def open_write_page(self):
        self.last_error_kind = "operation"
        return False

    def set_title(self, title):
        return True

    def set_content_smarteditor(self, html_content):
        return True

    def upload_image(self, image_path):
        return True

    def close(self):
        return None


class PremiumAutoRuntimeTest(unittest.TestCase):
    def test_run_automation_retries_once_on_session_drop(self):
        _FakePublisherSessionRetry.instance_count = 0
        with patch.object(premium_auto, "ensure_config", return_value=None), patch.object(
            premium_auto, "PremiumPublisher", _FakePublisherSessionRetry
        ), patch.object(
            premium_auto, "PremiumCrawler", _FakeCrawler
        ), patch.object(
            premium_auto, "ContentGenerator", _FakeGenerator
        ), patch.object(
            premium_auto, "ThumbnailMaker", _FakeThumbnail
        ), patch.object(
            premium_auto, "_write_premium_run_report", return_value=None
        ), patch(
            "builtins.input", return_value=""
        ):
            result = premium_auto.run_automation(start_from=7611, headless=True, verify_publish=True)

        self.assertTrue(result.get("ok"), msg=result)
        self.assertTrue(result.get("retry_used"), msg=result)
        self.assertEqual(_FakePublisherSessionRetry.instance_count, 2)

    def test_run_automation_does_not_retry_on_operation_fail(self):
        _FakePublisherOperationFail.instance_count = 0
        with patch.object(premium_auto, "ensure_config", return_value=None), patch.object(
            premium_auto, "PremiumPublisher", _FakePublisherOperationFail
        ), patch.object(
            premium_auto, "PremiumCrawler", _FakeCrawler
        ), patch.object(
            premium_auto, "ContentGenerator", _FakeGenerator
        ), patch.object(
            premium_auto, "ThumbnailMaker", _FakeThumbnail
        ), patch.object(
            premium_auto, "_write_premium_run_report", return_value=None
        ), patch(
            "builtins.input", return_value=""
        ):
            result = premium_auto.run_automation(start_from=7611, headless=True, verify_publish=True)

        self.assertFalse(result.get("ok"), msg=result)
        self.assertEqual(result.get("reason"), "open_write_failed")
        self.assertFalse(result.get("retry_used"), msg=result)
        self.assertEqual(_FakePublisherOperationFail.instance_count, 1)


if __name__ == "__main__":
    unittest.main()

