import unittest

from scripts import monthly_notice_rotation


class MonthlyNoticeRotationTests(unittest.TestCase):
    def test_pick_previous_notice_month_uses_latest_prior_month(self) -> None:
        month_state = {
            "2026-01": {"wr_id": 300, "notice_enabled": False},
            "2026-02": {"wr_id": 346},
            "2026-03": {"wr_id": 361, "notice_enabled": True},
        }
        self.assertEqual(
            monthly_notice_rotation.pick_previous_notice_month(month_state, "2026-03"),
            "2026-02",
        )

    def test_set_notice_flag_enables_and_clears_checkbox(self) -> None:
        payload = {"bo_table": "notice", "notice": "1", "wr_subject": "x"}
        self.assertEqual(
            monthly_notice_rotation.set_notice_flag(payload, enabled=True)["notice"],
            "1",
        )
        self.assertNotIn(
            "notice",
            monthly_notice_rotation.set_notice_flag(payload, enabled=False),
        )


if __name__ == "__main__":
    unittest.main()
