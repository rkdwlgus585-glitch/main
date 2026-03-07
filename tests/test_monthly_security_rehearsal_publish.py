import unittest

from scripts.monthly_security_rehearsal import _build_publish_content


class MonthlySecurityRehearsalPublishTests(unittest.TestCase):
    def test_build_publish_content_all_success(self):
        payload = {
            "generated_at": "2026-03-05 10:00:00",
            "ok": True,
            "steps": [
                {"name": "a", "ok": True, "returncode": 0},
                {"name": "b", "ok": True, "returncode": 0},
            ],
        }

        message, ticket_md, stats = _build_publish_content(payload)
        self.assertIn("overall_ok: True", message)
        self.assertEqual(stats["step_count"], 2)
        self.assertEqual(stats["fail_count"], 0)
        self.assertIn("| a | True | 0 |", ticket_md)

    def test_build_publish_content_with_failure(self):
        payload = {
            "generated_at": "2026-03-05 10:00:00",
            "ok": False,
            "steps": [
                {"name": "a", "ok": True, "returncode": 0, "stderr": ""},
                {"name": "b", "ok": False, "returncode": 1, "stderr": "failure detail"},
            ],
        }

        message, ticket_md, stats = _build_publish_content(payload)
        self.assertIn("fail_count: 1", message)
        self.assertEqual(stats["fail_count"], 1)
        self.assertIn("## Failures", ticket_md)
        self.assertIn("failure detail", ticket_md)


if __name__ == "__main__":
    unittest.main()
