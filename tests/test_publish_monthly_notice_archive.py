import unittest
from datetime import datetime

from scripts import publish_monthly_notice_archive as notice_publish


class PublishMonthlyNoticeArchiveScheduleTest(unittest.TestCase):
    def test_content_hash_ignores_banner_date(self) -> None:
        subject = "[26년 3월] 건설업 양도양수 신규 매물 16선"
        body_a = "<p>서울건설정보 강지현 행정사 엄선 · 2026.03.06 기준</p>"
        body_b = "<p>서울건설정보 강지현 행정사 엄선 · 2026.03.10 기준</p>"

        self.assertEqual(
            notice_publish._content_hash(subject, body_a),
            notice_publish._content_hash(subject, body_b),
        )
        self.assertNotEqual(
            notice_publish._legacy_content_hash(subject, body_a),
            notice_publish._legacy_content_hash(subject, body_b),
        )

    def test_skips_non_current_month_in_scheduled_mode(self) -> None:
        plan = notice_publish._plan_sync_action(
            month_key="2026-02",
            digest="new",
            legacy_hashes={"legacy"},
            prev={"wr_id": 355, "content_hash": "old"},
            now=datetime(2026, 3, 9, 9, 0, 0),
            only_month="",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "skip")
        self.assertEqual(plan["reason"], "not-current-month")

    def test_allows_catchup_create_after_first_day(self) -> None:
        plan = notice_publish._plan_sync_action(
            month_key="2026-03",
            digest="new",
            legacy_hashes={"legacy"},
            prev={},
            now=datetime(2026, 3, 2, 9, 0, 0),
            only_month="",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["schedule_kind"], "catchup_create")

    def test_blocks_current_month_update_before_monday(self) -> None:
        plan = notice_publish._plan_sync_action(
            month_key="2026-03",
            digest="new",
            legacy_hashes={"legacy"},
            prev={"wr_id": 361, "content_hash": "old", "last_synced_at": "2026-03-03T12:00:00"},
            now=datetime(2026, 3, 6, 9, 0, 0),
            only_month="",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "skip")
        self.assertEqual(plan["reason"], "wait-until-monday")

    def test_blocks_second_monday_sync_in_same_iso_week(self) -> None:
        plan = notice_publish._plan_sync_action(
            month_key="2026-03",
            digest="new",
            legacy_hashes={"legacy"},
            prev={
                "wr_id": 361,
                "content_hash": "old",
                "last_schedule_week": "2026-W11",
                "last_synced_at": "2026-03-09T09:30:00",
            },
            now=datetime(2026, 3, 9, 15, 0, 0),
            only_month="",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "skip")
        self.assertEqual(plan["reason"], "already-synced-this-week")

    def test_allows_first_monday_sync_for_changed_current_month(self) -> None:
        plan = notice_publish._plan_sync_action(
            month_key="2026-03",
            digest="new",
            legacy_hashes={"legacy"},
            prev={
                "wr_id": 361,
                "content_hash": "old",
                "last_synced_at": "2026-03-05T21:23:00",
            },
            now=datetime(2026, 3, 9, 9, 0, 0),
            only_month="",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "update")
        self.assertEqual(plan["schedule_kind"], "weekly_monday_update")

    def test_targeted_month_still_uses_min_update_days(self) -> None:
        plan = notice_publish._plan_sync_action(
            month_key="2026-02",
            digest="new",
            legacy_hashes={"legacy"},
            prev={"wr_id": 355, "content_hash": "old", "last_synced_at": "2026-03-05T10:00:00"},
            now=datetime(2026, 3, 6, 9, 0, 0),
            only_month="2026-02",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "skip")
        self.assertEqual(plan["reason"], "min-update-days")

    def test_legacy_hash_compatibility_uses_last_synced_banner_date(self) -> None:
        subject = "[26년 3월] 건설업 양도양수 신규 매물 16선"
        current_body = "<p>서울건설정보 강지현 행정사 엄선 · 2026.03.06 기준</p>"
        previous_body = "<p>서울건설정보 강지현 행정사 엄선 · 2026.03.05 기준</p>"
        prev_hash = notice_publish._legacy_content_hash(subject, previous_body)

        plan = notice_publish._plan_sync_action(
            month_key="2026-03",
            digest=notice_publish._content_hash(subject, current_body),
            legacy_hashes=notice_publish._legacy_compatible_hashes(
                subject,
                current_body,
                {"last_synced_at": "2026-03-05T21:23:00"},
            ),
            prev={"wr_id": 361, "content_hash": prev_hash, "last_synced_at": "2026-03-05T21:23:00"},
            now=datetime(2026, 3, 6, 9, 0, 0),
            only_month="",
            min_update_days=7.0,
        )

        self.assertEqual(plan["action"], "skip")
        self.assertEqual(plan["reason"], "unchanged")


if __name__ == "__main__":
    unittest.main()
