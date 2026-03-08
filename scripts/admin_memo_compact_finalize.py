from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import all as app

DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "cli\uD559\uC2B5"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_cell(value) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return " ".join(text.split())


def _safe_int(value) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def _load_sheet_records() -> list[dict]:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = app.ServiceAccountCredentials.from_json_keyfile_name(app.JSON_FILE, scope)
    client = app.gspread.authorize(creds)
    worksheet = client.open(app.SHEET_NAME).sheet1
    all_values = worksheet.get_all_values()
    return list(app._build_estimate_records(all_values))


def _build_export_text(records: list[dict]) -> str:
    sorted_records = sorted(
        records,
        key=lambda rec: (_safe_int(rec.get("number")), _safe_int(rec.get("uid"))),
        reverse=True,
    )
    lines = [
        "SeoulMNA admin memo compact export",
        f"generated_at\t{datetime.now().isoformat(timespec='seconds')}",
        f"sheet_name\t{_clean_cell(app.SHEET_NAME)}",
        f"total_records\t{len(sorted_records)}",
        "",
        "uid\tno\tlicense\tcurrent_price\tclaim_price\tlocation\tlicense_year\tcompany_type",
    ]
    for rec in sorted_records:
        lines.append(
            "\t".join(
                [
                    _clean_cell(rec.get("uid")),
                    str(_safe_int(rec.get("number")) or ""),
                    _clean_cell(rec.get("license_text")),
                    _clean_cell(rec.get("current_price_text")),
                    _clean_cell(rec.get("claim_price_text")),
                    _clean_cell(rec.get("location")),
                    str(_safe_int(rec.get("license_year")) or ""),
                    _clean_cell(rec.get("company_type")),
                ]
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _trim_log_file(path: Path, keep_lines: int) -> dict:
    result = {"path": str(path), "trimmed": False, "before_lines": 0, "after_lines": 0}
    if keep_lines <= 0 or not path.exists():
        return result
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    result["before_lines"] = len(lines)
    if len(lines) <= keep_lines:
        result["after_lines"] = len(lines)
        return result
    kept = lines[-keep_lines:]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    result["trimmed"] = True
    result["after_lines"] = len(kept)
    return result


def _cleanup_output_dir(output_dir: Path, keep_name: str) -> list[str]:
    removed: list[str] = []
    if not output_dir.exists():
        return removed
    for child in output_dir.iterdir():
        if child.name == keep_name:
            continue
        if child.is_file() and child.name.startswith("seoulmna_admin_memo_compact"):
            child.unlink(missing_ok=True)
            removed.append(str(child))
        elif child.is_dir() and child.name.startswith("seoulmna_admin_memo_compact"):
            shutil.rmtree(child, ignore_errors=True)
            removed.append(str(child))
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize admin memo backlog into one compact TXT export.")
    parser.add_argument("--state-file", default="logs/admin_memo_sync_state.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--txt-name", default="seoulmna_admin_memo_compact_latest.txt")
    parser.add_argument("--marker-file", default="logs/admin_memo_compact_finalize_marker.json")
    parser.add_argument("--trim-log-path", default="logs/auto_admin_memo_sync.log")
    parser.add_argument("--trim-log-lines", type=int, default=200)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    state_path = (REPO_ROOT / args.state_file).resolve() if not Path(args.state_file).is_absolute() else Path(args.state_file)
    marker_path = (REPO_ROOT / args.marker_file).resolve() if not Path(args.marker_file).is_absolute() else Path(args.marker_file)
    trim_log_path = (REPO_ROOT / args.trim_log_path).resolve() if not Path(args.trim_log_path).is_absolute() else Path(args.trim_log_path)
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / args.txt_name

    state = _read_json(state_path)
    processed_ids = state.get("processed_wr_ids") or []
    signature = {
        "state_signature": _clean_cell(state.get("signature")),
        "processed_count": len(processed_ids),
        "last_success_wr_id": _safe_int(state.get("last_success_wr_id")),
        "state_updated_at": _clean_cell(state.get("updated_at")),
    }
    export_signature = json.dumps(signature, ensure_ascii=False, sort_keys=True)
    marker = _read_json(marker_path)

    if not args.force and marker.get("export_signature") == export_signature and output_path.exists():
        print(f"skip: unchanged signature ({output_path})")
        return 0

    if not processed_ids:
        print("skip: admin memo state has no processed WR ids")
        return 0

    records = _load_sheet_records()
    output_path.write_text(_build_export_text(records), encoding="utf-8-sig")
    removed = _cleanup_output_dir(output_dir, output_path.name)
    trim_result = _trim_log_file(trim_log_path, int(args.trim_log_lines or 0))

    marker_payload = {
        "export_signature": export_signature,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "output_path": str(output_path),
        "record_count": len(records),
        "processed_count": len(processed_ids),
        "last_success_wr_id": _safe_int(state.get("last_success_wr_id")),
        "trim_log": trim_result,
        "removed_paths": removed,
    }
    _write_json(marker_path, marker_payload)

    print(f"compact finalize complete: {output_path}")
    print(
        f"records={len(records)} processed_wr={len(processed_ids)} "
        f"last_success_wr={marker_payload['last_success_wr_id']}"
    )
    if trim_result.get("trimmed"):
        print(
            f"log_trimmed={trim_result.get('before_lines', 0)}->"
            f"{trim_result.get('after_lines', 0)} ({trim_log_path})"
        )
    if removed:
        print(f"removed={len(removed)} old compact artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

