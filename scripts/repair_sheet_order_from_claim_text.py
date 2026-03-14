from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ALL_ROOT = Path(r"H:\ALL")
if str(ALL_ROOT) not in sys.path:
    sys.path.insert(0, str(ALL_ROOT))

import all as mod


STATUS_AVAILABLE = "가능"
STATUS_HOLD = "보류"
STATUS_DONE = "완료"
STATUS_NEGOTIATE = "협의"
STATUS_NEGOTIATING = "협의중"
STATUS_DELETE = "삭제"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair sheet UID order and duplicates. Row payload rewrites are opt-in.")
    parser.add_argument("--claim-file", required=True, help="Path to 청구 양도가 text file")
    parser.add_argument("--apply", action="store_true", help="Write changes to the Google Sheet")
    parser.add_argument("--json-file", default="", help="Override service_account.json path")
    parser.add_argument("--sheet-name", default="", help="Override sheet name")
    parser.add_argument("--rewrite-row-payload", action="store_true", help="Also rewrite B/C/AH from claim text for blank-A UID rows")
    parser.add_argument("--fill-missing-number", action="store_true", help="Also assign A열 번호 to blank-A UID rows")
    parser.add_argument("--drop-duplicates", action="store_true", help="Also remove duplicate rows. Disabled by default to preserve original sheet history.")
    return parser.parse_args()


def col_to_a1(n: int) -> str:
    out = ""
    cur = int(n)
    while cur > 0:
        cur, rem = divmod(cur - 1, 26)
        out = chr(65 + rem) + out
    return out or "A"


def pad_row(row: list[str], width: int) -> list[str]:
    out = list(row or [])
    if len(out) < width:
        out.extend([""] * (width - len(out)))
    return out[:width]


def extract_uid(row: list[str]) -> str:
    for col_idx in (34, 33, 32):
        cand = mod.extract_id_strict(mod._row_text(row, col_idx))
        if cand:
            return cand
    return ""


def desired_status(claim: str, claim_kind: str) -> str:
    src = str(claim or "").strip()
    kind = str(claim_kind or "").strip()
    if kind == "range":
        return STATUS_AVAILABLE
    if src == STATUS_HOLD:
        return STATUS_HOLD
    if src in {STATUS_DONE, STATUS_DELETE}:
        return STATUS_DONE
    if src in {STATUS_NEGOTIATE, STATUS_NEGOTIATING}:
        return STATUS_AVAILABLE
    return ""


def parse_license_from_raw(raw_line: str) -> dict[str, str]:
    src = str(raw_line or "").strip()
    src = re.sub(r"\[cite:[^\]]*\]\s*$", "", src).strip()
    m_uid = re.match(r"^(\d{4,6})\s*(.*)$", src)
    if m_uid:
        src = m_uid.group(2).strip()

    cut = len(src)
    range_match = re.search(r"\d+(?:\.\d+)?억\s*[-~]\s*\d+(?:\.\d+)?억", src)
    if range_match:
        cut = min(cut, range_match.start())
    else:
        single_match = re.search(r"\d+(?:\.\d+)?억", src)
        if single_match:
            cut = min(cut, single_match.start())

    for token in (STATUS_NEGOTIATING, STATUS_NEGOTIATE, STATUS_HOLD, STATUS_DONE, STATUS_DELETE):
        pos = src.find(token)
        if pos >= 0:
            cut = min(cut, pos)

    license_text = re.sub(r"\([^)]*\)", "", src[:cut]).strip()
    if not license_text:
        return {"multiline": "", "inline": ""}

    license_text = (
        license_text.replace(",", "/")
        .replace(" / ", "/")
        .replace("·", "/")
        .replace("ㆍ", "/")
    )
    tokens = [part.strip() for part in re.split(r"[\\/]+", license_text) if part.strip()]

    normalized: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        name = mod._compact_text(mod.normalize_license(token))
        key = mod._normalize_license_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(name)

    return {"multiline": "\n".join(normalized), "inline": " ".join(normalized)}


