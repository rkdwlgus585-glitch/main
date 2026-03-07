from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class MappingBatch:
    batch_id: str
    major_code: str
    major_name: str
    batch_index: int
    item_count: int
    service_codes: tuple[str, ...]


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _is_pending_row(row: Dict[str, Any]) -> bool:
    status = _normalize_text(row.get("collection_status")).lower()
    return status not in {"criteria_extracted", "mapped", "done"}


def _chunk(rows: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    step = max(1, int(size))
    for idx in range(0, len(rows), step):
        yield rows[idx : idx + step]


def apply_mapping_pipeline(
    industries: Iterable[Dict[str, Any]],
    *,
    batch_size: int = 12,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    pending_by_major: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    major_names: Dict[str, str] = {}

    for row in list(industries or []):
        if not isinstance(row, dict):
            continue
        copied = dict(row)
        major_code = _normalize_text(copied.get("major_code"))
        major_name = _normalize_text(copied.get("major_name"))
        if major_code:
            major_names.setdefault(major_code, major_name)
        copied["mapping_group_key"] = major_code
        if _is_pending_row(copied):
            pending_by_major[major_code].append(copied)
        else:
            copied["mapping_status"] = "mapped"
            copied["mapping_batch_id"] = ""
            copied["mapping_batch_seq"] = 0
        updated.append(copied)

    batches: List[MappingBatch] = []
    pending_lookup: Dict[str, Tuple[str, int]] = {}
    batch_count_by_major: Dict[str, int] = defaultdict(int)

    for major_code in sorted(pending_by_major.keys()):
        rows = pending_by_major[major_code]
        rows.sort(
            key=lambda x: (
                _normalize_text(x.get("service_code")),
                _normalize_text(x.get("service_name")),
            )
        )
        major_name = major_names.get(major_code, "")
        for chunk_idx, chunk_rows in enumerate(_chunk(rows, batch_size), 1):
            batch_count_by_major[major_code] += 1
            batch_id = f"M{major_code or '00'}-B{chunk_idx:02d}"
            service_codes: List[str] = []
            for seq, row in enumerate(chunk_rows, 1):
                code = _normalize_text(row.get("service_code"))
                service_codes.append(code)
                pending_lookup[code] = (batch_id, seq)
            batches.append(
                MappingBatch(
                    batch_id=batch_id,
                    major_code=major_code,
                    major_name=major_name,
                    batch_index=chunk_idx,
                    item_count=len(chunk_rows),
                    service_codes=tuple(service_codes),
                )
            )

    for row in updated:
        if not _is_pending_row(row):
            continue
        code = _normalize_text(row.get("service_code"))
        batch_info = pending_lookup.get(code)
        if batch_info is None:
            row["mapping_status"] = "pending_unassigned"
            row["mapping_batch_id"] = ""
            row["mapping_batch_seq"] = 0
            continue
        batch_id, seq = batch_info
        row["mapping_status"] = "queued_law_mapping"
        row["mapping_batch_id"] = batch_id
        row["mapping_batch_seq"] = int(seq)

    pending_total = sum(1 for row in updated if _is_pending_row(row))
    mapped_total = sum(1 for row in updated if not _is_pending_row(row))
    major_groups = sorted(
        [
            {
                "major_code": code,
                "major_name": major_names.get(code, ""),
                "pending_count": len(pending_by_major.get(code) or []),
                "batch_count": int(batch_count_by_major.get(code, 0)),
            }
            for code in pending_by_major.keys()
        ],
        key=lambda x: (str(x.get("major_code", "")), str(x.get("major_name", ""))),
    )

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "batch_size": max(1, int(batch_size)),
        "pending_total": int(pending_total),
        "mapped_total": int(mapped_total),
        "major_group_total": len(major_groups),
        "batch_total": len(batches),
        "major_groups": major_groups,
        "batches": [
            {
                "batch_id": batch.batch_id,
                "major_code": batch.major_code,
                "major_name": batch.major_name,
                "batch_index": int(batch.batch_index),
                "item_count": int(batch.item_count),
                "service_codes": list(batch.service_codes),
            }
            for batch in batches
        ],
    }
    return updated, meta
