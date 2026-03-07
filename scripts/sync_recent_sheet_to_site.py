from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import all as allmod


def _open_sheet_values() -> list[list[str]]:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(allmod.JSON_FILE, scope)
    ws = gspread.authorize(creds).open(allmod.SHEET_NAME).sheet1
    return ws.get_all_values()


def _parse_uid_list(raw: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for token in re.split(r"[\s,]+", str(raw or "").strip()):
        uid = str(token or "").strip()
        if not uid or (not uid.isdigit()) or uid in seen:
            continue
        seen.add(uid)
        items.append(uid)
    return items


def _load_recent_targets(limit: int, uid_min: int, uid_max: int) -> list[dict[str, Any]]:
    values = _open_sheet_values()
    out: list[dict[str, Any]] = []
    for row_idx, row in reversed(list(enumerate(values[1:], start=2))):
        uid = allmod._extract_sheet_uid_from_row(row)
        if not uid or (not str(uid).isdigit()):
            continue
        uid_num = int(uid)
        if uid_min and uid_num < uid_min:
            continue
        if uid_max and uid_num > uid_max:
            continue
        out.append(
            {
                "row_idx": row_idx,
                "uid": uid,
                "sheet_no": allmod._row_text(row, 0),
                "sheet_status": allmod._normalize_sync_status_label(allmod._row_text(row, 1)),
                "license": allmod._row_text(row, 2),
                "sheet_price": allmod._row_text(row, 18),
                "sheet_claim_price": allmod._row_text(row, 33),
                "row": row,
            }
        )
        if limit > 0 and len(out) >= limit:
            break
    out.reverse()
    return out


def _load_targets_by_uid_list(uid_list: list[str]) -> list[dict[str, Any]]:
    uid_order = [uid for uid in uid_list if str(uid or "").strip()]
    wanted = set(uid_order)
    if not wanted:
        return []

    values = _open_sheet_values()
    found: dict[str, dict[str, Any]] = {}
    for row_idx, row in enumerate(values[1:], start=2):
        uid = allmod._extract_sheet_uid_from_row(row)
        if uid not in wanted:
            continue
        found[uid] = {
            "row_idx": row_idx,
            "uid": uid,
            "sheet_no": allmod._row_text(row, 0),
            "sheet_status": allmod._normalize_sync_status_label(allmod._row_text(row, 1)),
            "license": allmod._row_text(row, 2),
            "sheet_price": allmod._row_text(row, 18),
            "sheet_claim_price": allmod._row_text(row, 33),
            "row": row,
        }
    return [found[uid] for uid in uid_order if uid in found]


def _seed_site_wr_ids(targets: list[dict[str, Any]]) -> None:
    seeded = dict(allmod._seed_site_wr_map_from_upload_state() or {})
    for row in targets:
        sheet_wr_id = allmod._sheet_no_to_int(row.get("sheet_no", ""))
        if sheet_wr_id > 0:
            row["site_wr_id"] = int(sheet_wr_id)
            row["site_wr_source"] = "sheet_no"
            continue
        state_wr_id = int(seeded.get(str(row.get("uid", "")).strip(), 0) or 0)
        if state_wr_id > 0:
            row["site_wr_id"] = state_wr_id
            row["site_wr_source"] = "upload_state"
            continue
        row["site_wr_id"] = 0
        row["site_wr_source"] = ""


def _read_limit_state() -> dict[str, Any]:
    today = datetime.now().strftime("%Y-%m-%d")
    path = Path(str(getattr(allmod, "SEOUL_DAILY_LIMIT_STATE_FILE", "") or "")).resolve()
    payload: dict[str, Any] = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    if str(payload.get("date", "")) != today:
        payload = {"date": today, "requests": 0, "writes": 0}
    payload["state_file"] = str(path)
    payload["request_cap"] = int(getattr(allmod, "SEOUL_DAILY_REQUEST_CAP", 0) or 0)
    payload["write_cap"] = int(getattr(allmod, "SEOUL_DAILY_WRITE_CAP", 0) or 0)
    payload["request_buffer"] = int(getattr(allmod, "SEOUL_TRAFFIC_GUARD_REQUEST_BUFFER", 24) or 24)
    payload["write_buffer"] = int(getattr(allmod, "SEOUL_TRAFFIC_GUARD_WRITE_BUFFER", 6) or 6)
    payload["requests"] = int(payload.get("requests", 0) or 0)
    payload["writes"] = int(payload.get("writes", 0) or 0)
    return payload


def _build_traffic_plan(target_count: int, dry_run: bool, limit_state: dict[str, Any]) -> dict[str, Any]:
    req_cap = int(limit_state.get("request_cap", 0) or 0)
    write_cap = int(limit_state.get("write_cap", 0) or 0)
    req_used = int(limit_state.get("requests", 0) or 0)
    write_used = int(limit_state.get("writes", 0) or 0)
    request_buffer = int(limit_state.get("request_buffer", 0) or 0)
    write_buffer = int(limit_state.get("write_buffer", 0) or 0)

    fixed_login_req = 3
    per_target_req = 1 if dry_run else 2
    per_target_write = 0 if dry_run else 1

    req_remaining = max(0, req_cap - req_used)
    write_remaining = max(0, write_cap - write_used)
    usable_req = max(0, req_remaining - request_buffer - fixed_login_req)
    req_limit = usable_req // max(1, per_target_req)

    if per_target_write <= 0:
        write_limit = target_count
    else:
        usable_write = max(0, write_remaining - write_buffer)
        write_limit = usable_write // per_target_write

    safe_limit = max(0, min(int(target_count), int(req_limit), int(write_limit)))
    return {
        "targets": int(target_count),
        "mode": "dry-run" if dry_run else "apply",
        "req_remaining": int(req_remaining),
        "write_remaining": int(write_remaining),
        "fixed_login_req": int(fixed_login_req),
        "per_target_req": int(per_target_req),
        "per_target_write": int(per_target_write),
        "safe_limit": int(safe_limit),
    }


def _build_target_updates(
    publisher: allmod.MnaBoardPublisher,
    row: dict[str, Any],
) -> dict[str, Any]:
    wr_id = int(row.get("site_wr_id", 0) or 0)
    uid = str(row.get("uid", "")).strip()
    action_url, payload, form, _html = publisher.get_edit_payload(wr_id)

    updates: dict[str, Any] = {}
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}

    sheet_status = allmod._normalize_sync_status_label(row.get("sheet_status", ""))
    status_map = allmod._select_label_value_map(form, "wr_17")
    target_status_val = allmod._select_value_from_text(status_map, sheet_status)
    current_status_val = str(payload.get("wr_17", "")).strip()
    if target_status_val and current_status_val != target_status_val:
        updates["wr_17"] = target_status_val
        before["status"] = current_status_val
        after["status"] = sheet_status

    subject_item = {
        "price": allmod._compact_text(row.get("sheet_price", "")),
        "claim_price": allmod._normalize_multiline_text(row.get("sheet_claim_price", "")),
    }
    target_subject = allmod._build_mna_subject(subject_item)
    current_subject = str(payload.get("wr_subject", "") or "")
    if target_subject and (
        allmod._normalize_compare_text(current_subject)
        != allmod._normalize_compare_text(target_subject)
    ):
        updates["wr_subject"] = target_subject
        before["wr_subject"] = current_subject
        after["wr_subject"] = target_subject

    basis = {
        "sheet_price": row.get("sheet_price", ""),
        "sheet_claim_price": row.get("sheet_claim_price", ""),
    }
    current_memo = str(payload.get("wr_20", "") or "")
    target_memo = allmod._build_admin_memo_from_sheet_basis(uid, current_memo, payload, basis)
    if target_memo and (
        allmod._normalize_compare_text(current_memo)
        != allmod._normalize_compare_text(target_memo)
    ):
        updates["wr_20"] = target_memo
        before["wr_20"] = current_memo
        after["wr_20"] = target_memo

    return {
        "uid": uid,
        "row_idx": int(row.get("row_idx", 0) or 0),
        "wr_id": wr_id,
        "sheet_status": sheet_status,
        "updates": updates,
        "before": before,
        "after": after,
        "action_url": action_url,
        "payload": payload,
    }


