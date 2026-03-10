"""Comprehensive tests for consult_match_scheduler.py — scheduler pure functions."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from consult_match_scheduler import (
    _build_parser,
    _cfg_bool,
    _load_state,
    _parse_hhmm,
    _same_local_day,
    _save_state,
    _state_path,
    _target_hhmm_int,
    run_match_once,
    show_status,
)


# ────────────────────────────────────────────────
# _cfg_bool
# ────────────────────────────────────────────────


class TestCfgBool:
    @patch("consult_match_scheduler.CONFIG", {"k": "true"})
    def test_true_string(self) -> None:
        assert _cfg_bool("k") is True

    @patch("consult_match_scheduler.CONFIG", {"k": "false"})
    def test_false_string(self) -> None:
        assert _cfg_bool("k") is False

    @patch("consult_match_scheduler.CONFIG", {"k": "1"})
    def test_one_is_true(self) -> None:
        assert _cfg_bool("k") is True

    @patch("consult_match_scheduler.CONFIG", {"k": "0"})
    def test_zero_is_false(self) -> None:
        assert _cfg_bool("k") is False

    @patch("consult_match_scheduler.CONFIG", {"k": "yes"})
    def test_yes(self) -> None:
        assert _cfg_bool("k") is True

    @patch("consult_match_scheduler.CONFIG", {"k": "no"})
    def test_no(self) -> None:
        assert _cfg_bool("k") is False

    @patch("consult_match_scheduler.CONFIG", {"k": "on"})
    def test_on(self) -> None:
        assert _cfg_bool("k") is True

    @patch("consult_match_scheduler.CONFIG", {"k": "off"})
    def test_off(self) -> None:
        assert _cfg_bool("k") is False

    @patch("consult_match_scheduler.CONFIG", {"k": "y"})
    def test_y(self) -> None:
        assert _cfg_bool("k") is True

    @patch("consult_match_scheduler.CONFIG", {"k": "n"})
    def test_n(self) -> None:
        assert _cfg_bool("k") is False

    @patch("consult_match_scheduler.CONFIG", {"k": "  TRUE  "})
    def test_whitespace_trimmed(self) -> None:
        assert _cfg_bool("k") is True

    @patch("consult_match_scheduler.CONFIG", {})
    def test_missing_key_default_false(self) -> None:
        assert _cfg_bool("missing") is False

    @patch("consult_match_scheduler.CONFIG", {})
    def test_missing_key_default_true(self) -> None:
        assert _cfg_bool("missing", True) is True

    @patch("consult_match_scheduler.CONFIG", {"k": "random"})
    def test_unrecognized_value_uses_default(self) -> None:
        assert _cfg_bool("k", True) is True
        assert _cfg_bool("k", False) is False


# ────────────────────────────────────────────────
# _parse_hhmm
# ────────────────────────────────────────────────


class TestParseHhmm:
    def test_basic(self) -> None:
        assert _parse_hhmm("09:40") == (9, 40)

    def test_midnight(self) -> None:
        assert _parse_hhmm("00:00") == (0, 0)

    def test_end_of_day(self) -> None:
        assert _parse_hhmm("23:59") == (23, 59)

    def test_single_digit(self) -> None:
        assert _parse_hhmm("9:5") == (9, 5)

    def test_invalid_hour(self) -> None:
        with pytest.raises(ValueError, match="invalid HH:MM"):
            _parse_hhmm("25:00")

    def test_invalid_minute(self) -> None:
        with pytest.raises(ValueError, match="invalid HH:MM"):
            _parse_hhmm("12:60")

    def test_negative_hour(self) -> None:
        with pytest.raises(ValueError, match="invalid HH:MM"):
            _parse_hhmm("-1:00")

    def test_missing_colon(self) -> None:
        with pytest.raises(ValueError):
            _parse_hhmm("0930")

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError):
            _parse_hhmm("")


# ────────────────────────────────────────────────
# _target_hhmm_int
# ────────────────────────────────────────────────


class TestTargetHhmmInt:
    def test_basic(self) -> None:
        assert _target_hhmm_int("09:40") == 9 * 60 + 40

    def test_midnight(self) -> None:
        assert _target_hhmm_int("00:00") == 0

    def test_end_of_day(self) -> None:
        assert _target_hhmm_int("23:59") == 23 * 60 + 59


# ────────────────────────────────────────────────
# _same_local_day
# ────────────────────────────────────────────────


class TestSameLocalDay:
    def test_today(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        assert _same_local_day(now) is True

    def test_yesterday(self) -> None:
        yesterday = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
        assert _same_local_day(yesterday) is False

    def test_empty_string(self) -> None:
        assert _same_local_day("") is False

    def test_none(self) -> None:
        assert _same_local_day(None) is False

    def test_invalid_format(self) -> None:
        assert _same_local_day("not-a-date") is False

    def test_numeric(self) -> None:
        assert _same_local_day(12345) is False


# ────────────────────────────────────────────────
# _load_state / _save_state
# ────────────────────────────────────────────────


class TestStateIO:
    @patch("consult_match_scheduler._state_path")
    def test_load_missing_file(self, mock_path, tmp_path) -> None:
        mock_path.return_value = str(tmp_path / "nonexistent.json")
        state = _load_state()
        assert state == {"last_run": {}}

    @patch("consult_match_scheduler._state_path")
    def test_save_and_load_roundtrip(self, mock_path, tmp_path) -> None:
        path = str(tmp_path / "state.json")
        mock_path.return_value = path
        state = {"last_run": {"time": "2026-01-01", "success": True}}
        _save_state(state)
        loaded = _load_state()
        assert loaded["last_run"]["time"] == "2026-01-01"
        assert loaded["last_run"]["success"] is True
        assert "updated_at" in loaded

    @patch("consult_match_scheduler._state_path")
    def test_load_corrupted_json(self, mock_path, tmp_path) -> None:
        path = str(tmp_path / "bad.json")
        mock_path.return_value = path
        with open(path, "w") as f:
            f.write("{corrupt")
        state = _load_state()
        assert state == {"last_run": {}}

    @patch("consult_match_scheduler._state_path")
    def test_load_non_dict(self, mock_path, tmp_path) -> None:
        path = str(tmp_path / "list.json")
        mock_path.return_value = path
        with open(path, "w") as f:
            json.dump([1, 2, 3], f)
        state = _load_state()
        assert state == {"last_run": {}}

    @patch("consult_match_scheduler._state_path")
    def test_load_missing_last_run_key(self, mock_path, tmp_path) -> None:
        path = str(tmp_path / "no_last.json")
        mock_path.return_value = path
        with open(path, "w") as f:
            json.dump({"other": "data"}, f)
        state = _load_state()
        assert state["last_run"] == {}
        assert state["other"] == "data"

    @patch("consult_match_scheduler._state_path")
    def test_save_none_state(self, mock_path, tmp_path) -> None:
        path = str(tmp_path / "none.json")
        mock_path.return_value = path
        _save_state(None)
        loaded = _load_state()
        assert "updated_at" in loaded


# ────────────────────────────────────────────────
# _build_parser
# ────────────────────────────────────────────────


class TestBuildParser:
    def test_defaults(self) -> None:
        args = _build_parser().parse_args([])
        assert args.once is False
        assert args.status is False
        assert args.scheduler is False

    def test_once_flag(self) -> None:
        args = _build_parser().parse_args(["--once"])
        assert args.once is True

    def test_status_flag(self) -> None:
        args = _build_parser().parse_args(["--status"])
        assert args.status is True

    def test_scheduler_flag(self) -> None:
        args = _build_parser().parse_args(["--scheduler"])
        assert args.scheduler is True


# ────────────────────────────────────────────────
# run_match_once (mocked subprocess)
# ────────────────────────────────────────────────


class TestRunMatchOnce:
    @patch("consult_match_scheduler._save_state")
    @patch("consult_match_scheduler._load_state", return_value={"last_run": {}})
    @patch("consult_match_scheduler.subprocess.run")
    def test_success(self, mock_run, mock_load, mock_save) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        ok = run_match_once(reason="test")
        assert ok is True
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["last_run"]["success"] is True
        assert saved["last_run"]["reason"] == "test"

    @patch("consult_match_scheduler._save_state")
    @patch("consult_match_scheduler._load_state", return_value={"last_run": {}})
    @patch("consult_match_scheduler.subprocess.run")
    def test_failure(self, mock_run, mock_load, mock_save) -> None:
        mock_run.return_value = MagicMock(returncode=1)
        ok = run_match_once(reason="test_fail")
        assert ok is False
        saved = mock_save.call_args[0][0]
        assert saved["last_run"]["success"] is False
        assert saved["last_run"]["exit_code"] == 1

    @patch("consult_match_scheduler._save_state")
    @patch("consult_match_scheduler._load_state", return_value={"last_run": {}})
    @patch("consult_match_scheduler.subprocess.run", side_effect=OSError("spawn failed"))
    def test_os_error(self, mock_run, mock_load, mock_save) -> None:
        ok = run_match_once()
        assert ok is False
        saved = mock_save.call_args[0][0]
        assert "spawn failed" in saved["last_run"]["error"]


# ────────────────────────────────────────────────
# show_status (stdout capture)
# ────────────────────────────────────────────────


class TestShowStatus:
    @patch("consult_match_scheduler._load_state", return_value={"last_run": {}})
    def test_no_last_run(self, mock_load, capsys) -> None:
        show_status()
        out = capsys.readouterr().out
        assert "last_run=never" in out

    @patch("consult_match_scheduler._load_state", return_value={
        "last_run": {
            "time": "2026-03-10T09:40:00",
            "reason": "daily_schedule",
            "success": True,
            "exit_code": 0,
            "error": "",
        }
    })
    def test_with_last_run(self, mock_load, capsys) -> None:
        show_status()
        out = capsys.readouterr().out
        assert "2026-03-10T09:40:00" in out
        assert "daily_schedule" in out
        assert "True" in out
