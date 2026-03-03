from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
AUTODRIVE_DIR = LOGS / "calculator_autodrive"
STATE_PATH = LOGS / "calculator_autodrive_state.json"
LATEST_PATH = LOGS / "calculator_autodrive_latest.json"
BACKLOG_PATH = LOGS / "calculator_autodrive_backlog.md"
JSONL_PATH = LOGS / "calculator_autodrive_cycles.jsonl"
TRAFFIC_GUARD_PATH = LOGS / "calculator_autodrive_traffic_guard.json"
AUTODRIVE_PID_PATH = LOGS / "calculator_autodrive.pid"

YANGDO_KR_URL = "https://seoulmna.kr/yangdo-ai-customer/"
ACQ_KR_URL = "https://seoulmna.kr/ai-license-acquisition-calculator/"
CONTEXT_DEFAULT_PATH = ROOT / "docs" / "calculator_autopilot_context.json"
SKILLS_DEFAULT_PATH = ROOT / "docs" / "skills_context_booster.md"
KR_LOCK_PATH = LOGS / "kr_only_mode.lock"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def next_9am() -> datetime:
    now = datetime.now()
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target + timedelta(days=1)
    return target


def parse_end_at(raw: str) -> datetime:
    src = str(raw or "").strip()
    if not src:
        return next_9am()
    if len(src) == 5 and src[2] == ":":
        hh = int(src[:2])
        mm = int(src[3:])
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now >= target:
            target = target + timedelta(days=1)
        return target
    try:
        parsed = datetime.fromisoformat(src)
        if parsed <= datetime.now():
            parsed = parsed + timedelta(days=1)
        return parsed
    except ValueError:
        return next_9am()


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}


def _date_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_traffic_guard() -> Dict[str, Any]:
    payload = load_json(TRAFFIC_GUARD_PATH)
    day = _date_key()
    if str(payload.get("date", "")) != day:
        payload = {
            "date": day,
            "precheck_count": 0,
            "blocked_precheck_count": 0,
            "last_update_at": now_iso(),
        }
        save_json(TRAFFIC_GUARD_PATH, payload)
    return payload


def _reserve_precheck_budget(max_prechecks_per_day: int, cost: int) -> Dict[str, Any]:
    payload = _load_traffic_guard()
    limit = max(2, int(max_prechecks_per_day))
    cost = max(1, int(cost))
    used = max(0, int(payload.get("precheck_count", 0)))
    allowed = (used + cost) <= limit
    if allowed:
        used += cost
        payload["precheck_count"] = used
        payload["last_update_at"] = now_iso()
    else:
        payload["budget_exhausted_at"] = now_iso()
        payload["last_update_at"] = now_iso()
    save_json(TRAFFIC_GUARD_PATH, payload)
    return {
        "ok": bool(allowed),
        "date": str(payload.get("date", _date_key())),
        "used": int(payload.get("precheck_count", 0)),
        "limit": limit,
        "remaining": max(0, limit - int(payload.get("precheck_count", 0))),
    }


def _note_blocked_precheck() -> None:
    payload = _load_traffic_guard()
    payload["blocked_precheck_count"] = max(0, int(payload.get("blocked_precheck_count", 0))) + 1
    payload["last_blocked_at"] = now_iso()
    payload["last_update_at"] = now_iso()
    save_json(TRAFFIC_GUARD_PATH, payload)


