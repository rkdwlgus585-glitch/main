import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import all  # noqa: E402


def _pad_row(row, width):
    out = list(row or [])
    if len(out) < width:
        out.extend([""] * (width - len(out)))
    return out[:width]


def _sheet_state(values):
    if not values:
        return {
            "width": 41,
            "header": [],
            "anchors": [],
            "orphans": [],
        }

    width = max(41, max(len(r) for r in values))
    header = _pad_row(values[0], width)
    anchors = []
    orphans = []

    for row_idx, row in enumerate(values[1:], start=2):
        if all._is_listing_anchor_row(row):
            anchors.append((row_idx, _pad_row(row, width)))
        elif any(str(cell or "").strip() for cell in row):
            orphans.append((row_idx, _pad_row(row, width)))

    return {
        "width": width,
        "header": header,
        "anchors": anchors,
        "orphans": orphans,
    }


def _write_backup(values, state, backup_prefix):
    os.makedirs("logs", exist_ok=True)
    json_path = f"{backup_prefix}.json"
    csv_path = f"{backup_prefix}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "sheet_name": all.SHEET_NAME,
                "total_rows": len(values),
                "width": state["width"],
                "anchor_rows": len(state["anchors"]),
                "orphan_rows": len(state["orphans"]),
                "first_anchor_row": state["anchors"][0][0] if state["anchors"] else 0,
                "last_anchor_row": state["anchors"][-1][0] if state["anchors"] else 0,
                "orphan_row_indexes_head": [x[0] for x in state["orphans"][:50]],
                "orphan_row_indexes_tail": [x[0] for x in state["orphans"][-50:]],
                "values": values,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(values)

    return json_path, csv_path


def _load_worksheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(all.JSON_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(all.SHEET_NAME).sheet1


def main():
    parser = argparse.ArgumentParser(description="Compress row gaps in 26양도매물 sheet by listing anchor rows.")
    parser.add_argument("--apply", action="store_true", help="Apply changes to sheet (default: dry-run)")
    parser.add_argument("--keep-orphan", action="store_true", help="Keep orphan rows after anchors instead of dropping")
    parser.add_argument("--max-orphan-sample", type=int, default=20, help="How many orphan row indices to print")
    args = parser.parse_args()

    ws = _load_worksheet()
    values = ws.get_all_values()
    state = _sheet_state(values)
    width = state["width"]
    anchors = state["anchors"]
    orphans = state["orphans"]

    compact_rows = [state["header"]]
    compact_rows.extend([row for _, row in anchors])
    if args.keep_orphan:
        compact_rows.extend([row for _, row in orphans])

    old_rows = len(values)
    new_rows = len(compact_rows)
    moved = 0
    move_examples = []
    for new_pos, (old_pos, row) in enumerate(anchors, start=2):
        if old_pos != new_pos:
            moved += 1
            if len(move_examples) < 20:
                move_examples.append(
                    {
                        "old_row": old_pos,
                        "new_row": new_pos,
                        "번호": row[0],
                        "uid": all.extract_id_strict(row[34]) or all.extract_id_strict(row[33]) or "",
                    }
                )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_prefix = os.path.join("logs", f"sheet_compact_backup_{ts}")
    backup_json, backup_csv = _write_backup(values, state, backup_prefix)

    print(f"[sheet-compact] sheet={all.SHEET_NAME} rows={old_rows} width={width}")
    print(f"[sheet-compact] anchors={len(anchors)} orphans={len(orphans)} moved={moved}")
    if orphans:
        sample = [x[0] for x in orphans[: max(1, int(args.max_orphan_sample))]]
        print(f"[sheet-compact] orphan sample rows={sample}")
    print(f"[sheet-compact] backup_json={backup_json}")
    print(f"[sheet-compact] backup_csv={backup_csv}")
    print(f"[sheet-compact] target_rows={new_rows} (keep_orphan={args.keep_orphan})")
    for ex in move_examples:
        print(
            f"  - old_row={ex['old_row']} -> new_row={ex['new_row']} "
            f"번호={ex['번호']} uid={ex['uid']}"
        )

    if not args.apply:
        print("[sheet-compact] dry-run only. use --apply to write changes.")
        return 0

    end_col = all._col_to_a1(width)
    write_range = f"A1:{end_col}{new_rows}"
    ws.update(range_name=write_range, values=compact_rows)

    if old_rows > new_rows:
        clear_range = f"A{new_rows + 1}:{end_col}{old_rows}"
        ws.batch_clear([clear_range])
        print(f"[sheet-compact] cleared tail range {clear_range}")

    refreshed = ws.get_all_values()
    ctx = all._analyze_sheet_rows(refreshed)
    print(
        f"[sheet-compact] done. real_last_row={ctx['real_last_row']} "
        f"last_my_number={ctx['last_my_number']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

