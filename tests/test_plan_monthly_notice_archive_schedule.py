import unittest
from datetime import date

from scripts import plan_monthly_notice_archive_schedule as notice_schedule


class PlanMonthlyNoticeArchiveScheduleTest(unittest.TestCase):
    def test_missing_month_post_runs_on_first_day(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 4, 1),
            publish_state={"months": {}},
            run_state={"last_attempt": {}},
        )

        self.assertTrue(plan["should_run"])
        self.assertEqual(plan["schedule_kind"], "create")
        self.assertEqual(plan["slot"], "create-w1-d01")

    def test_missing_month_post_runs_on_second_day_catchup(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 4, 2),
            publish_state={"months": {}},
            run_state={"last_attempt": {}},
        )

        self.assertTrue(plan["should_run"])
        self.assertEqual(plan["schedule_kind"], "create")
        self.assertEqual(plan["slot"], "create-w1-d02")

    def test_skips_second_attempt_on_same_day(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 4, 2),
            publish_state={"months": {}},
            run_state={"last_attempt": {"month_key": "2026-04", "run_date": "2026-04-02"}},
        )

        self.assertFalse(plan["should_run"])
        self.assertEqual(plan["reason"], "already-attempted-today")

    def test_existing_post_skips_non_monday(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 3, 6),
            publish_state={"months": {"2026-03": {"wr_id": 361, "last_synced_at": "2026-03-05T21:23:00"}}},
            run_state={"last_attempt": {}},
        )

        self.assertFalse(plan["should_run"])
        self.assertEqual(plan["reason"], "not-monday")

    def test_existing_post_runs_once_on_monday(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 3, 9),
            publish_state={"months": {"2026-03": {"wr_id": 361, "last_synced_at": "2026-03-05T21:23:00"}}},
            run_state={"last_attempt": {}},
        )

        self.assertTrue(plan["should_run"])
        self.assertEqual(plan["schedule_kind"], "update")
        self.assertEqual(plan["slot"], "week-2")

    def test_existing_post_skips_if_already_published_same_week(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 3, 9),
            publish_state={"months": {"2026-03": {"wr_id": 361, "last_schedule_week": "2026-W11"}}},
            run_state={"last_attempt": {}},
        )

        self.assertFalse(plan["should_run"])
        self.assertEqual(plan["reason"], "already-published-this-week")

    def test_existing_post_skips_if_already_attempted_today(self) -> None:
        plan = notice_schedule._describe_schedule(
            today=date(2026, 3, 16),
            publish_state={"months": {"2026-03": {"wr_id": 361, "last_schedule_week": "2026-W11"}}},
            run_state={"last_attempt": {"month_key": "2026-03", "run_date": "2026-03-16"}},
        )

        self.assertFalse(plan["should_run"])
        self.assertEqual(plan["reason"], "already-attempted-today")


if __name__ == "__main__":
    unittest.main()
