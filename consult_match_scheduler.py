import argparse
import atexit
import json
import os
import subprocess
import sys
import time
from datetime import datetime

from utils import load_config, setup_logger

CONFIG = load_config(
    {
        "MATCH_SCHEDULER_ENABLED": "true",
        "MATCH_SCHEDULE_TIME": "09:40",
        "MATCH_RUN_MISSED_ON_STARTUP": "true",
        "MATCH_SCRIPT": "match.py",
        "MATCH_SCHEDULER_STATE_FILE": "match_scheduler_state.json",
        "MATCH_SCHEDULER_LOCK_FILE": "match_scheduler.lock",
    }
)

logger = setup_logger(name="match_scheduler")

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _cfg_bool(key, default=False):
    val = str(CONFIG.get(key, default)).strip().lower()
    if val in {"1", "true", "yes", "on", "y"}:
        return True
    if val in {"0", "false", "no", "off", "n"}:
        return False
    return bool(default)


def _state_path():
    return str(CONFIG.get("MATCH_SCHEDULER_STATE_FILE", "match_scheduler_state.json")).strip() or "match_scheduler_state.json"


def _lock_path():
    return str(CONFIG.get("MATCH_SCHEDULER_LOCK_FILE", "match_scheduler.lock")).strip() or "match_scheduler.lock"


def _load_state():
    path = _state_path()
    if not os.path.exists(path):
        return {"last_run": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"last_run": {}}
        if "last_run" not in data or not isinstance(data["last_run"], dict):
            data["last_run"] = {}
        return data
    except Exception:
        return {"last_run": {}}


def _save_state(state):
    state = dict(state or {})
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _same_local_day(iso_ts):
    if not iso_ts:
        return False
    try:
        dt = datetime.fromisoformat(str(iso_ts))
    except Exception:
        return False
    return dt.date() == datetime.now().date()


def _parse_hhmm(value):
    raw = str(value or "").strip()
    hh, mm = raw.split(":", 1)
    hh_i = int(hh)
    mm_i = int(mm)
    if hh_i < 0 or hh_i > 23 or mm_i < 0 or mm_i > 59:
        raise ValueError(f"invalid HH:MM time: {raw}")
    return hh_i, mm_i


def _now_hhmm_int():
    now = datetime.now()
    return now.hour * 60 + now.minute


def _target_hhmm_int(hhmm):
    hh, mm = _parse_hhmm(hhmm)
    return hh * 60 + mm


_LOCK_ACQUIRED = False


def _acquire_lock():
    global _LOCK_ACQUIRED
    lock_file = _lock_path()
    pid = os.getpid()

    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_pid = int(old.get("pid", 0))
        except Exception:
            old_pid = 0

        if old_pid > 0:
            try:
                os.kill(old_pid, 0)
                raise RuntimeError(f"lock already held by pid={old_pid}")
            except OSError:
                pass

        try:
            os.remove(lock_file)
        except Exception:
            pass

    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": pid, "started_at": datetime.now().isoformat(timespec="seconds")}, f)

    _LOCK_ACQUIRED = True
    logger.info(f"lock acquired: {lock_file} (pid={pid})")


@atexit.register
def _release_lock():
    if not _LOCK_ACQUIRED:
        return
    lock_file = _lock_path()
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except Exception:
        pass


def run_match_once(reason="manual"):
    script = str(CONFIG.get("MATCH_SCRIPT", "match.py")).strip() or "match.py"
    cmd = [sys.executable, script]

    logger.info(f"match job started (reason={reason})")
    started_at = datetime.now().isoformat(timespec="seconds")
    rc = 1
    err = ""

    try:
        proc = subprocess.run(cmd, check=False)
        rc = int(proc.returncode)
    except Exception as e:
        err = str(e)

    success = (rc == 0 and not err)

    state = _load_state()
    state["last_run"] = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "started_at": started_at,
        "reason": reason,
        "success": success,
        "exit_code": rc,
        "error": err,
        "schedule_time": str(CONFIG.get("MATCH_SCHEDULE_TIME", "09:40")),
    }
    _save_state(state)

    if success:
        logger.info("match job success")
    else:
        logger.error(f"match job failed (exit={rc}, error={err})")

    return success


def run_startup_catchup_if_needed():
    if not _cfg_bool("MATCH_RUN_MISSED_ON_STARTUP", True):
        return

    schedule_time = str(CONFIG.get("MATCH_SCHEDULE_TIME", "09:40")).strip() or "09:40"
    now_min = _now_hhmm_int()
    target_min = _target_hhmm_int(schedule_time)

    state = _load_state()
    last = state.get("last_run", {})

    if _same_local_day(last.get("time")):
        logger.info("startup catch-up skipped: already ran today")
        return

    if now_min >= target_min:
        logger.info("startup catch-up triggered")
        run_match_once(reason="startup_catchup")
    else:
        logger.info("startup catch-up skipped: before schedule time")


def show_status():
    state = _load_state()
    last = state.get("last_run", {})

    print("match_scheduler_status")
    print("enabled=" + str(_cfg_bool("MATCH_SCHEDULER_ENABLED", True)).lower())
    print("schedule_time=" + (str(CONFIG.get("MATCH_SCHEDULE_TIME", "09:40")).strip() or "09:40"))
    print("script=" + (str(CONFIG.get("MATCH_SCRIPT", "match.py")).strip() or "match.py"))

    if not last:
        print("last_run=never")
        return

    print("last_run_time=" + str(last.get("time", "")))
    print("last_run_reason=" + str(last.get("reason", "")))
    print("last_run_success=" + str(last.get("success", "")))
    print("last_run_exit_code=" + str(last.get("exit_code", "")))
    print("last_run_error=" + str(last.get("error", "")))


def start_scheduler_loop():
    if not _cfg_bool("MATCH_SCHEDULER_ENABLED", True):
        logger.info("MATCH_SCHEDULER_ENABLED is false; scheduler stopped")
        return

    try:
        import schedule
    except ImportError:
        logger.error("schedule package missing; install with: pip install schedule")
        raise SystemExit(1)

    _acquire_lock()

    schedule_time = str(CONFIG.get("MATCH_SCHEDULE_TIME", "09:40")).strip() or "09:40"
    _parse_hhmm(schedule_time)

    run_startup_catchup_if_needed()

    schedule.clear("match_daily")
    schedule.every().day.at(schedule_time).do(run_match_once, reason="daily_schedule").tag("match_daily")
    logger.info(f"match daily schedule registered: {schedule_time}")

    while True:
        try:
            schedule.run_pending()
            time.sleep(20)
        except KeyboardInterrupt:
            logger.info("scheduler interrupted by user")
            break
        except Exception as e:
            logger.error(f"scheduler loop error: {e}")
            time.sleep(5)


def _build_parser():
    p = argparse.ArgumentParser(description="Daily scheduler for 상담관리<->매물 match sync")
    p.add_argument("--once", action="store_true", help="run match.py once and exit")
    p.add_argument("--status", action="store_true", help="show last run status")
    p.add_argument("--scheduler", action="store_true", help="start daily scheduler loop")
    return p


def main():
    args = _build_parser().parse_args()

    if args.status:
        show_status()
        return

    if args.once:
        ok = run_match_once(reason="manual_once")
        raise SystemExit(0 if ok else 1)

    if args.scheduler:
        start_scheduler_loop()
        return

    show_status()


if __name__ == "__main__":
    main()
