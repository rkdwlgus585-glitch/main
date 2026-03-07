from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import all as allmod


def _sheet_status(value: str) -> str:
    return allmod._normalize_sync_status_label(value)


def _row_to_record(row: list[str]) -> dict[str, Any]:
    return {
        "sheet_no": allmod._row_text(row, 0),
        "sheet_status": _sheet_status(allmod._row_text(row, 1)),
        "license": allmod._row_text(row, 2),
        "claim_price": allmod._row_text(row, 33),
        "source_uid": allmod._row_text(row, 32),
    }


def _bool_issue(row: dict[str, Any], key: str, issue: str, value: bool) -> None:
    if value:
        row.setdefault(key, []).append(issue)


def _select_targets(
    uid_to_row: dict[str, int],
    all_values: list[list[str]],
    *,
    uid_min: int,
    uid_max: int,
    sheet_no_min: int,
    limit: int,
) -> list[str]:
    rows: list[tuple[int, str]] = []
    for uid, row_idx in uid_to_row.items():
        uid_text = str(uid or "").strip()
        if not uid_text.isdigit():
            continue
        uid_num = int(uid_text)
        if uid_min and uid_num < uid_min:
            continue
        if uid_max and uid_num > uid_max:
            continue
        row = all_values[row_idx - 1] if 0 < row_idx <= len(all_values) else []
        sheet_no = allmod._sheet_no_to_int(allmod._row_text(row, 0))
        if sheet_no_min and sheet_no < sheet_no_min:
            continue
        rows.append((row_idx, uid_text))
    rows.sort(key=lambda x: x[0])
    if limit > 0:
        rows = rows[-limit:]
    return [uid for _, uid in rows]


def _site_read_headroom_ok() -> tuple[bool, dict[str, Any]]:
    state_path = Path(str(getattr(allmod, "SEOUL_DAILY_LIMIT_STATE_FILE", "") or "")).resolve()
    req_cap = int(getattr(allmod, "SEOUL_DAILY_REQUEST_CAP", 0) or 0)
    req_buffer = int(getattr(allmod, "SEOUL_TRAFFIC_GUARD_REQUEST_BUFFER", 0) or 0)
    payload: dict[str, Any] = {
        "state_file": str(state_path),
        "request_cap": req_cap,
        "request_buffer": req_buffer,
        "requests": 0,
        "allowed": True,
    }
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        requests_used = int(raw.get("requests", 0) or 0)
        payload["requests"] = requests_used
        if req_cap > 0 and requests_used >= max(0, req_cap - req_buffer):
            payload["allowed"] = False
    except Exception:
        pass
    return bool(payload.get("allowed")), payload


