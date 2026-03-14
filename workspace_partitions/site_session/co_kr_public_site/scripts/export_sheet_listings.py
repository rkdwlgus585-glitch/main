#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "imported" / "listing-sheet-rows.json"


def resolve_all_root() -> Path:
    override = os.environ.get("SEOULMNA_ALL_ROOT", "").strip()
    if override:
        candidate = Path(override).expanduser().resolve()
        if (candidate / "all.py").exists():
            return candidate

    candidates: list[Path] = []
    for parent in PROJECT_ROOT.parents:
        candidates.append(parent / "ALL")
        if parent.parent != parent:
            candidates.append(parent.parent / "ALL")

    project_drive_root = Path(PROJECT_ROOT.anchor)
    candidates.append(project_drive_root / "ALL")

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "all.py").exists():
            return candidate

    raise RuntimeError(
        "Unable to locate ALL/all.py. Set SEOULMNA_ALL_ROOT to the directory that contains all.py.",
    )


ALL_ROOT = resolve_all_root()


def resolve_auto_root() -> Path:
    override = os.environ.get("SEOULMNA_AUTO_ROOT", "").strip()
    if override:
        candidate = Path(override).expanduser().resolve()
        if candidate.exists():
            return candidate

    for parent in PROJECT_ROOT.parents:
        if parent.name.lower() == "auto":
            return parent

    fallback = ALL_ROOT.parent / "auto"
    if fallback.exists():
        return fallback

    return PROJECT_ROOT


AUTO_ROOT = resolve_auto_root()

if str(ALL_ROOT) not in sys.path:
    sys.path.insert(0, str(ALL_ROOT))

import all as allmod  # noqa: E402


def clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", "\n").split()).strip()


def split_multiline(value: str) -> list[str]:
    parts: list[str] = []
    seen: set[str] = set()
    for chunk in str(value or "").replace("\r", "\n").split("\n"):
        text = clean(chunk)
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return parts


def extract_uid(row: list[str]) -> str:
    for idx in (34, 33, 32):
        text = clean(row[idx]) if len(row) > idx else ""
        match = re.match(r"^(\d{4,5})", text)
        if match:
            return match.group(1)
    return ""


def derive_base_listing_id(row: list[str]) -> tuple[str, str, str]:
    sheet_no = clean(row[0]) if len(row) > 0 else ""
    uid = extract_uid(row)
    return sheet_no or uid, sheet_no, uid


def build_unique_listing_ids(rows: list[list[str]]) -> dict[int, str]:
    base_records: list[tuple[int, str, str]] = []
    base_counts: dict[str, int] = {}

    for row_index, row in enumerate(rows, start=2):
        if not any(clean(cell) for cell in row):
            continue
        base_id, _sheet_no, uid = derive_base_listing_id(row)
        if not base_id:
            continue
        base_records.append((row_index, base_id, uid))
        base_counts[base_id] = base_counts.get(base_id, 0) + 1

    resolved_candidates: list[tuple[int, str]] = []
    candidate_counts: dict[str, int] = {}
    for row_index, base_id, uid in base_records:
        candidate = base_id
        if base_counts.get(base_id, 0) > 1 and uid and uid != base_id:
            candidate = f"{base_id}-{uid}"
        resolved_candidates.append((row_index, candidate))
        candidate_counts[candidate] = candidate_counts.get(candidate, 0) + 1

    occurrence_counts: dict[str, int] = {}
    listing_ids: dict[int, str] = {}
    for row_index, candidate in resolved_candidates:
        listing_id = candidate
        if candidate_counts.get(candidate, 0) > 1:
            next_occurrence = occurrence_counts.get(candidate, 0) + 1
            occurrence_counts[candidate] = next_occurrence
            listing_id = f"{candidate}-{next_occurrence}"
        listing_ids[row_index] = listing_id

    return listing_ids


