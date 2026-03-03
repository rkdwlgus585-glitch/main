import argparse
import datetime as dt
import json
import pathlib
import shutil


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _safe_read(path: pathlib.Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_dt(value: str, fallback: dt.datetime) -> dt.datetime:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    try:
        return dt.datetime.fromisoformat(raw)
    except Exception:
        return fallback


def _issue_key(item: dict) -> str:
    return f"{item.get('automation','')}:{item.get('check_id','')}"


def _extract_issues(report: dict) -> dict:
    required = []
    optional = []
    for row in report.get("results", []) or []:
        automation = str(row.get("automation", ""))
        contract_file = str(row.get("contract_file", ""))
        for check in row.get("checks", []) or []:
            if check.get("ok"):
                continue
            issue = {
                "automation": automation,
                "contract_file": contract_file,
                "check_id": str(check.get("id", "")),
                "check_type": str(check.get("type", "")),
                "required": bool(check.get("required", True)),
            }
            if issue["required"]:
                required.append(issue)
            else:
                optional.append(issue)
    return {"required": required, "optional": optional}


def _load_reports(log_dir: pathlib.Path, window_days: int, include_partial: bool) -> list[dict]:
    cutoff = dt.datetime.now() - dt.timedelta(days=max(1, int(window_days)))
    rows = []
    for path in sorted(log_dir.glob("quality_daily_*.json")):
        if path.name == "quality_daily_latest.json":
            continue
        try:
            payload = json.loads(_safe_read(path))
        except json.JSONDecodeError:
            continue
        selected_contracts = payload.get("selected_contracts", [])
        if (not include_partial) and isinstance(selected_contracts, list) and len(selected_contracts) > 0:
            continue
        fallback = dt.datetime.fromtimestamp(path.stat().st_mtime)
        started = _parse_dt(payload.get("started_at", ""), fallback)
        if started < cutoff:
            continue
        rows.append(
            {
                "path": path,
                "name": path.name,
                "started_at": started,
                "ok": bool(payload.get("ok", False)),
                "payload": payload,
            }
        )
    rows.sort(key=lambda x: x["started_at"])
    return rows


def _build_trend(reports: list[dict], window_days: int) -> dict:
    now = dt.datetime.now().isoformat()
    if not reports:
        return {
            "generated_at": now,
            "window_days": int(window_days),
            "report_count": 0,
            "latest_report": "",
            "new_failures": [],
            "repeated_warnings": [],
            "summary": {
                "new_failure_count": 0,
                "repeated_warning_count": 0,
            },
        }

    latest = reports[-1]
    previous = reports[:-1]
    latest_issues = _extract_issues(latest["payload"])

    history_required_keys = set()
    history_optional_counts = {}
    history_optional_samples = {}
    for row in previous:
        issues = _extract_issues(row["payload"])
        for issue in issues["required"]:
            history_required_keys.add(_issue_key(issue))
        for issue in issues["optional"]:
            key = _issue_key(issue)
            history_optional_counts[key] = history_optional_counts.get(key, 0) + 1
            history_optional_samples.setdefault(key, issue)

    new_failures = []
    for issue in latest_issues["required"]:
        key = _issue_key(issue)
        if key in history_required_keys:
            continue
        new_failures.append(issue)

    repeated_warnings = []
    for issue in latest_issues["optional"]:
        key = _issue_key(issue)
        prev_count = int(history_optional_counts.get(key, 0))
        if prev_count <= 0:
            continue
        repeated_warnings.append(
            {
                **issue,
                "previous_occurrences": prev_count,
                "window_occurrences": prev_count + 1,
            }
        )

    return {
        "generated_at": now,
        "window_days": int(window_days),
        "report_count": len(reports),
        "latest_report": latest["name"],
        "latest_started_at": latest["started_at"].isoformat(),
        "new_failures": new_failures,
        "repeated_warnings": repeated_warnings,
        "summary": {
            "new_failure_count": len(new_failures),
            "repeated_warning_count": len(repeated_warnings),
        },
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build 7-day quality trend report (new failures / repeated warnings).")
    p.add_argument("--logs-dir", default="logs", help="Logs directory path (default: logs)")
    p.add_argument("--window-days", type=int, default=7, help="Comparison window days (default: 7)")
    p.add_argument("--include-partial", action="store_true", help="Include partial reports from --contracts runs.")
    p.add_argument("--quiet", action="store_true", help="Print summary only")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    log_dir = pathlib.Path(args.logs_dir)
    if not log_dir.is_absolute():
        log_dir = ROOT / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    reports = _load_reports(
        log_dir=log_dir,
        window_days=int(args.window_days),
        include_partial=bool(args.include_partial),
    )
    trend = _build_trend(reports, window_days=int(args.window_days))

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = log_dir / f"quality_trend_{stamp}.json"
    out_path.write_text(json.dumps(trend, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path = log_dir / "quality_trend_latest.json"
    shutil.copyfile(out_path, latest_path)

    try:
        out_display = out_path.relative_to(ROOT).as_posix()
    except ValueError:
        out_display = str(out_path)
    print(f"[quality-trend] report: {out_display}")
    print(
        "[quality-trend] summary: "
        f"reports={trend.get('report_count', 0)} "
        f"new_failures={trend.get('summary', {}).get('new_failure_count', 0)} "
        f"repeated_warnings={trend.get('summary', {}).get('repeated_warning_count', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