def _discover_site_map_for_targets(target_uids: list[str], max_pages: int) -> tuple[dict[str, int], dict[str, Any]]:
    out = dict(allmod._seed_site_wr_map_from_upload_state() or {})
    unresolved = [uid for uid in target_uids if int(out.get(uid, 0) or 0) <= 0]
    diag = {"seeded": len(out), "resolved": 0, "scanned_pages": 0, "scanned_wr_ids": 0}
    if not unresolved:
        return out, diag
    headroom_ok, headroom = _site_read_headroom_ok()
    diag["headroom"] = headroom
    if not headroom_ok:
        diag["warning"] = "site_read_guard_skip"
        return out, diag

    admin_id = str(allmod.CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(allmod.CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        diag["warning"] = "admin_credentials_missing"
        return out, diag

    publisher = allmod.MnaBoardPublisher(allmod.SITE_URL, allmod.MNA_BOARD_SLUG, admin_id, admin_pw)
    try:
        publisher.login()
        discovered, raw_diag = allmod._discover_site_wr_map_from_board(
            publisher,
            unresolved,
            max_pages=max_pages,
        )
        for uid, wr_id in dict(discovered or {}).items():
            wr_num = int(wr_id or 0)
            if wr_num > 0:
                out[str(uid)] = wr_num
        diag["resolved"] = len([uid for uid in unresolved if int(out.get(uid, 0) or 0) > 0])
        diag["scanned_pages"] = int(raw_diag.get("scanned_pages", 0))
        diag["scanned_wr_ids"] = int(raw_diag.get("scanned_wr_ids", 0))
    finally:
        try:
            publisher.close()
        except Exception:
            pass
    return out, diag


def _fetch_site_payloads(site_map: dict[str, int], target_uids: list[str]) -> dict[int, dict[str, Any]]:
    wr_ids = sorted({int(site_map.get(uid, 0) or 0) for uid in target_uids if int(site_map.get(uid, 0) or 0) > 0})
    if not wr_ids:
        return {}
    headroom_ok, _headroom = _site_read_headroom_ok()
    if not headroom_ok:
        return {}

    admin_id = str(allmod.CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(allmod.CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        return {}

    publisher = allmod.MnaBoardPublisher(allmod.SITE_URL, allmod.MNA_BOARD_SLUG, admin_id, admin_pw)
    payloads: dict[int, dict[str, Any]] = {}
    try:
        try:
            publisher.login()
        except Exception:
            return payloads
        for wr_id in wr_ids:
            try:
                _action_url, payload, form, _html = publisher.get_edit_payload(wr_id)
            except Exception:
                continue
            status_map = allmod._select_label_value_map(form, "wr_17")
            status_value = str(payload.get("wr_17", "")).strip()
            status_label = ""
            for label, value in status_map.items():
                if str(value).strip() == status_value:
                    status_label = str(label).strip()
                    break
            if not status_label:
                status_label = status_value
            payloads[wr_id] = {
                "status_label": _sheet_status(status_label),
                "admin_uid": allmod._extract_uid_from_admin_memo(payload.get("wr_20", "")),
                "subject": str(payload.get("wr_subject", "")).strip(),
            }
    finally:
        try:
            publisher.close()
        except Exception:
            pass
    return payloads


def build_report(*, uid_min: int, uid_max: int, sheet_no_min: int, limit: int, nowmna_max_pages: int, seoul_max_pages: int) -> dict[str, Any]:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(allmod.JSON_FILE, scope)
    worksheet = gspread.authorize(creds).open(allmod.SHEET_NAME).sheet1
    all_values = worksheet.get_all_values()
    sheet_ctx = allmod._analyze_sheet_rows(all_values)
    uid_to_row = dict(sheet_ctx.get("existing_web_ids", {}))
    target_uids = _select_targets(
        uid_to_row,
        all_values,
        uid_min=uid_min,
        uid_max=uid_max,
        sheet_no_min=sheet_no_min,
        limit=limit,
    )
    if not target_uids:
        raise SystemExit("No target rows matched filters.")

    nowmna_uids, now_status_map, now_pages = allmod._collect_nowmna_uid_status_map(max_pages=nowmna_max_pages, delay_sec=0.0)
    nowmna_uid_set = {str(uid) for uid in list(nowmna_uids or [])}
    site_map, site_diag = _discover_site_map_for_targets(target_uids, max_pages=seoul_max_pages)
    site_payloads = _fetch_site_payloads(site_map, target_uids)
    upload_state = allmod._load_upload_state(allmod.UPLOAD_STATE_FILE)
    uploaded = upload_state.get("uploaded_uids", {}) if isinstance(upload_state, dict) else {}

    no_to_uids: dict[str, list[str]] = defaultdict(list)
    rows: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()

    for uid in target_uids:
        row_idx = int(uid_to_row.get(uid, 0) or 0)
        row = all_values[row_idx - 1] if 0 < row_idx <= len(all_values) else []
        rec = _row_to_record(row)
        sheet_no = rec["sheet_no"]
        sheet_status = rec["sheet_status"]
        claim_price = rec["claim_price"]
        sheet_no_num = allmod._sheet_no_to_int(sheet_no)
        if sheet_no:
            no_to_uids[sheet_no].append(uid)

        source_present = uid in nowmna_uid_set
        now_status = "완료" if not source_present else _sheet_status(str(now_status_map.get(uid, "가능")).strip() or "가능")
        authoritative_wr_id = int(site_map.get(uid, 0) or 0)
        site_payload = dict(site_payloads.get(authoritative_wr_id, {}) or {})
        site_status = _sheet_status(site_payload.get("status_label", "")) if authoritative_wr_id > 0 else ""
        state_row = uploaded.get(uid, {}) if isinstance(uploaded, dict) else {}
        state_url = str((state_row or {}).get("url", "")).strip()

        issues: list[str] = []
        _bool_issue(rec, "issues", "sheet_no_mismatch", authoritative_wr_id > 0 and sheet_no_num != authoritative_wr_id)
        _bool_issue(rec, "issues", "sheet_no_without_site", sheet_no_num > 0 and authoritative_wr_id <= 0)
        _bool_issue(rec, "issues", "sheet_status_mismatch_source", sheet_status != now_status)
        _bool_issue(rec, "issues", "site_status_mismatch_source", authoritative_wr_id > 0 and site_status and site_status != now_status)
        _bool_issue(rec, "issues", "state_url_noncanonical", bool(state_url) and "/bbs/write.php" in state_url)
        _bool_issue(
            rec,
            "issues",
            "active_with_claim_but_no_site",
            now_status != "완료" and bool(allmod._compact_text(claim_price)) and authoritative_wr_id <= 0,
        )
        _bool_issue(
            rec,
            "issues",
            "complete_with_claim_and_no_site",
            now_status == "완료" and bool(allmod._compact_text(claim_price)) and authoritative_wr_id <= 0 and sheet_no_num > 0,
        )
        _bool_issue(
            rec,
            "issues",
            "site_uid_mismatch",
            authoritative_wr_id > 0 and bool(site_payload) and str(site_payload.get("admin_uid", "")).strip() not in {"", uid},
        )

        issues = list(rec.get("issues", []) or [])
        for issue in issues:
            issue_counter[issue] += 1
        rec.update(
            {
                "uid": uid,
                "row_idx": row_idx,
                "now_status": now_status,
                "source_present": source_present,
                "site_wr_id": authoritative_wr_id,
                "site_status": site_status,
                "site_admin_uid": str(site_payload.get("admin_uid", "")).strip(),
                "state_url": state_url,
                "issues": issues,
            }
        )
        rows.append(rec)

    for sheet_no, uid_list in no_to_uids.items():
        if len(uid_list) <= 1:
            continue
        issue_counter["duplicate_sheet_no"] += len(uid_list)
        for row in rows:
            if row.get("sheet_no") == sheet_no and "duplicate_sheet_no" not in row.get("issues", []):
                row["issues"].append("duplicate_sheet_no")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "filters": {
            "uid_min": uid_min,
            "uid_max": uid_max,
            "sheet_no_min": sheet_no_min,
            "limit": limit,
            "nowmna_max_pages": nowmna_max_pages,
            "seoul_max_pages": seoul_max_pages,
        },
        "sheet_name": allmod.SHEET_NAME,
        "target_count": len(rows),
        "now_pages_scanned": now_pages,
        "site_diag": site_diag,
        "issue_counts": dict(issue_counter),
        "rows": rows,
    }


def write_report(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)

    lines = [
        "# Listing Alignment Audit",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- sheet_name: `{report.get('sheet_name', '')}`",
        f"- target_count: `{report.get('target_count', 0)}`",
        f"- now_pages_scanned: `{report.get('now_pages_scanned', 0)}`",
        f"- site_diag: `{json.dumps(report.get('site_diag', {}), ensure_ascii=False)}`",
        "",
        "## Issue Counts",
        "",
    ]
    issue_counts = dict(report.get("issue_counts", {}) or {})
    if issue_counts:
        for key, value in sorted(issue_counts.items()):
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Rows With Issues", ""])
    issue_rows = [row for row in list(report.get("rows", []) or []) if row.get("issues")]
    if not issue_rows:
        lines.append("- none")
    else:
        for row in issue_rows:
            lines.append(
                f"- UID `{row.get('uid', '')}` / sheet_no=`{row.get('sheet_no', '')}` / "
                f"site_wr=`{row.get('site_wr_id', '')}` / sheet_status=`{row.get('sheet_status', '')}` / "
                f"now_status=`{row.get('now_status', '')}` / issues=`{', '.join(row.get('issues', []))}`"
            )

    with md_path.open("w", encoding="utf-8-sig") as fp:
        fp.write("\n".join(lines).rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit recent now/sheet/co.kr alignment drift.")
    parser.add_argument("--uid-min", type=int, default=0)
    parser.add_argument("--uid-max", type=int, default=0)
    parser.add_argument("--sheet-no-min", type=int, default=0)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--nowmna-max-pages", type=int, default=4)
    parser.add_argument("--seoul-max-pages", type=int, default=20)
    parser.add_argument("--report-json", default="logs/listing_alignment_audit_latest.json")
    parser.add_argument("--report-md", default="logs/listing_alignment_audit_latest.md")
    args = parser.parse_args()

    report = build_report(
        uid_min=int(args.uid_min or 0),
        uid_max=int(args.uid_max or 0),
        sheet_no_min=int(args.sheet_no_min or 0),
        limit=int(args.limit or 0),
        nowmna_max_pages=int(args.nowmna_max_pages or 0),
        seoul_max_pages=int(args.seoul_max_pages or 0),
    )
    json_path = (ROOT / str(args.report_json)).resolve()
    md_path = (ROOT / str(args.report_md)).resolve()
    write_report(report, json_path, md_path)
    print(f"[audit] json={json_path}")
    print(f"[audit] md={md_path}")
    print(f"[audit] issue_counts={json.dumps(report.get('issue_counts', {}), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