def load_sheet_values() -> list[list[str]]:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_file = Path(allmod.JSON_FILE)
    if not json_file.is_absolute():
        auto_candidate = (AUTO_ROOT / json_file).resolve()
        project_candidate = (PROJECT_ROOT / json_file).resolve()
        if auto_candidate.exists():
            json_file = auto_candidate
        elif project_candidate.exists():
            json_file = project_candidate
        else:
            json_file = auto_candidate
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(json_file), scope)
    client = gspread.authorize(creds)
    worksheet = client.open(allmod.SHEET_NAME).sheet1
    return worksheet.get_all_values()


def row_to_record(row: list[str], row_index: int, generated_at: str, *, listing_id: str) -> dict[str, Any] | None:
    item = allmod._sheet_row_to_listing_item(row)
    uid = clean(item.get("uid", "")) or extract_uid(row)
    if not listing_id:
        return None
    sheet_no = clean(allmod._row_text(row, 0))

    sectors = split_multiline(item.get("license", ""))
    license_years = split_multiline(item.get("license_year", ""))
    capacity_values = split_multiline(item.get("specialty", ""))
    performance3_values = split_multiline(allmod._row_text(row, 10))
    performance5_values = split_multiline(allmod._row_text(row, 11))
    performance2025_values = split_multiline(item.get("y25", ""))
    status = clean(allmod._normalize_sync_status_label(allmod._row_text(row, 1))) or "검토중"
    sector_label = " · ".join(sectors) if sectors else "건설업"

    return {
        "id": listing_id,
        "sourceUid": uid,
        "rowIndex": row_index,
        "sheetNo": sheet_no,
        "updatedAt": generated_at,
        "status": status,
        "sectors": sectors,
        "sectorLabel": sector_label,
        "licenseYears": license_years,
        "capacityValues": capacity_values,
        "performance3Values": performance3_values,
        "performance5Values": performance5_values,
        "performance2025Values": performance2025_values,
        "region": clean(item.get("location", "")),
        "companyType": clean(item.get("company_type", "")),
        "companyYear": clean(item.get("founded_year", "")),
        "shares": clean(item.get("shares", "")),
        "associationMembership": clean(item.get("association", "")),
        "capital": clean(item.get("capital", "")),
        "balance": clean(item.get("balance", "")),
        "price": clean(item.get("sheet_price", "") or item.get("price", "")) or "협의",
        "claimPrice": clean(item.get("sheet_claim_price", "") or item.get("claim_price", "")),
        "memo": clean(item.get("memo", "")),
        "debtRatio": clean(item.get("debt_ratio", "")),
        "liquidityRatio": clean(item.get("liquidity_ratio", "")),
        "surplus": clean(item.get("surplus", "")),
        "priceTraceSummary": clean(item.get("price_trace_summary", "")),
        "priceSource": clean(item.get("price_source", "")),
        "priceEvidence": clean(item.get("price_evidence", "")),
        "priceConfidence": clean(item.get("price_confidence", "")),
        "priceFallback": clean(item.get("price_fallback", "")),
        "sourceUrl": f"/mna/{listing_id}",
        "sourceNowmnaUrl": clean(item.get("source_url", "")),
    }


def sort_key(record: dict[str, Any]) -> tuple[int, str]:
    raw_id = clean(record.get("id", ""))
    match = re.match(r"^(\d+)", raw_id)
    if match:
        return (-int(match.group(1)), raw_id)
    return (0, raw_id)


def main() -> int:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    values = load_sheet_values()
    rows = values[1:] if len(values) > 1 else []
    listing_ids = build_unique_listing_ids(rows)
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []

    for row_index, row in enumerate(rows, start=2):
        if not any(clean(cell) for cell in row):
            continue
        record = row_to_record(
            row,
            row_index,
            generated_at,
            listing_id=listing_ids.get(row_index, ""),
        )
        if not record:
            continue
        listing_id = str(record["id"])
        if listing_id in seen_ids:
            duplicate_ids.append(listing_id)
        seen_ids.add(listing_id)
        records.append(record)

    records = sorted(records, key=sort_key)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH),
                "generatedAt": generated_at,
                "sheetName": allmod.SHEET_NAME,
                "rowsSeen": len(rows),
                "recordsWritten": len(records),
                "duplicateIds": sorted(set(duplicate_ids)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
