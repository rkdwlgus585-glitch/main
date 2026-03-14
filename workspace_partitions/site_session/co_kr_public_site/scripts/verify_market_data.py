#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORTED_DIR = PROJECT_ROOT / "data" / "imported"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    legacy_summaries = read_json(IMPORTED_DIR / "listing-summaries.json")
    sheet_rows = read_json(IMPORTED_DIR / "listing-sheet-rows.json")

    legacy_ids = {str(item["id"]).strip() for item in legacy_summaries}
    sheet_ids = [str(item["id"]).strip() for item in sheet_rows]
    unique_sheet_ids = set(sheet_ids)
    duplicate_sheet_ids = sorted({item_id for item_id in sheet_ids if sheet_ids.count(item_id) > 1})

    errors: list[str] = []
    if len(sheet_ids) != len(unique_sheet_ids):
        errors.append(f"duplicate sheet listing ids detected: {', '.join(duplicate_sheet_ids[:20])}")

    stats = {
        "legacyImportedCount": len(legacy_ids),
        "sheetCount": len(unique_sheet_ids),
        "sheetOnlyCount": len(unique_sheet_ids - legacy_ids),
        "legacyOnlyCount": len(legacy_ids - unique_sheet_ids),
        "mergedCount": len(legacy_ids | unique_sheet_ids),
    }

    if stats["sheetCount"] == 0:
        errors.append("sheet export is empty")
    if stats["mergedCount"] < stats["sheetCount"]:
        errors.append("merged count cannot be smaller than sheet count")

    if errors:
        raise SystemExit("\n".join(errors))

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
