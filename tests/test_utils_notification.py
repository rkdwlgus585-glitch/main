"""Unit tests for utils.Notifier retry, send, and error-handling logic.

Covers: _post_with_retry, send, _send_discord, _send_slack.
All HTTP is mocked — no real network calls.
"""

import unittest
from unittest.mock import patch, MagicMock

from utils import Notifier


class _FakeResponse:
    """Minimal requests.Response substitute."""

    def __init__(self, status_code: int = 200):
        self.status_code = status_code


class PostWithRetryTest(unittest.TestCase):
    """Tests for Notifier._post_with_retry()."""

    def _make(self, **kw) -> Notifier:
        return Notifier(**kw)

    @patch("utils.requests.post")
    def test_success_on_first_try(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = self._make()
        self.assertTrue(n._post_with_retry("http://x", {}, {200}, "test"))
        self.assertEqual(mock_post.call_count, 1)

    @patch("utils.requests.post")
    def test_success_after_retry(self, mock_post):
        mock_post.side_effect = [
            _FakeResponse(500),
            _FakeResponse(200),
        ]
        n = self._make()
        n.RETRY_DELAY = 0  # skip sleep
        self.assertTrue(n._post_with_retry("http://x", {}, {200}, "test"))
        self.assertEqual(mock_post.call_count, 2)

    @patch("utils.requests.post")
    def test_all_retries_fail_returns_false(self, mock_post):
        mock_post.return_value = _FakeResponse(500)
        n = self._make()
        n.RETRY_DELAY = 0
        self.assertFalse(n._post_with_retry("http://x", {}, {200}, "test"))
        self.assertEqual(mock_post.call_count, n.MAX_RETRIES + 1)

    @patch("utils.requests.post")
    def test_network_error_retries(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError("refused")
        n = self._make()
        n.RETRY_DELAY = 0
        self.assertFalse(n._post_with_retry("http://x", {}, {200}, "test"))
        self.assertEqual(mock_post.call_count, n.MAX_RETRIES + 1)

    @patch("utils.requests.post")
    def test_os_error_retries(self, mock_post):
        mock_post.side_effect = OSError("socket failed")
        n = self._make()
        n.RETRY_DELAY = 0
        self.assertFalse(n._post_with_retry("http://x", {}, {200}, "test"))

    @patch("utils.requests.post")
    def test_error_message_no_info_leak(self, mock_post):
        """Ensure exception details (URLs, paths) are NOT logged."""
        import requests as req
        mock_post.side_effect = req.ConnectionError("http://secret.internal:9200/data")
        n = self._make()
        n.RETRY_DELAY = 0
        with self.assertLogs("mnakr", level="WARNING") as cm:
            n._post_with_retry("http://x", {}, {200}, "Discord")
        log_line = cm.output[0]
        self.assertNotIn("secret.internal", log_line)
        self.assertNotIn("9200", log_line)
        self.assertIn("ConnectionError", log_line)

    @patch("utils.requests.post")
    def test_status_code_in_error_log(self, mock_post):
        """Non-ok status code IS safe to log (no sensitive data)."""
        mock_post.return_value = _FakeResponse(429)
        n = self._make()
        n.RETRY_DELAY = 0
        with self.assertLogs("mnakr", level="WARNING") as cm:
            n._post_with_retry("http://x", {}, {200}, "Slack")
        self.assertIn("status=429", cm.output[0])

    @patch("utils.requests.post")
    def test_multiple_ok_statuses(self, mock_post):
        mock_post.return_value = _FakeResponse(204)
        n = self._make()
        self.assertTrue(n._post_with_retry("http://x", {}, {200, 204}, "test"))


class SendTest(unittest.TestCase):
    """Tests for Notifier.send()."""

    @patch("utils.requests.post")
    def test_no_webhooks_returns_false(self, mock_post):
        n = Notifier(discord_url="", slack_url="")
        self.assertFalse(n.send("hello"))
        mock_post.assert_not_called()

    @patch("utils.requests.post")
    def test_discord_only(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(discord_url="http://discord.test")
        self.assertTrue(n.send("test msg"))
        self.assertEqual(mock_post.call_count, 1)

    @patch("utils.requests.post")
    def test_slack_only(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(slack_url="http://slack.test")
        self.assertTrue(n.send("test msg"))
        self.assertEqual(mock_post.call_count, 1)

    @patch("utils.requests.post")
    def test_both_channels(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(discord_url="http://discord.test", slack_url="http://slack.test")
        self.assertTrue(n.send("test msg"))
        self.assertEqual(mock_post.call_count, 2)

    @patch("utils.requests.post")
    def test_one_fails_returns_false(self, mock_post):
        """If one channel fails, send() returns False."""
        mock_post.side_effect = [
            _FakeResponse(200),  # discord ok
            _FakeResponse(500),  # slack fail
            _FakeResponse(500),  # slack retry 1
            _FakeResponse(500),  # slack retry 2
        ]
        n = Notifier(discord_url="http://d", slack_url="http://s")
        n.RETRY_DELAY = 0
        self.assertFalse(n.send("test"))


class SendDiscordTest(unittest.TestCase):
    """Tests for Notifier._send_discord() payload structure."""

    @patch("utils.requests.post")
    def test_payload_has_embed(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(discord_url="http://d.test")
        n._send_discord("hello", "title")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertIn("embeds", payload)
        self.assertEqual(payload["embeds"][0]["title"], "title")
        self.assertEqual(payload["embeds"][0]["description"], "hello")

    @patch("utils.requests.post")
    def test_title_truncated(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(discord_url="http://d.test")
        n._send_discord("msg", "A" * 300)
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertLessEqual(len(payload["embeds"][0]["title"]), 240)

    @patch("utils.requests.post")
    def test_accepts_204(self, mock_post):
        mock_post.return_value = _FakeResponse(204)
        n = Notifier(discord_url="http://d.test")
        self.assertTrue(n._send_discord("msg", "title"))


class SendSlackTest(unittest.TestCase):
    """Tests for Notifier._send_slack() payload structure."""

    @patch("utils.requests.post")
    def test_payload_has_text(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(slack_url="http://s.test")
        n._send_slack("hello", "title")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertIn("text", payload)
        self.assertIn("hello", payload["text"])
        self.assertIn("title", payload["text"])

    @patch("utils.requests.post")
    def test_empty_title_fallback(self, mock_post):
        mock_post.return_value = _FakeResponse(200)
        n = Notifier(slack_url="http://s.test")
        n._send_slack("msg", "")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        # empty title should fall back to default
        self.assertIn("msg", payload["text"])


if __name__ == "__main__":
    unittest.main()
