import argparse
import importlib.util
import json
import pathlib
import tempfile
import types
import unittest
from unittest import mock


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1].parent / "ALL" / "tistory_ops" / "daily_publish.py"
SPEC = importlib.util.spec_from_file_location("tistory_daily_publish", SCRIPT_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class _FakeLookup:
    COL_SEQ = 0

    def _load_rows(self):
        return [
            ["등록번호"],
            ["7539"],
            ["7540"],
            ["7541"],
            ["7542"],
        ]

    def _row_value(self, row, idx):
        return row[idx] if idx < len(row) else ""


class TistoryDailyPublishTest(unittest.TestCase):
    def test_daily_once_picks_7540_then_updates_state_on_success(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = pathlib.Path(td) / "daily_state.json"
            calls = []

            def _fake_run(cmd, **_kwargs):
                calls.append(cmd)
                return types.SimpleNamespace(returncode=0, stdout='{"ok": true}', stderr="")

            args = argparse.Namespace(
                start_registration="7540",
                state_file=str(state_file),
                debugger="127.0.0.1:9222",
                ensure_chrome=False,
                chrome_user_data_dir="",
                chrome_wait_sec="1",
                login_wait_sec="120",
                interactive_login=True,
                draft_policy="discard",
                auto_login=True,
                seo_min_score="90",
                seo_gate=True,
                auto_images=True,
                image_count="2",
                allow_repeat=False,
                audit_tag="daily_test",
                print_command=False,
                dry_run=False,
                force=False,
            )

            with mock.patch.object(MOD.gabji, "ListingSheetLookup", _FakeLookup):
                with mock.patch.object(MOD, "_today_str", return_value="2026-02-25"):
                    with mock.patch.object(MOD.subprocess, "run", side_effect=_fake_run):
                        rc = MOD.run(args)

            self.assertEqual(rc, 0)
            self.assertEqual(len(calls), 1)
            self.assertIn("--registration", calls[0])
            self.assertIn("7540", calls[0])

            payload = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("last_registration"), "7540")
            self.assertEqual(payload.get("next_registration"), "7541")
            self.assertEqual(payload.get("last_publish_date"), "2026-02-25")

    def test_daily_once_dry_run_does_not_update_state(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = pathlib.Path(td) / "daily_state.json"
            state_file.write_text(
                json.dumps({"next_registration": "7540", "last_publish_date": "2026-02-24"}, ensure_ascii=False),
                encoding="utf-8",
            )
            calls = []

            def _fake_run(cmd, **_kwargs):
                calls.append(cmd)
                return types.SimpleNamespace(returncode=0, stdout='{"ok": true}', stderr="")

            args = argparse.Namespace(
                start_registration="7540",
                state_file=str(state_file),
                debugger="127.0.0.1:9222",
                ensure_chrome=False,
                chrome_user_data_dir="",
                chrome_wait_sec="1",
                login_wait_sec="120",
                interactive_login=True,
                draft_policy="discard",
                auto_login=True,
                seo_min_score="90",
                seo_gate=True,
                auto_images=True,
                image_count="2",
                allow_repeat=False,
                audit_tag="daily_test",
                print_command=False,
                dry_run=True,
                force=True,
            )

            with mock.patch.object(MOD.gabji, "ListingSheetLookup", _FakeLookup):
                with mock.patch.object(MOD, "_today_str", return_value="2026-02-25"):
                    with mock.patch.object(MOD.subprocess, "run", side_effect=_fake_run):
                        rc = MOD.run(args)

            self.assertEqual(rc, 0)
            self.assertEqual(len(calls), 1)
            payload = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("next_registration"), "7540")
            self.assertEqual(payload.get("last_publish_date"), "2026-02-24")

    def test_daily_once_skips_when_already_posted_today(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = pathlib.Path(td) / "daily_state.json"
            state_file.write_text(
                json.dumps({"last_publish_date": "2026-02-25"}, ensure_ascii=False),
                encoding="utf-8",
            )

            args = argparse.Namespace(
                start_registration="7540",
                state_file=str(state_file),
                debugger="127.0.0.1:9222",
                ensure_chrome=False,
                chrome_user_data_dir="",
                chrome_wait_sec="1",
                login_wait_sec="120",
                interactive_login=True,
                draft_policy="discard",
                auto_login=True,
                seo_min_score="90",
                seo_gate=True,
                auto_images=True,
                image_count="2",
                allow_repeat=False,
                audit_tag="daily_test",
                print_command=False,
                dry_run=True,
                force=False,
            )

            with mock.patch.object(MOD, "_today_str", return_value="2026-02-25"):
                with mock.patch.object(MOD.subprocess, "run") as sp:
                    rc = MOD.run(args)
            self.assertEqual(rc, 0)
            sp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