def _write_report(report: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync recent Google Sheet rows to seoulmna.co.kr listings.")
    parser.add_argument("--limit", type=int, default=25, help="Recent sheet rows to inspect from the bottom.")
    parser.add_argument("--uid-list", default="", help="Explicit UID list (comma/space separated). Overrides --limit.")
    parser.add_argument("--uid-min", type=int, default=0, help="Minimum UID filter.")
    parser.add_argument("--uid-max", type=int, default=0, help="Maximum UID filter.")
    parser.add_argument("--seoul-max-pages", type=int, default=20, help="Pages to scan when resolving missing WR IDs.")
    parser.add_argument("--delay-sec", type=float, default=1.2, help="Delay between site writes.")
    parser.add_argument("--plan-only", action="store_true", help="Only print target/mapping plan without site login.")
    parser.add_argument("--dry-run", action="store_true", help="Read site and print diffs without writing.")
    parser.add_argument("--yes", action="store_true", help="Required for apply mode.")
    parser.add_argument(
        "--report-json",
        default="logs/recent_sheet_to_site_latest.json",
        help="Path for the latest JSON report.",
    )
    args = parser.parse_args()

    uid_list = _parse_uid_list(args.uid_list)
    if uid_list:
        targets = _load_targets_by_uid_list(uid_list)
    else:
        targets = _load_recent_targets(
            limit=max(0, int(args.limit or 0)),
            uid_min=max(0, int(args.uid_min or 0)),
            uid_max=max(0, int(args.uid_max or 0)),
        )
    if not targets:
        raise SystemExit("No recent sheet targets matched the filters.")

    _seed_site_wr_ids(targets)
    limit_state = _read_limit_state()
    plan = _build_traffic_plan(target_count=len(targets), dry_run=bool(args.dry_run), limit_state=limit_state)

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sheet_name": allmod.SHEET_NAME,
        "site_url": allmod.SITE_URL,
        "mode": "plan-only" if args.plan_only else ("dry-run" if args.dry_run else "apply"),
        "limit": int(args.limit or 0),
        "uid_list": uid_list,
        "uid_min": int(args.uid_min or 0),
        "uid_max": int(args.uid_max or 0),
        "seoul_max_pages": int(args.seoul_max_pages or 0),
        "limit_state": limit_state,
        "traffic_plan": plan,
        "targets": [
            {
                "row_idx": int(row.get("row_idx", 0) or 0),
                "uid": str(row.get("uid", "")).strip(),
                "sheet_no": str(row.get("sheet_no", "")).strip(),
                "sheet_status": str(row.get("sheet_status", "")).strip(),
                "sheet_price": str(row.get("sheet_price", "")).strip(),
                "sheet_claim_price": str(row.get("sheet_claim_price", "")).strip(),
                "site_wr_id": int(row.get("site_wr_id", 0) or 0),
                "site_wr_source": str(row.get("site_wr_source", "")).strip(),
            }
            for row in targets
        ],
    }

    if args.plan_only:
        _write_report(report, (ROOT / str(args.report_json)).resolve())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if not args.dry_run and not args.yes:
        raise SystemExit("Apply mode requires --yes.")

    if int(plan.get("safe_limit", 0) or 0) <= 0:
        report["error"] = "traffic_guard_safe_limit_zero"
        _write_report(report, (ROOT / str(args.report_json)).resolve())
        raise SystemExit(
            "Traffic guard safe limit is 0 for this run. Wait for the daily limit to reset or use --plan-only."
        )

    admin_id = str(allmod.CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(allmod.CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        raise SystemExit("ADMIN_ID/ADMIN_PW is missing.")

    publisher = allmod.MnaBoardPublisher(allmod.SITE_URL, allmod.MNA_BOARD_SLUG, admin_id, admin_pw)
    results: list[dict[str, Any]] = []
    try:
        publisher.login()

        unresolved = [str(row.get("uid", "")).strip() for row in targets if int(row.get("site_wr_id", 0) or 0) <= 0]
        resolve_diag = {"scanned_pages": 0, "scanned_wr_ids": 0}
        if unresolved:
            discovered, resolve_diag = allmod._discover_site_wr_map_from_board(
                publisher,
                unresolved,
                max_pages=max(0, int(args.seoul_max_pages or 0)),
            )
            for row in targets:
                if int(row.get("site_wr_id", 0) or 0) <= 0:
                    wr_id = int(discovered.get(str(row.get("uid", "")).strip(), 0) or 0)
                    if wr_id > 0:
                        row["site_wr_id"] = wr_id
                        row["site_wr_source"] = "board_scan"
        report["resolve_diag"] = resolve_diag

        safe_limit = int(plan.get("safe_limit", 0) or 0)
        if len(targets) > safe_limit:
            targets = targets[:safe_limit]
            report["trimmed_to_safe_limit"] = safe_limit

        stats = {"updated": 0, "same": 0, "failed": 0, "unmapped": 0}
        for row in targets:
            if int(row.get("site_wr_id", 0) or 0) <= 0:
                stats["unmapped"] += 1
                results.append(
                    {
                        "uid": row.get("uid", ""),
                        "row_idx": row.get("row_idx", 0),
                        "result": "unmapped",
                    }
                )
                continue

            try:
                prepared = _build_target_updates(publisher, row)
                updates = dict(prepared.get("updates", {}) or {})
                if not updates:
                    stats["same"] += 1
                    results.append(
                        {
                            "uid": prepared.get("uid", ""),
                            "row_idx": prepared.get("row_idx", 0),
                            "wr_id": prepared.get("wr_id", 0),
                            "result": "same",
                        }
                    )
                    continue

                if args.dry_run:
                    stats["updated"] += 1
                    results.append(
                        {
                            "uid": prepared.get("uid", ""),
                            "row_idx": prepared.get("row_idx", 0),
                            "wr_id": prepared.get("wr_id", 0),
                            "result": "planned",
                            "keys": sorted(updates.keys()),
                            "before": prepared.get("before", {}),
                            "after": prepared.get("after", {}),
                        }
                    )
                    continue

                publisher.submit_edit_updates(
                    str(prepared.get("action_url", "")).strip(),
                    dict(prepared.get("payload", {}) or {}),
                    updates,
                )
                stats["updated"] += 1
                results.append(
                    {
                        "uid": prepared.get("uid", ""),
                        "row_idx": prepared.get("row_idx", 0),
                        "wr_id": prepared.get("wr_id", 0),
                        "result": "updated",
                        "keys": sorted(updates.keys()),
                    }
                )
                if float(args.delay_sec or 0.0) > 0:
                    time.sleep(max(0.0, float(args.delay_sec or 0.0)))
            except Exception as exc:
                stats["failed"] += 1
                results.append(
                    {
                        "uid": row.get("uid", ""),
                        "row_idx": row.get("row_idx", 0),
                        "wr_id": row.get("site_wr_id", 0),
                        "result": "failed",
                        "error": str(exc),
                    }
                )

        report["stats"] = stats
        report["results"] = results
    finally:
        try:
            publisher.close()
        except Exception:
            pass

    report_path = (ROOT / str(args.report_json)).resolve()
    _write_report(report, report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
