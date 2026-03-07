import argparse
import importlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
YEAR_KEYS = {"mp_2020[]", "mp_2021[]", "mp_2022[]", "mp_2023[]", "mp_2024[]", "mp_2025[]"}


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_latest_targets() -> str:
    audit_dir = ROOT / "logs" / "reconcile_audit"
    candidates = sorted(audit_dir.glob("affected_row_shift_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return ""
    return str(candidates[0])


def _build_targets_from_latest_reconcile() -> str:
    audit_dir = ROOT / "logs" / "reconcile_audit"
    reconcile_files = sorted(audit_dir.glob("reconcile_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for rec in reconcile_files:
        try:
            data = json.loads(rec.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = []
        for row in data.get("entries", []):
            wr_id = str(row.get("wr_id", "")).strip()
            uid = str(row.get("uid", "")).strip()
            keys = list(row.get("site_changed_keys", []) or [])
            if not wr_id.isdigit() or not uid.isdigit():
                continue
            if not any(key in YEAR_KEYS for key in keys):
                continue
            items.append(
                {
                    "wr_id": int(wr_id),
                    "uid": uid,
                    "result": row.get("result", ""),
                    "site_changed_keys": keys,
                    "message": row.get("message", ""),
                    "error": row.get("error", ""),
                }
            )
        if not items:
            continue
        out = audit_dir / f"affected_row_shift_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {"count": len(items), "items": items, "source_reconcile": str(rec)}
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out)
    return ""


def _load_targets(path: str, key_mode: str):
    src = Path(path)
    data = json.loads(src.read_text(encoding="utf-8"))
    items = data.get("items", [])

    targets = []
    for row in items:
        wr_id = str(row.get("wr_id", "")).strip()
        uid = str(row.get("uid", "")).strip()
        keys = list(row.get("site_changed_keys", []) or [])
        if not wr_id.isdigit() or not uid.isdigit():
            continue

        keep = False
        if key_mode == "all":
            keep = True
        elif key_mode == "mp":
            keep = any(str(key).startswith("mp_") for key in keys)
        else:
            keep = any(key in YEAR_KEYS for key in keys)
        if keep:
            targets.append({"wr_id": int(wr_id), "uid": uid, "keys": keys})
    return targets


def _build_source_marker(target_path: str) -> dict:
    src = Path(str(target_path)).resolve()
    data = _load_json(src, {})
    source_path = src
    source_reconcile = str(data.get("source_reconcile", "")).strip()
    if source_reconcile:
        candidate = Path(source_reconcile).resolve()
        if candidate.exists():
            source_path = candidate
    source_stat = source_path.stat()
    target_stat = src.stat()
    return {
        "target_path": str(src),
        "target_mtime_ns": int(target_stat.st_mtime_ns),
        "target_size": int(target_stat.st_size),
        "source_path": str(source_path),
        "source_mtime_ns": int(source_stat.st_mtime_ns),
        "source_size": int(source_stat.st_size),
        "source_key": f"{source_path}|{int(source_stat.st_mtime_ns)}|{int(source_stat.st_size)}",
    }


def _is_same_completed_source(state: dict, marker: dict) -> bool:
    if not bool(state.get("complete")):
        return False
    prev_key = str(state.get("source_key", "")).strip()
    cur_key = str(marker.get("source_key", "")).strip()
    return bool(prev_key) and prev_key == cur_key


def _read_daily_limit_state(allmod):
    today = datetime.now().strftime("%Y-%m-%d")
    req_cap = int(getattr(allmod, "SEOUL_DAILY_REQUEST_CAP", 0) or 0)
    write_cap = int(getattr(allmod, "SEOUL_DAILY_WRITE_CAP", 0) or 0)
    path = Path(str(getattr(allmod, "SEOUL_DAILY_LIMIT_STATE_FILE", "") or "")).resolve()

    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if str(data.get("date", "")) != today:
        data = {"date": today, "requests": 0, "writes": 0}

    return {
        "date": today,
        "requests": int(data.get("requests", 0) or 0),
        "writes": int(data.get("writes", 0) or 0),
        "request_cap": req_cap,
        "write_cap": write_cap,
        "state_file": str(path),
    }


def _build_traffic_plan(target_count, limit_state, dry_run, request_buffer, write_buffer):
    req_used = int(limit_state.get("requests", 0) or 0)
    write_used = int(limit_state.get("writes", 0) or 0)
    req_cap = int(limit_state.get("request_cap", 0) or 0)
    write_cap = int(limit_state.get("write_cap", 0) or 0)

    req_remaining = max(0, req_cap - req_used)
    write_remaining = max(0, write_cap - write_used)

    fixed_login_req = 3
    per_target_req = 1 if dry_run else 2
    per_target_write = 0 if dry_run else 1

    usable_req = max(0, req_remaining - max(0, int(request_buffer)) - fixed_login_req)
    req_limit = usable_req // max(1, per_target_req)

    if per_target_write <= 0:
        write_limit = target_count
    else:
        usable_write = max(0, write_remaining - max(0, int(write_buffer)))
        write_limit = usable_write // per_target_write

    safe_limit = max(0, min(int(target_count), int(req_limit), int(write_limit)))
    return {
        "targets": int(target_count),
        "mode": "dry-run" if dry_run else "apply",
        "request_buffer": max(0, int(request_buffer)),
        "write_buffer": max(0, int(write_buffer)),
        "fixed_login_req": fixed_login_req,
        "per_target_req": per_target_req,
        "per_target_write": per_target_write,
        "req_remaining": req_remaining,
        "write_remaining": write_remaining,
        "req_limit": int(req_limit),
        "write_limit": int(write_limit),
        "safe_limit": int(safe_limit),
    }


def _print_traffic_plan(limit_state, plan):
    print("Preflight traffic plan:")
    print(
        "  - daily state: "
        f"req {limit_state['requests']}/{limit_state['request_cap']} "
        f"write {limit_state['writes']}/{limit_state['write_cap']}"
    )
    print(
        "  - estimate: "
        f"fixed_login_req={plan['fixed_login_req']} "
        f"per_target_req={plan['per_target_req']} "
        f"per_target_write={plan['per_target_write']}"
    )
    print(
        "  - headroom after buffer: "
        f"req_limit={plan['req_limit']} write_limit={plan['write_limit']}"
    )
    print(f"  - safe target limit for this run: {plan['safe_limit']} / {plan['targets']}")


def _write_state(path: Path, marker: dict, *, complete: bool, target_count: int, processed_count: int, updated: int, skipped_same: int, failed: int, dry_run: bool, reason: str = "") -> None:
    _save_json(
        path,
        {
            **marker,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "complete": bool(complete),
            "target_count": int(target_count),
            "processed_count": int(processed_count),
            "updated": int(updated),
            "skipped_same": int(skipped_same),
            "failed": int(failed),
            "dry_run": bool(dry_run),
            "reason": str(reason or "").strip(),
        },
    )


def main():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    parser = argparse.ArgumentParser(description="Republish selected entries from reconcile audit targets.")
    parser.add_argument("--targets", default="", help="Path to target json (default: latest affected_row_shift_*.json).")
    parser.add_argument("--key-mode", choices=["year", "mp", "all"], default="year")
    parser.add_argument("--limit", type=int, default=0, help="Max items to process (0=all).")
    parser.add_argument("--delay-sec", type=float, default=1.5, help="Delay between updates.")
    parser.add_argument("--plan-only", action="store_true", help="Print the traffic plan without opening the site.")
    parser.add_argument("--request-buffer", type=int, default=80, help="Reserved request headroom.")
    parser.add_argument("--write-buffer", type=int, default=8, help="Reserved write headroom.")
    parser.add_argument("--state-file", default="logs/republish_from_audit_state.json", help="Path to run state json.")
    parser.add_argument("--skip-if-source-unchanged", action="store_true", help="Skip when the latest completed source matches the prior run.")
    parser.add_argument("--force", action="store_true", help="Ignore source-based skip state.")
    parser.add_argument("--yes", action="store_true", help="Proceed without interactive confirmation.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    allmod = importlib.import_module("all")
    target_path = str(args.targets or "").strip() or _find_latest_targets()
    if not target_path:
        target_path = _build_targets_from_latest_reconcile()
    if not target_path:
        print("No targets file found. Skip this run.")
        return

    print(f"Targets file: {target_path}")
    state_path = Path(str(args.state_file)).resolve()
    source_marker = _build_source_marker(target_path)
    prior_state = _load_json(state_path, {})
    if bool(args.skip_if_source_unchanged) and (not bool(args.force)) and _is_same_completed_source(prior_state, source_marker):
        print("Skip this run: latest reconcile source already completed without diff/write errors.")
        return

    targets = _load_targets(target_path, args.key_mode)
    if args.limit > 0:
        targets = targets[: args.limit]

    if not targets:
        print("No targets to process.")
        _write_state(
            state_path,
            source_marker,
            complete=True,
            target_count=0,
            processed_count=0,
            updated=0,
            skipped_same=0,
            failed=0,
            dry_run=bool(args.dry_run),
            reason="no_targets",
        )
        return

    original_target_count = len(targets)
    limit_state = _read_daily_limit_state(allmod)
    plan = _build_traffic_plan(
        target_count=len(targets),
        limit_state=limit_state,
        dry_run=bool(args.dry_run),
        request_buffer=args.request_buffer,
        write_buffer=args.write_buffer,
    )
    _print_traffic_plan(limit_state, plan)

    if args.plan_only:
        return

    safe_limit = int(plan.get("safe_limit", 0) or 0)
    if safe_limit <= 0:
        print("Safe limit is 0. Skip this run to avoid traffic overrun.")
        _write_state(
            state_path,
            source_marker,
            complete=False,
            target_count=original_target_count,
            processed_count=0,
            updated=0,
            skipped_same=0,
            failed=0,
            dry_run=bool(args.dry_run),
            reason="safe_limit_zero",
        )
        return
    if len(targets) > safe_limit:
        print(f"Trimming targets by plan: {len(targets)} -> {safe_limit}")
        targets = targets[:safe_limit]

    if not args.dry_run and not args.yes:
        if not (sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
            raise SystemExit("Non-interactive shell: re-run with --yes to continue.")
        ans = input(f"Proceed with apply for {len(targets)} targets? [y/N]: ").strip().lower()
        if ans not in {"y", "yes"}:
            print("Cancelled.")
            return

    admin_id = str(allmod.CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(allmod.CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        raise SystemExit("Missing ADMIN_ID/ADMIN_PW in config.")

    publisher = allmod.MnaBoardPublisher(allmod.SITE_URL, allmod.MNA_BOARD_SLUG, admin_id, admin_pw)
    publisher.login()
    limit_info = publisher.daily_limit_summary()
    print(
        f"Daily limit before run: req {limit_info['requests']}/{limit_info['request_cap']} "
        f"/ write {limit_info['writes']}/{limit_info['write_cap']}"
    )

    options = allmod.webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = allmod.webdriver.Chrome(
        service=allmod.Service(allmod.ChromeDriverManager().install()),
        options=options,
    )

    updated = 0
    skipped_same = 0
    failed = 0
    processed_count = 0
    try:
        for idx, target in enumerate(targets, start=1):
            wr_id = int(target["wr_id"])
            uid = str(target["uid"])
            print(f"[{idx}/{len(targets)}] wr={wr_id} uid={uid}")
            current_limit = publisher.daily_limit_summary()
            req_stop = int(current_limit["request_cap"]) - max(1, int(args.request_buffer // 2))
            if int(current_limit["requests"]) >= req_stop:
                print("   - stop: request headroom exhausted by safety policy")
                break
            if not args.dry_run:
                write_stop = int(current_limit["write_cap"]) - max(0, int(args.write_buffer))
                if int(current_limit["writes"]) >= write_stop:
                    print("   - stop: write headroom exhausted by safety policy")
                    break
            try:
                item = allmod._extract_item_from_detail_link(driver, allmod._safe_nowmna_detail_link(uid))
                action_url, payload, form, form_html = publisher.get_edit_payload(wr_id)
                updates = allmod._build_sync_updates(item, form, form_html, payload)
                diff_keys = allmod._diff_payload_updates(payload, updates)
                if not diff_keys:
                    skipped_same += 1
                    print("   - skip: no diff")
                elif args.dry_run:
                    print(f"   - dry-run diff: {', '.join(diff_keys)}")
                else:
                    publisher.submit_edit_updates(action_url, payload, updates)
                    updated += 1
                    print(f"   - updated: {', '.join(diff_keys)}")
            except Exception as exc:
                failed += 1
                print(f"   - failed: {exc}")
            processed_count += 1

            if args.delay_sec > 0:
                time.sleep(max(0.0, float(args.delay_sec)))
    finally:
        allmod._safe_quit(driver)

    limit_after = publisher.daily_limit_summary()
    print(
        f"Done: updated={updated}, skipped_same={skipped_same}, failed={failed}, "
        f"req {limit_after['requests']}/{limit_after['request_cap']}, "
        f"write {limit_after['writes']}/{limit_after['write_cap']}"
    )
    _write_state(
        state_path,
        source_marker,
        complete=bool(processed_count == original_target_count and failed == 0 and len(targets) == original_target_count),
        target_count=original_target_count,
        processed_count=processed_count,
        updated=updated,
        skipped_same=skipped_same,
        failed=failed,
        dry_run=bool(args.dry_run),
        reason="completed",
    )


if __name__ == "__main__":
    main()
