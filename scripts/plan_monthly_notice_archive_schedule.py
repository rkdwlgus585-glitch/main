#!/usr/bin/env python3
"""
Plan whether the monthly notice archive pipeline should run today.

Policy:
- If the current month post does not exist, attempt creation once per day until created.
- If the current month post exists, allow one weekly refresh on Mondays only.
- The watchdog pipeline should execute at most once per calendar day.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLISH_STATE = ROOT / "logs" / "notice_publish_state.json"
DEFAULT_RUN_STATE = ROOT / "logs" / "notice_archive_schedule_state.json"
SKIP_EXIT_CODE = 10


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(_read_text(path))
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _iso_week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_of_month(day: date) -> int:
    return ((int(day.day) - 1) // 7) + 1


def _parse_iso_datetime(raw: str) -> datetime | None:
    txt = str(raw or "").strip()
    if not txt:
        return None
    try:
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def _published_week_key(entry: dict) -> str:
    explicit = str(entry.get("last_schedule_week", "")).strip()
    if explicit:
        return explicit
    fallback = _parse_iso_datetime(entry.get("last_synced_at", ""))
    if fallback is None:
        return ""
    return _iso_week_key(fallback)


def _parse_day(raw: str) -> date:
    txt = str(raw or "").strip()
    if not txt:
        return datetime.now().date()
    return datetime.strptime(txt, "%Y-%m-%d").date()


def _describe_schedule(today: date, publish_state: dict, run_state: dict) -> dict:
    month_key = _month_key(today)
    publish_months = dict(publish_state.get("months", {}) or {})
    month_entry = dict(publish_months.get(month_key, {}) or {})
    today_iso = today.isoformat()
    week_index = _week_of_month(today)
    run_last = dict(run_state.get("last_attempt", {}) or {})

    wr_id = int(month_entry.get("wr_id", 0) or 0)
    if wr_id <= 0:
        slot = f"create-w{week_index}-d{today.day:02d}"
        if str(run_last.get("run_date", "")).strip() == today_iso and str(run_last.get("month_key", "")).strip() == month_key:
            return {
                "should_run": False,
                "reason": "already-attempted-today",
                "month_key": month_key,
                "slot": slot,
                "schedule_kind": "create",
            }
        return {
            "should_run": True,
            "reason": "missing-current-month-post",
            "month_key": month_key,
            "slot": slot,
            "schedule_kind": "create",
        }

    if today.weekday() != 0:
        return {
            "should_run": False,
            "reason": "not-monday",
            "month_key": month_key,
            "slot": f"week-{week_index}",
            "schedule_kind": "update",
        }

    current_week = _iso_week_key(datetime.combine(today, datetime.min.time()))
    if _published_week_key(month_entry) == current_week:
        return {
            "should_run": False,
            "reason": "already-published-this-week",
            "month_key": month_key,
            "slot": f"week-{week_index}",
            "schedule_kind": "update",
        }

    if str(run_last.get("run_date", "")).strip() == today_iso and str(run_last.get("month_key", "")).strip() == month_key:
        return {
            "should_run": False,
            "reason": "already-attempted-today",
            "month_key": month_key,
            "slot": f"week-{week_index}",
            "schedule_kind": "update",
        }

    return {
        "should_run": True,
        "reason": "weekly-monday-refresh",
        "month_key": month_key,
        "slot": f"week-{week_index}",
        "schedule_kind": "update",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan startup schedule for monthly notice archive.")
    parser.add_argument("--publish-state-file", default=str(DEFAULT_PUBLISH_STATE))
    parser.add_argument("--run-state-file", default=str(DEFAULT_RUN_STATE))
    parser.add_argument("--today", default="", help="Override today date (YYYY-MM-DD).")
    parser.add_argument("--mark-run", action="store_true", help="Persist this schedule slot as attempted.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    publish_state_path = Path(args.publish_state_file)
    run_state_path = Path(args.run_state_file)
    today = _parse_day(args.today)

    publish_state = _load_json(publish_state_path, {"months": {}, "updated_at": ""})
    if not isinstance(publish_state, dict):
        publish_state = {"months": {}, "updated_at": ""}
    run_state = _load_json(run_state_path, {"last_attempt": {}, "updated_at": ""})
    if not isinstance(run_state, dict):
        run_state = {"last_attempt": {}, "updated_at": ""}

    plan = _describe_schedule(today=today, publish_state=publish_state, run_state=run_state)
    month_key = str(plan.get("month_key", "")).strip()
    slot = str(plan.get("slot", "")).strip()
    schedule_kind = str(plan.get("schedule_kind", "")).strip()
    reason = str(plan.get("reason", "")).strip()

    if not plan.get("should_run"):
        print(f"[skip] {month_key} {schedule_kind} slot={slot} reason={reason}")
        return SKIP_EXIT_CODE

    if args.mark_run:
        run_state["last_attempt"] = {
            "month_key": month_key,
            "run_date": today.isoformat(),
            "slot": slot,
            "schedule_kind": schedule_kind,
            "marked_at": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
        }
        run_state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _save_json(run_state_path, run_state)

    print(f"[run] {month_key} {schedule_kind} slot={slot} reason={reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
