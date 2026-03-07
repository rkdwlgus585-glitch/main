#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core_engine.permit_mapping_pipeline import apply_mapping_pipeline


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply major-group split batches to permit mapping backlog and write into criteria json.",
    )
    parser.add_argument(
        "--criteria",
        default=str(ROOT / "config" / "permit_registration_criteria_expanded.json"),
        help="permit criteria expanded json path",
    )
    parser.add_argument(
        "--output",
        default="",
        help="optional output path; default overwrites --criteria",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=12,
        help="pending rows per mapping batch",
    )
    args = parser.parse_args()

    criteria_path = Path(str(args.criteria)).expanduser().resolve()
    output_path = Path(str(args.output)).expanduser().resolve() if str(args.output or "").strip() else criteria_path
    payload = _load_json(criteria_path)

    industries = list(payload.get("industries") or [])
    updated, mapping_meta = apply_mapping_pipeline(industries, batch_size=max(1, int(args.batch_size)))
    payload["industries"] = updated
    payload["mapping_pipeline"] = mapping_meta

    summary = dict(payload.get("summary") or {})
    summary["industry_total"] = _coerce_int(summary.get("industry_total"), len(updated))
    summary["pending_industry_total"] = _coerce_int(mapping_meta.get("pending_total"), 0)
    summary["criteria_extracted_industry_total"] = _coerce_int(mapping_meta.get("mapped_total"), 0)
    summary["mapping_major_group_total"] = _coerce_int(mapping_meta.get("major_group_total"), 0)
    summary["mapping_batch_total"] = _coerce_int(mapping_meta.get("batch_total"), 0)
    summary["mapping_batch_size"] = _coerce_int(mapping_meta.get("batch_size"), max(1, int(args.batch_size)))
    summary["mapping_pipeline_generated_at"] = str(mapping_meta.get("generated_at") or "")
    payload["summary"] = summary

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "criteria_path": str(criteria_path),
                "output_path": str(output_path),
                "pending_total": mapping_meta.get("pending_total"),
                "major_group_total": mapping_meta.get("major_group_total"),
                "batch_total": mapping_meta.get("batch_total"),
                "batch_size": mapping_meta.get("batch_size"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