def _cleanup_artifacts(keep_cycles: int, keep_days: int) -> Dict[str, Any]:
    keep_cycles = max(20, int(keep_cycles))
    keep_days = max(1, int(keep_days))
    removed_dirs = 0
    removed_files = 0
    errors = 0
    cutoff = datetime.now() - timedelta(days=keep_days)

    # Trim cycle folders by count + age.
    cycle_dirs = [d for d in AUTODRIVE_DIR.glob("cycle_*") if d.is_dir()]
    cycle_dirs = sorted(cycle_dirs, key=lambda p: p.stat().st_mtime, reverse=True)
    protected = set(cycle_dirs[:keep_cycles])
    for d in cycle_dirs:
        if d in protected:
            continue
        try:
            if datetime.fromtimestamp(d.stat().st_mtime) <= cutoff:
                shutil.rmtree(d, ignore_errors=False)
                removed_dirs += 1
        except Exception:  # noqa: BLE001
            errors += 1

    # Trim stdout/stderr logs older than keep_days.
    for pat in ("calculator_autodrive_stdout_*.log", "calculator_autodrive_stderr_*.log"):
        for fp in LOGS.glob(pat):
            try:
                if datetime.fromtimestamp(fp.stat().st_mtime) <= cutoff:
                    fp.unlink(missing_ok=True)
                    removed_files += 1
            except Exception:  # noqa: BLE001
                errors += 1

    # Remove stale pid file if no active process.
    try:
        if AUTODRIVE_PID_PATH.exists():
            state = load_json(STATE_PATH)
            if str(state.get("status", "")).lower() != "running":
                AUTODRIVE_PID_PATH.unlink(missing_ok=True)
                removed_files += 1
    except Exception:  # noqa: BLE001
        errors += 1

    return {
        "removed_cycle_dirs": removed_dirs,
        "removed_files": removed_files,
        "errors": errors,
        "keep_cycles": keep_cycles,
        "keep_days": keep_days,
    }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def resolve_path(raw: str, default_path: Path) -> Path:
    src = str(raw or "").strip()
    if not src:
        return default_path
    p = Path(src)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p


def load_context(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return {}
    if isinstance(data, dict):
        return data
    return {}


def extract_recommended_skills(skills_doc: Path) -> List[str]:
    if not skills_doc.exists():
        return []
    out: List[str] = []
    try:
        lines = skills_doc.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:  # noqa: BLE001
        return out
    for line in lines:
        m = re.search(r"`([a-z0-9][a-z0-9-]+)`", str(line))
        if not m:
            continue
        name = str(m.group(1)).strip()
        if name and name not in out:
            out.append(name)
        if len(out) >= 12:
            break
    return out


def ensure_kr_only_lock(reason: str) -> None:
    KR_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": True,
        "reason": str(reason or "calculator_autodrive"),
        "locked_at": now_iso(),
    }
    KR_LOCK_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_python_cmd() -> List[str]:
    if sys.platform.startswith("win"):
        if shutil.which("py"):
            return ["py", "-3"]
        if shutil.which("python"):
            return ["python"]
    return [sys.executable]