def load_sheet(args: argparse.Namespace):
    if args.json_file:
        mod.JSON_FILE = args.json_file
    if args.sheet_name:
        mod.SHEET_NAME = args.sheet_name
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = mod.ServiceAccountCredentials.from_json_keyfile_name(mod.JSON_FILE, scope)
    client = mod.gspread.authorize(creds)
    worksheet = client.open(mod.SHEET_NAME).sheet1
    values = worksheet.get_all_values()
    return worksheet, values


def backup_sheet(logs_dir: Path, values: list[list[str]]) -> dict[str, str]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = logs_dir / f"sheet_backup_before_repair_{ts}.json"
    csv_path = logs_dir / f"sheet_backup_before_repair_{ts}.csv"
    json_path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(values)
    return {"json": str(json_path), "csv": str(csv_path)}


def analyze_and_repair(
    values: list[list[str]],
    parsed_map: dict[str, dict],
    *,
    rewrite_row_payload: bool = False,
    fill_missing_number: bool = False,
    drop_duplicates: bool = False,
) -> dict:
    header = pad_row(values[0] if values else [], 42)
    raw_rows = [pad_row(row, 42) for row in values[1:]]

    row_items = []
    by_uid: dict[str, list[dict]] = defaultdict(list)
    max_no = 0
    for row_idx, row in enumerate(raw_rows, start=2):
        uid = extract_uid(row)
        no_num = mod._sheet_no_to_int(mod._row_text(row, 0))
        max_no = max(max_no, no_num)
        item = {
            "row_idx": row_idx,
            "uid": uid,
            "row": row,
            "drop": False,
            "fixes": {},
        }
        row_items.append(item)
        if uid:
            by_uid[uid].append(item)

    dedupe_actions = []
    for uid, items in by_uid.items():
        if len(items) < 2:
            continue
        filled = [x for x in items if mod._compact_text(mod._row_text(x["row"], 33))]
        blank = [x for x in items if not mod._compact_text(mod._row_text(x["row"], 33))]
        for drop in blank:
            if filled:
                dedupe_actions.append(
                    {
                        "uid": uid,
                        "drop_row": drop["row_idx"],
                        "keep_row": filled[0]["row_idx"],
                        "reason": "blank_ah_duplicate",
                    }
                )
                if drop_duplicates:
                    drop["drop"] = True

        sig_map: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for item in items:
            if item["drop"]:
                continue
            row = item["row"]
            sig = (
                mod._row_text(row, 2),
                mod._row_text(row, 18),
                mod._row_text(row, 33),
            )
            sig_map[sig].append(item)
        for sig_rows in sig_map.values():
            if len(sig_rows) < 2:
                continue
            sig_rows = sorted(
                sig_rows,
                key=lambda x: (0 if mod._row_text(x["row"], 1) == STATUS_AVAILABLE else 1, x["row_idx"]),
            )
            keep = sig_rows[0]
            for drop in sig_rows[1:]:
                dedupe_actions.append(
                    {
                        "uid": uid,
                        "drop_row": drop["row_idx"],
                        "keep_row": keep["row_idx"],
                        "reason": "exact_duplicate",
                    }
                )
                if drop_duplicates:
                    drop["drop"] = True

    row_fix_actions = []
    if rewrite_row_payload:
        for item in row_items:
            if item["drop"]:
                continue
            row = item["row"]
            uid = item["uid"]
            if not uid:
                continue
            if mod._row_text(row, 0).strip():
                continue
            parsed = parsed_map.get(uid)
            if not parsed:
                continue

            claim = str(parsed.get("claim", "")).strip()
            claim_kind = str(parsed.get("claim_kind", "")).strip()
            license_parts = parse_license_from_raw(str(parsed.get("raw_line", "")))
            current_c = mod._row_text(row, 2)
            current_b = mod._row_text(row, 1)
            current_ah = mod._row_text(row, 33)

            desired_b = desired_status(claim, claim_kind) or current_b
            desired_c = license_parts["multiline"] or current_c
            ah_license_inline = license_parts["inline"] or current_c.replace("\n", " ").strip()
            first_line = uid + (f" {ah_license_inline}" if ah_license_inline else "")
            desired_ah = first_line + (f"\n{claim}" if claim else "")

            changes = {}
            if desired_b and desired_b != current_b:
                row[1] = desired_b
                changes["B"] = {"old": current_b, "new": desired_b}
            if desired_c and desired_c != current_c:
                row[2] = desired_c
                changes["C"] = {"old": current_c, "new": desired_c}
            if desired_ah and desired_ah != current_ah:
                row[33] = desired_ah
                changes["AH"] = {"old": current_ah, "new": desired_ah}
            if changes:
                row_fix_actions.append({"uid": uid, "row_idx": item["row_idx"], "changes": changes})

    kept_uid_rows = [item for item in row_items if item["uid"] and not item["drop"]]
    kept_nonuid_rows = [item for item in row_items if (not item["uid"]) and not item["drop"]]
    kept_uid_rows.sort(key=lambda x: (int(x["uid"]), x["row_idx"]))

    next_no = max_no
    numbering_actions = []
    if fill_missing_number:
        for item in kept_uid_rows:
            row = item["row"]
            if mod._row_text(row, 0).strip():
                continue
            next_no += 1
            old = mod._row_text(row, 0)
            row[0] = str(next_no)
            numbering_actions.append({"uid": item["uid"], "row_idx": item["row_idx"], "old": old, "new": str(next_no)})

    repaired_values = [header] + [item["row"] for item in kept_uid_rows] + [item["row"] for item in kept_nonuid_rows]

    prev_num = None
    violations_after = 0
    for item in kept_uid_rows:
        uid_num = int(item["uid"])
        if prev_num is not None and uid_num < prev_num:
            violations_after += 1
        prev_num = uid_num

    return {
        "original_row_count": len(raw_rows),
        "repaired_row_count": len(repaired_values) - 1,
        "dedupe_actions": dedupe_actions,
        "row_fix_actions": row_fix_actions,
        "numbering_actions": numbering_actions,
        "violations_after": violations_after,
        "repaired_values": repaired_values,
    }


