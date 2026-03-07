#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "logs" / "yangdo_consult_requests.sqlite3"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from yangdo_consult_api import _normalize_business_payload


def _normalize_row(source: str, page_mode: str, raw_json: str) -> Tuple[str, str]:
    payload: Dict[str, object] = {}
    try:
        loaded = json.loads(str(raw_json or "")) if str(raw_json or "").strip() else {}
    except Exception:
        loaded = {}
    if isinstance(loaded, dict):
        payload.update(loaded)
    if "source" not in payload:
        payload["source"] = str(source or "")
    if "page_mode" not in payload:
        payload["page_mode"] = str(page_mode or "")
    normalized = _normalize_business_payload(payload)
    return str(normalized.get("source", "") or ""), str(normalized.get("page_mode", "") or "")


def migrate(db_path: Path, dry_run: bool = False) -> Dict[str, int]:
    stats = {
        "consult_scanned": 0,
        "consult_updated": 0,
        "usage_scanned": 0,
        "usage_updated": 0,
    }
    if not db_path.exists():
        return stats

    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute("BEGIN")
        try:
            consult_rows = conn.execute(
                """
                SELECT id, COALESCE(source, ''), COALESCE(page_mode, ''), COALESCE(raw_json, '')
                FROM consult_requests
                """
            ).fetchall()
        except sqlite3.OperationalError:
            consult_rows = []
        for row_id, source, page_mode, raw_json in consult_rows:
            stats["consult_scanned"] += 1
            new_source, new_mode = _normalize_row(source, page_mode, raw_json)
            if new_source != str(source or "") or new_mode != str(page_mode or ""):
                stats["consult_updated"] += 1
                if not dry_run:
                    conn.execute(
                        "UPDATE consult_requests SET source=?, page_mode=? WHERE id=?",
                        (new_source, new_mode, int(row_id)),
                    )

        try:
            usage_rows = conn.execute(
                """
                SELECT id, COALESCE(source, ''), COALESCE(page_mode, ''), COALESCE(raw_json, '')
                FROM usage_events
                """
            ).fetchall()
        except sqlite3.OperationalError:
            usage_rows = []
        for row_id, source, page_mode, raw_json in usage_rows:
            stats["usage_scanned"] += 1
            new_source, new_mode = _normalize_row(source, page_mode, raw_json)
            if new_source != str(source or "") or new_mode != str(page_mode or ""):
                stats["usage_updated"] += 1
                if not dry_run:
                    conn.execute(
                        "UPDATE usage_events SET source=?, page_mode=? WHERE id=?",
                        (new_source, new_mode, int(row_id)),
                    )

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize legacy page_mode/source taxonomy in consult API SQLite DB.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stats = migrate(Path(str(args.db)).resolve(), dry_run=bool(args.dry_run))
    print(json.dumps({"ok": True, "dry_run": bool(args.dry_run), **stats}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