def run_cmd(cmd: List[str], timeout_sec: int) -> Dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(60, int(timeout_sec)),
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": int(proc.returncode),
            "duration_sec": round(time.time() - started, 2),
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": 124,
            "duration_sec": round(time.time() - started, 2),
            "stdout_tail": ((exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else ""),
            "stderr_tail": ((exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else ""),
            "cmd": cmd,
            "error": "timeout",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "returncode": 1,
            "duration_sec": round(time.time() - started, 2),
            "stdout_tail": "",
            "stderr_tail": "",
            "cmd": cmd,
            "error": str(exc),
        }


def precheck_calculator_pages(urls: List[str], timeout_sec: int = 20) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    blocked = 0
    for url in urls:
        row: Dict[str, Any] = {"url": str(url), "ok": False, "status_code": None, "length": 0, "blocked_reason": ""}
        try:
            res = requests.get(
                str(url),
                timeout=max(5, int(timeout_sec)),
                headers={"User-Agent": "Mozilla/5.0"},
                allow_redirects=True,
            )
            text = str(res.text or "")
            low = text.lower()
            is_warn = ("warn.css" in low and "cafe24" in low) or ("noindex,nofollow" in low and len(text) < 5000)
            is_short = len(text) < 7000
            row.update(
                {
                    "status_code": int(res.status_code),
                    "length": len(text),
                    "final_url": str(res.url or ""),
                    "ok": bool(200 <= int(res.status_code) < 400 and (not is_warn) and (not is_short)),
                }
            )
            if is_warn:
                row["blocked_reason"] = "cafe24_warn_page_detected"
            elif is_short:
                row["blocked_reason"] = "short_html_response"
        except Exception as exc:  # noqa: BLE001
            row.update({"ok": False, "blocked_reason": f"request_error:{exc}", "error": str(exc)})
        if not row.get("ok"):
            blocked += 1
        rows.append(row)
    return {"ok": blocked == 0, "blocked_count": blocked, "checks": rows}


def build_improvement_notes(cycle: Dict[str, Any]) -> List[str]:
    notes: List[str] = []

    precheck = dict(cycle.get("precheck") or {})
    if not bool(precheck.get("ok", True)):
        notes.append(
            "precheck_failed: KR calculator pages appear unavailable "
            + f"(blocked={precheck.get('blocked_count', 0)})"
        )

    if not bool(cycle.get("context_guard_ok", True)):
        notes.append("context_guard_failed: context deployment guardrail mismatch")

    if not bool(cycle.get("co_guard_ok", True)):
        notes.append("co_guard_failed: heal report did not confirm co.skipped=true")

    if not bool(cycle.get("verify_ok")):
        notes.append("런타임 검증 실패: KR 배포/계산식 점검 필요")

    if not bool(cycle.get("step_behavior", {}).get("ok")):
        notes.append("행동 파일럿 실패: 입력 폼/버튼/결과 렌더 흐름 점검 필요")

    if not bool(cycle.get("step_stress", {}).get("ok")):
        notes.append("구조화 스트레스 실패: 경계값/복수업종/단위 입력 방어 보강 필요")

    behavior_anom = cycle.get("behavior_anomaly_counter") or {}
    if behavior_anom:
        top = sorted(behavior_anom.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:5]
        notes.append("행동 이상치 상위: " + ", ".join(f"{k}({v})" for k, v in top))

    stress_y = cycle.get("stress_yangdo_anomaly_counter") or {}
    stress_a = cycle.get("stress_acq_anomaly_counter") or {}
    if stress_y or stress_a:
        notes.append(
            "스트레스 이상치: "
            + f"양도양수={json.dumps(stress_y, ensure_ascii=False)}, "
            + f"신규등록={json.dumps(stress_a, ensure_ascii=False)}"
        )

    if not notes:
        notes.append("특이 이슈 없음: 현재 정책 유지 + 데이터/법령 변경분 점검 권장")
    return notes


def append_backlog(cycle: Dict[str, Any], notes: List[str]) -> None:
    BACKLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKLOG_PATH.exists():
        BACKLOG_PATH.write_text("# Calculator Autodrive Backlog\n\n", encoding="utf-8")

    lines = [
        f"## Cycle {cycle.get('cycle_index')} - {cycle.get('ended_at')}",
        f"- verify_ok: `{cycle.get('verify_ok')}`",
        f"- behavior_ok_rate: `{cycle.get('behavior_ok_rate')}`",
        f"- behavior_fail_events: `{cycle.get('behavior_fail_events')}`",
        f"- stress_yangdo_anomaly_counter: `{cycle.get('stress_yangdo_anomaly_counter')}`",
        f"- stress_acq_anomaly_counter: `{cycle.get('stress_acq_anomaly_counter')}`",
    ]
    for note in notes:
        lines.append(f"- note: {note}")
    lines.append("")

    with BACKLOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Autodrive loop for SeoulMNA calculators (KR-only, verify/heal/report)."
    )
    parser.add_argument("--end-at", default="", help="HH:MM or ISO datetime; default next 09:00 local")
    parser.add_argument("--pilot-minutes", type=int, default=20)
    parser.add_argument("--pilot-sleep-sec", type=float, default=1.5)
    parser.add_argument("--stress-yangdo-iterations", type=int, default=120)
    parser.add_argument("--stress-acq-iterations", type=int, default=120)
    parser.add_argument("--cycle-cooldown-sec", type=int, default=20)
    parser.add_argument("--blocked-backoff-sec", type=int, default=1800)
    parser.add_argument("--max-prechecks-per-day", type=int, default=120)
    parser.add_argument("--cleanup-keep-cycles", type=int, default=150)
    parser.add_argument("--cleanup-keep-days", type=int, default=7)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means unlimited until end-at")
    parser.add_argument("--max-train-rows", type=int, default=260)
    parser.add_argument("--context-file", default=str(CONTEXT_DEFAULT_PATH))
    parser.add_argument("--skills-doc", default=str(SKILLS_DEFAULT_PATH))
    parser.add_argument("--ensure-kr-lock", action="store_true", default=True)
    parser.add_argument("--no-ensure-kr-lock", dest="ensure_kr_lock", action="store_false")
    args = parser.parse_args()

    context_path = resolve_path(str(args.context_file), CONTEXT_DEFAULT_PATH)
    skills_doc_path = resolve_path(str(args.skills_doc), SKILLS_DEFAULT_PATH)
    context = load_context(context_path)
    guard = dict(context.get("deployment_guardrail") or {})
    context_mode = str(guard.get("mode", "")).strip().lower()
    context_co_default = guard.get("co_publish_default", None)
    context_guard_ok = (not context_mode or context_mode == "kr_only") and (
        (context_co_default is None) or (bool(context_co_default) is False)
    )
    skill_hints = extract_recommended_skills(skills_doc_path)

    if bool(args.ensure_kr_lock):
        ensure_kr_only_lock("run_calculator_autodrive")

    end_at = parse_end_at(str(args.end_at))
    started_at = now_iso()
    cycle_idx = 0

    LOGS.mkdir(parents=True, exist_ok=True)
    AUTODRIVE_DIR.mkdir(parents=True, exist_ok=True)

    state: Dict[str, Any] = {
        "status": "running",
        "started_at": started_at,
        "end_at": end_at.isoformat(timespec="seconds"),
        "pid": 0,
        "last_cycle_index": 0,
        "message": "autodrive started",
        "context_file": str(context_path),
        "skills_doc": str(skills_doc_path),
        "context_guard_ok": bool(context_guard_ok),
        "recommended_skills": skill_hints,
        "kr_lock_path": str(KR_LOCK_PATH),
        "kr_lock_enabled": bool(args.ensure_kr_lock),
    }
    # Cross-platform pid set
    try:
        state["pid"] = os.getpid()
    except Exception:  # noqa: BLE001
        pass
    save_json(STATE_PATH, state)

    if not context_guard_ok:
        state.update(
            {
                "status": "ended",
                "ended_at": now_iso(),
                "message": "context deployment guardrail mismatch",
            }
        )
        save_json(STATE_PATH, state)
        save_json(
            LATEST_PATH,
            {
                "generated_at": now_iso(),
                "status": "ended",
                "ok": False,
                "context_guard_ok": False,
                "context_file": str(context_path),
                "skills_doc": str(skills_doc_path),
                "recommended_skills": skill_hints,
                "blocking_issues": ["context_guardrail_mismatch"],
                "state_path": str(STATE_PATH),
            },
        )
        print("[autodrive] blocked by context guardrail mismatch")
        print(f"[context] {context_path}")
        return 2

    py = build_python_cmd()
    blocked_streak = 0

    while datetime.now() < end_at:
        if int(args.max_cycles) > 0 and cycle_idx >= int(args.max_cycles):
            break

        cycle_idx += 1
        cycle_started = time.time()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cycle_dir = AUTODRIVE_DIR / f"cycle_{cycle_idx:03d}_{stamp}"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        behavior_report = cycle_dir / "behavior_report.json"
        behavior_events = cycle_dir / "behavior_events.jsonl"
        stress_report = cycle_dir / "stress_report.json"
        verify_report = cycle_dir / "verify_report.json"
        heal_report = cycle_dir / "heal_report.json"
        reverify_report = cycle_dir / "reverify_report.json"

        budget = _reserve_precheck_budget(int(args.max_prechecks_per_day), cost=2)
        if bool(budget.get("ok")):
            precheck = precheck_calculator_pages([YANGDO_KR_URL, ACQ_KR_URL], timeout_sec=20)
        else:
            precheck = {
                "ok": False,
                "blocked_count": 2,
                "blocked_reason": "daily_precheck_budget_exceeded",
                "traffic_budget": budget,
                "checks": [
                    {"url": YANGDO_KR_URL, "ok": False, "blocked_reason": "daily_precheck_budget_exceeded"},
                    {"url": ACQ_KR_URL, "ok": False, "blocked_reason": "daily_precheck_budget_exceeded"},
                ],
            }

        if bool(precheck.get("ok")):
            blocked_streak = 0
            step_behavior = run_cmd(
                py
                + [
                    "scripts/run_calculator_behavior_pilot.py",
                    "--yangdo-url",
                    YANGDO_KR_URL,
                    "--acq-url",
                    ACQ_KR_URL,
                    "--duration-minutes",
                    str(max(1, int(args.pilot_minutes))),
                    "--sleep-sec",
                    str(max(0.1, float(args.pilot_sleep_sec))),
                    "--report",
                    str(behavior_report),
                    "--events",
                    str(behavior_events),
                ],
                timeout_sec=max(600, int(args.pilot_minutes) * 60 + 300),
            )

            step_stress = run_cmd(
                py
                + [
                    "scripts/run_calculator_structured_stress.py",
                    "--yangdo-url",
                    YANGDO_KR_URL,
                    "--acq-url",
                    ACQ_KR_URL,
                    "--yangdo-iterations",
                    str(max(20, int(args.stress_yangdo_iterations))),
                    "--acq-iterations",
                    str(max(20, int(args.stress_acq_iterations))),
                    "--report",
                    str(stress_report),
                ],
                timeout_sec=2400,
            )

            step_verify = run_cmd(
                py
                + [
                    "scripts/verify_calculator_runtime.py",
                    "--kr-only",
                    "--allow-no-browser",
                    "--report",
                    str(verify_report),
                ],
                timeout_sec=900,
            )
        else:
            _note_blocked_precheck()
            blocked_streak += 1
            blocked_summary = ", ".join(
                f"{str(x.get('url'))}::{str(x.get('blocked_reason') or 'blocked')}"
                for x in list(precheck.get("checks") or [])
            )
            step_behavior = {
                "ok": False,
                "returncode": 2,
                "duration_sec": 0.0,
                "stdout_tail": "",
                "stderr_tail": "",
                "skipped": True,
                "reason": f"precheck blocked: {blocked_summary}",
                "cmd": [],
            }
            step_stress = {
                "ok": False,
                "returncode": 2,
                "duration_sec": 0.0,
                "stdout_tail": "",
                "stderr_tail": "",
                "skipped": True,
                "reason": "precheck blocked",
                "cmd": [],
            }
            step_verify = {
                "ok": False,
                "returncode": 2,
                "duration_sec": 0.0,
                "stdout_tail": "",
                "stderr_tail": "",
                "skipped": True,
                "reason": "precheck blocked",
                "cmd": [],
            }

        verify_data = load_json(verify_report)
        verify_ok = bool(step_verify.get("ok") and verify_data.get("ok"))
        healed = False
        step_heal: Dict[str, Any] = {}
        step_reverify: Dict[str, Any] = {}
        co_guard_ok = True

        if (not verify_ok) and bool(precheck.get("ok")):
            step_heal = run_cmd(
                py
                + [
                    "scripts/deploy_yangdo_kr_banner_bridge.py",
                    "--skip-co-publish",
                    "--max-train-rows",
                    str(max(100, int(args.max_train_rows))),
                    "--report",
                    str(heal_report),
                ],
                timeout_sec=1500,
            )
            step_reverify = run_cmd(
                py
                + [
                    "scripts/verify_calculator_runtime.py",
                    "--kr-only",
                    "--allow-no-browser",
                    "--report",
                    str(reverify_report),
                ],
                timeout_sec=900,
            )
            reverify_data = load_json(reverify_report)
            verify_ok = bool(step_reverify.get("ok") and reverify_data.get("ok"))
            heal_data = load_json(heal_report)
            co_guard_ok = bool(((heal_data.get("co") or {}).get("skipped")) is True)
            verify_ok = bool(verify_ok and co_guard_ok)
            healed = verify_ok
        elif not bool(precheck.get("ok")):
            co_guard_ok = True

        behavior_data = load_json(behavior_report)
        stress_data = load_json(stress_report)

        cycle: Dict[str, Any] = {
            "cycle_index": cycle_idx,
            "started_at": datetime.fromtimestamp(cycle_started).isoformat(timespec="seconds"),
            "ended_at": now_iso(),
            "duration_sec": round(time.time() - cycle_started, 2),
            "verify_ok": verify_ok,
            "healed": healed,
            "context_guard_ok": bool(context_guard_ok),
            "co_guard_ok": bool(co_guard_ok),
            "precheck": precheck,
            "traffic_budget": budget,
            "blocked_streak": blocked_streak,
            "behavior_ok_rate": behavior_data.get("ok_rate"),
            "behavior_fail_events": behavior_data.get("fail_events"),
            "behavior_anomaly_counter": behavior_data.get("anomaly_counter", {}),
            "stress_yangdo_anomaly_counter": (stress_data.get("yangdo") or {}).get("anomaly_counter", {}),
            "stress_acq_anomaly_counter": (stress_data.get("acquisition") or {}).get("anomaly_counter", {}),
            "step_behavior": step_behavior,
            "step_stress": step_stress,
            "step_verify": step_verify,
            "step_heal": step_heal,
            "step_reverify": step_reverify,
            "cycle_dir": str(cycle_dir),
        }

        notes = build_improvement_notes(cycle)
        cycle["improvement_notes"] = notes
        if cycle_idx == 1 or cycle_idx % 10 == 0:
            cycle["cleanup"] = _cleanup_artifacts(
                keep_cycles=int(args.cleanup_keep_cycles),
                keep_days=int(args.cleanup_keep_days),
            )
        append_backlog(cycle, notes)

        with JSONL_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(cycle, ensure_ascii=False) + "\n")

        latest = {
            "generated_at": now_iso(),
            "status": "running",
            "ok": bool(verify_ok and context_guard_ok and co_guard_ok),
            "started_at": started_at,
            "end_at": end_at.isoformat(timespec="seconds"),
            "cycles_completed": cycle_idx,
            "context_file": str(context_path),
            "skills_doc": str(skills_doc_path),
            "recommended_skills": skill_hints,
            "context_guard_ok": bool(context_guard_ok),
            "last_cycle": cycle,
            "state_path": str(STATE_PATH),
            "backlog_path": str(BACKLOG_PATH),
            "cycles_jsonl_path": str(JSONL_PATH),
        }
        save_json(LATEST_PATH, latest)

        state.update(
            {
                "status": "running",
                "last_cycle_index": cycle_idx,
                "last_cycle_ended_at": cycle.get("ended_at"),
                "last_verify_ok": verify_ok,
                "message": "healthy" if verify_ok else "degraded",
            }
        )
        save_json(STATE_PATH, state)

        if datetime.now() >= end_at:
            break
        base_cooldown = max(5, int(args.cycle_cooldown_sec))
        if bool(precheck.get("ok")):
            sleep_sec = base_cooldown
        else:
            backoff = max(base_cooldown, int(args.blocked_backoff_sec))
            sleep_sec = min(3600, backoff * max(1, blocked_streak))
        time.sleep(max(5, int(sleep_sec)))

    state.update(
        {
            "status": "ended",
            "ended_at": now_iso(),
            "last_cycle_index": cycle_idx,
            "message": "autodrive completed by schedule",
        }
    )
    save_json(STATE_PATH, state)

    latest = load_json(LATEST_PATH)
    latest.update(
        {
            "generated_at": now_iso(),
            "status": "ended",
            "ok": bool(state.get("last_verify_ok", True) and context_guard_ok),
            "cycles_completed": cycle_idx,
            "context_file": str(context_path),
            "skills_doc": str(skills_doc_path),
            "recommended_skills": skill_hints,
            "context_guard_ok": bool(context_guard_ok),
            "state_path": str(STATE_PATH),
            "backlog_path": str(BACKLOG_PATH),
            "cycles_jsonl_path": str(JSONL_PATH),
        }
    )
    save_json(LATEST_PATH, latest)
    _cleanup_artifacts(
        keep_cycles=int(args.cleanup_keep_cycles),
        keep_days=int(args.cleanup_keep_days),
    )

    print(f"[autodrive] ended; cycles={cycle_idx}")
    print(f"[state] {STATE_PATH}")
    print(f"[latest] {LATEST_PATH}")
    print(f"[backlog] {BACKLOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