def write_sheet(worksheet, new_values: list[list[str]], old_row_count: int) -> None:
    end_col = col_to_a1(len(new_values[0]))
    new_row_count = len(new_values)
    worksheet.update(f"A1:{end_col}{new_row_count}", new_values)
    if old_row_count > new_row_count:
        worksheet.batch_clear([f"A{new_row_count + 1}:{end_col}{old_row_count}"])


def main() -> int:
    args = parse_args()
    logs_dir = Path(r"H:\auto\logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    claim_file = Path(args.claim_file)
    if not claim_file.exists():
        raise SystemExit(f"claim file not found: {claim_file}")

    parsed_map = mod._parse_kakao_claim_updates(str(claim_file), sender_contains="")
    worksheet, values = load_sheet(args)
    backup = backup_sheet(logs_dir, values)
    plan = analyze_and_repair(
        values,
        parsed_map,
        rewrite_row_payload=bool(args.rewrite_row_payload),
        fill_missing_number=bool(args.fill_missing_number),
        drop_duplicates=bool(args.drop_duplicates),
    )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "claim_file": str(claim_file),
        "sheet_name": mod.SHEET_NAME,
        "backup": backup,
        "original_row_count": plan["original_row_count"],
        "repaired_row_count": plan["repaired_row_count"],
        "dedupe_count": len(plan["dedupe_actions"]),
        "row_fix_count": len(plan["row_fix_actions"]),
        "numbering_count": len(plan["numbering_actions"]),
        "violations_after": plan["violations_after"],
        "rewrite_row_payload": bool(args.rewrite_row_payload),
        "fill_missing_number": bool(args.fill_missing_number),
        "drop_duplicates": bool(args.drop_duplicates),
        "dedupe_sample": plan["dedupe_actions"][:20],
        "row_fix_sample": plan["row_fix_actions"][:20],
        "numbering_sample": plan["numbering_actions"][:20],
        "applied": bool(args.apply),
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = logs_dir / f"sheet_repair_plan_{ts}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(str(summary_path))

    if args.apply:
        write_sheet(worksheet, plan["repaired_values"], old_row_count=len(values))
        print("APPLY_DONE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
