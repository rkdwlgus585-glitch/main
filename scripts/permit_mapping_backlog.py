#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator as permit


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _build_pending_rows(criteria: Dict[str, Any], top_n: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in list(criteria.get("industries") or []):
        if not isinstance(row, dict):
            continue
        status = _normalize_text(row.get("collection_status"))
        if status not in {"pending_law_mapping", "pending"}:
            continue
        detail_url = _normalize_text(row.get("detail_url"))
        name = _normalize_text(row.get("service_name"))
        major = _normalize_text(row.get("major_name"))
        score = 0
        if detail_url:
            score += 30
        if major in {"건설", "전기", "소방", "정보통신"}:
            score += 25
        if "공사업" in name or "건설" in name:
            score += 20
        if "시설" in name or "설비" in name:
            score += 10
        rows.append(
            {
                "service_code": _normalize_text(row.get("service_code")),
                "service_name": name,
                "major_code": _normalize_text(row.get("major_code")),
                "major_name": major,
                "collection_status": status,
                "priority_score": score,
                "detail_url": detail_url,
            }
        )
    rows.sort(key=lambda x: (-int(x.get("priority_score", 0)), str(x.get("major_code", "")), str(x.get("service_name", ""))))
    return rows[: max(1, int(top_n))]


def _build_pending_groups(criteria: Dict[str, Any], top_n: int) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for row in list(criteria.get("industries") or []):
        if not isinstance(row, dict):
            continue
        status = _normalize_text(row.get("collection_status")).lower()
        if status in {"criteria_extracted", "mapped", "done"}:
            continue
        major_code = _normalize_text(row.get("major_code"))
        major_name = _normalize_text(row.get("major_name"))
        key = major_code or "00"
        if key not in groups:
            groups[key] = {
                "major_code": key,
                "major_name": major_name,
                "pending_count": 0,
                "sample_service_codes": [],
            }
        groups[key]["pending_count"] += 1
        sample = groups[key]["sample_service_codes"]
        code = _normalize_text(row.get("service_code"))
        if code and len(sample) < 5:
            sample.append(code)
    rows = list(groups.values())
    rows.sort(key=lambda x: (-int(x.get("pending_count", 0)), str(x.get("major_code", ""))))
    return rows[: max(1, int(top_n))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Print permit legal-mapping backlog (no file write)")
    parser.add_argument(
        "--criteria",
        default=str(ROOT / "config" / "permit_registration_criteria_expanded.json"),
        help="criteria expanded json path",
    )
    parser.add_argument("--top", type=int, default=40, help="top pending rows to print")
    parser.add_argument("--group-top", type=int, default=20, help="top pending major groups to print")
    parser.add_argument("--json", action="store_true", help="json output only")
    args = parser.parse_args()

    criteria_path = Path(str(args.criteria)).expanduser().resolve()
    criteria = _load_json(criteria_path)
    summary = dict(criteria.get("summary") or {})

    industry_total = int(summary.get("industry_total") or 0)
    extracted = int(summary.get("criteria_extracted_industry_total") or 0)
    pending = int(summary.get("pending_industry_total") or 0)
    coverage_pct = round((extracted / industry_total * 100.0), 2) if industry_total > 0 else 0.0

    backlog = _build_pending_rows(criteria, top_n=int(args.top))
    pending_groups = _build_pending_groups(criteria, top_n=int(args.group_top))
    mapping_pipeline = dict(criteria.get("mapping_pipeline") or {})
    mapping_pipeline_summary = {
        "batch_total": int(mapping_pipeline.get("batch_total") or 0),
        "major_group_total": int(mapping_pipeline.get("major_group_total") or 0),
        "batch_size": int(mapping_pipeline.get("batch_size") or 0),
        "generated_at": _normalize_text(mapping_pipeline.get("generated_at")),
    }
    payload = {
        "criteria_path": str(criteria_path),
        "industry_total": industry_total,
        "criteria_extracted_industry_total": extracted,
        "pending_industry_total": pending,
        "coverage_pct": coverage_pct,
        "pending_groups": pending_groups,
        "mapping_pipeline": mapping_pipeline_summary,
        "top_pending": backlog,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("=== Permit Mapping Backlog ===")
    print(
        f"coverage={coverage_pct:.2f}% "
        f"(extracted={extracted}/{industry_total}, pending={pending})"
    )
    if mapping_pipeline_summary["batch_total"] > 0:
        print(
            f"pipeline=batch_total:{mapping_pipeline_summary['batch_total']} "
            f"major_groups:{mapping_pipeline_summary['major_group_total']} "
            f"batch_size:{mapping_pipeline_summary['batch_size']}"
        )
    print("\n-- Pending Groups --")
    for idx, group in enumerate(pending_groups, 1):
        print(
            f"{idx:02d}. [{group['pending_count']:03d}] {group['major_code']} {group['major_name']} "
            f"samples={','.join(group['sample_service_codes'])}"
        )
    print("\n-- Pending Rows --")
    for idx, row in enumerate(backlog, 1):
        print(
            f"{idx:02d}. [{row['priority_score']:02d}] {row['major_name']} / {row['service_name']} "
            f"({row['service_code']})"
        )
    print("\n-- JSON --")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
