import importlib
import unittest
from datetime import datetime as real_datetime


allmod = importlib.import_module("all")


class _FixedDateTime(real_datetime):
    current = real_datetime(2026, 3, 10, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.current


class AllSchedulerCatchupTest(unittest.TestCase):
    def test_parse_schedule_target_hours_prefers_explicit_slots(self) -> None:
        self.assertEqual(
            allmod._parse_schedule_target_hours("18, 12, invalid, 18", 21),
            (12, 18),
        )

    def test_scheduled_catchup_runs_for_noon_slot_after_previous_evening(self) -> None:
        original_datetime = allmod.datetime
        original_load = allmod._load_json_file
        original_save = allmod._save_json_file
        original_scraper = allmod.run_scraper
        original_reconcile = allmod.run_reconcile_published
        original_hours = allmod.SCHEDULE_TARGET_HOURS
        original_state_file = allmod.SCHEDULER_STATE_FILE

        saved = {}
        calls = {"scraper": 0, "reconcile": 0}
        try:
            _FixedDateTime.current = real_datetime(2026, 3, 10, 12, 0, 0)
            allmod.datetime = _FixedDateTime
            allmod.SCHEDULE_TARGET_HOURS = (12, 18)
            allmod.SCHEDULER_STATE_FILE = "test_scheduler_state.json"
            allmod._load_json_file = lambda path, default=None: {"last_slot_date": "2026-03-09"}
            allmod._save_json_file = lambda path, payload: saved.update({"path": path, "payload": dict(payload)})
            allmod.run_scraper = lambda upload_enabled=True, allow_sheet_jump=False, allow_low_quality_upload=False: calls.__setitem__("scraper", calls["scraper"] + 1)
            allmod.run_reconcile_published = lambda **kwargs: calls.__setitem__("reconcile", calls["reconcile"] + 1)

            allmod.run_scheduled_catchup(no_upload=True, reconcile_status_only=False)
        finally:
            allmod.datetime = original_datetime
            allmod._load_json_file = original_load
            allmod._save_json_file = original_save
            allmod.run_scraper = original_scraper
            allmod.run_reconcile_published = original_reconcile
            allmod.SCHEDULE_TARGET_HOURS = original_hours
            allmod.SCHEDULER_STATE_FILE = original_state_file

        self.assertEqual(calls["scraper"], 1)
        self.assertEqual(calls["reconcile"], 1)
        self.assertEqual(saved["path"], "test_scheduler_state.json")
        self.assertEqual(saved["payload"]["last_slot_key"], "2026-03-10T12")
        self.assertEqual(saved["payload"]["last_slot_hour"], 12)

    def test_scheduled_catchup_skips_when_same_slot_already_processed(self) -> None:
        original_datetime = allmod.datetime
        original_load = allmod._load_json_file
        original_save = allmod._save_json_file
        original_scraper = allmod.run_scraper
        original_reconcile = allmod.run_reconcile_published
        original_hours = allmod.SCHEDULE_TARGET_HOURS

        calls = {"scraper": 0, "reconcile": 0, "save": 0}
        try:
            _FixedDateTime.current = real_datetime(2026, 3, 10, 12, 30, 0)
            allmod.datetime = _FixedDateTime
            allmod.SCHEDULE_TARGET_HOURS = (12, 18)
            allmod._load_json_file = lambda path, default=None: {"last_slot_key": "2026-03-10T12"}
            allmod._save_json_file = lambda path, payload: calls.__setitem__("save", calls["save"] + 1)
            allmod.run_scraper = lambda upload_enabled=True, allow_sheet_jump=False, allow_low_quality_upload=False: calls.__setitem__("scraper", calls["scraper"] + 1)
            allmod.run_reconcile_published = lambda **kwargs: calls.__setitem__("reconcile", calls["reconcile"] + 1)

            allmod.run_scheduled_catchup()
        finally:
            allmod.datetime = original_datetime
            allmod._load_json_file = original_load
            allmod._save_json_file = original_save
            allmod.run_scraper = original_scraper
            allmod.run_reconcile_published = original_reconcile
            allmod.SCHEDULE_TARGET_HOURS = original_hours

        self.assertEqual(calls["scraper"], 0)
        self.assertEqual(calls["reconcile"], 0)
        self.assertEqual(calls["save"], 0)


if __name__ == "__main__":
    unittest.main()
