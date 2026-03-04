import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _parse_dt(text: str) -> datetime | None:
    src = str(text or "").strip()
    if not src:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(src, fmt)
        except Exception:
            continue
    return None


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _read_history(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            s = str(raw or "").strip()
            if not s:
                continue
            try:
                row = json.loads(s)
                if isinstance(row, dict):
                    out.append(row)
            except Exception:
                continue
    return out


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _streak_stats(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    current_fail = 0
    max_fail = 0
    for row in rows:
        if bool(row.get("ok", False)):
            current_fail = 0
        else:
            current_fail += 1
            if current_fail > max_fail:
                max_fail = current_fail
    tail_fail = 0
    for row in reversed(rows):
        if bool(row.get("ok", False)):
            break
        tail_fail += 1
    return {"max_fail_streak": max_fail, "tail_fail_streak": tail_fail}


def _top_failed_checks(rows: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    counter: Dict[str, int] = {}
    for row in rows:
        for chk in list(row.get("checks") or []):
            name = str(chk.get("name", "")).strip()
            if not name:
                continue
            if not bool(chk.get("pass", False)):
                counter[name] = int(counter.get(name, 0)) + 1
    ranked = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    return [{"name": k, "count": v} for k, v in ranked[:top_n]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 7-day site CX health digest.")
    parser.add_argument("--history", default="logs/site_cx_health_history.jsonl")
    parser.add_argument("--rollup", default="logs/site_cx_health_rollup_latest.json")
    parser.add_argument("--latest-json", default="logs/site_cx_health_digest_latest.json")
    parser.add_argument("--latest-md", default="logs/site_cx_health_digest_latest.md")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    history_path = (ROOT / str(args.history)).resolve()
    rollup_path = (ROOT / str(args.rollup)).resolve()
    json_path = (ROOT / str(args.latest_json)).resolve()
    md_path = (ROOT / str(args.latest_md)).resolve()
    days = max(1, int(args.days))
    since = datetime.now() - timedelta(days=days)

    all_rows = _read_history(history_path)
    rows: List[Dict[str, Any]] = []
    for row in all_rows:
        ts = _parse_dt(str(row.get("generated_at", "")))
        if ts and ts >= since:
            rows.append(row)

    total = len(rows)
    ok_count = sum(1 for r in rows if bool(r.get("ok", False)))
    fail_count = max(0, total - ok_count)
    uptime_pct = round((ok_count / total) * 100.0, 2) if total > 0 else 0.0
    streaks = _streak_stats(rows)
    top_failed = _top_failed_checks(rows, top_n=6)
    latest_rollup = _read_json(rollup_path)

    payload: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window_days": days,
        "since": since.strftime("%Y-%m-%d %H:%M:%S"),
        "samples": total,
        "ok_samples": ok_count,
        "fail_samples": fail_count,
        "uptime_pct": uptime_pct,
        "max_fail_streak": streaks["max_fail_streak"],
        "tail_fail_streak": streaks["tail_fail_streak"],
        "latest_ok": bool(latest_rollup.get("ok", False)),
        "latest_required_fail_count": int(latest_rollup.get("required_fail_count", 0) or 0),
        "latest_optional_fail_count": int(latest_rollup.get("optional_fail_count", 0) or 0),
        "top_failed_checks": top_failed,
        "history_file": str(history_path),
        "rollup_file": str(rollup_path),
    }
    _write_json(json_path, payload)

    lines = [
        f"# Site CX Health Digest ({payload['generated_at']})",
        "",
        f"- window_days: {days}",
        f"- samples: {total}",
        f"- uptime_pct: {uptime_pct}%",
        f"- fail_samples: {fail_count}",
        f"- max_fail_streak: {streaks['max_fail_streak']}",
        f"- tail_fail_streak: {streaks['tail_fail_streak']}",
        f"- latest_ok: {payload['latest_ok']}",
        f"- latest_required_fail_count: {payload['latest_required_fail_count']}",
        f"- latest_optional_fail_count: {payload['latest_optional_fail_count']}",
        "",
        "## Top Failed Checks",
    ]
    if top_failed:
        for row in top_failed:
            lines.append(f"- {row['name']}: {row['count']}")
    else:
        lines.append("- (none)")

    _write_text(md_path, "\n".join(lines) + "\n")
    print(f"[saved] {json_path}")
    print(f"[saved] {md_path}")
    print(
        "[summary] "
        + f"samples={total} "
        + f"uptime_pct={uptime_pct} "
        + f"latest_ok={payload['latest_ok']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
