#!/usr/bin/env python3
"""산출물 스키마 회귀 체크."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
RESULT_DIR = BASE_DIR / "result"
FIXTURE = BASE_DIR / "fixtures" / "g2b_schema_expectation.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_file(pattern: str):
    files = sorted(RESULT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def parse_args():
    p = argparse.ArgumentParser(description="Check exported schema against fixtures.")
    p.add_argument(
        "--strict-matched",
        action="store_true",
        help="Fail when matched output is missing or empty.",
    )
    return p.parse_args()


def main(strict_matched: bool = False) -> int:
    if not FIXTURE.exists():
        print(f"[ERR] fixture missing: {FIXTURE}")
        return 1
    fixture = load_json(FIXTURE)

    all_path = RESULT_DIR / "latest_all.json"
    summary_path = RESULT_DIR / "latest_summary.json"
    matched_path = RESULT_DIR / "latest_matched.json"
    if not matched_path.exists():
        matched_path = latest_file("G2B_Matched_*.json")

    errors = []
    warnings = []

    if not all_path.exists():
        errors.append(f"latest_all.json missing: {all_path}")
    if not summary_path.exists():
        errors.append(f"latest_summary.json missing: {summary_path}")

    if errors:
        for e in errors:
            print(f"[ERR] {e}")
        return 1

    all_data = load_json(all_path)
    summary = load_json(summary_path)
    matched = load_json(matched_path) if matched_path and matched_path.exists() else []

    if not isinstance(all_data, list) or not all_data:
        errors.append("all_data is empty")
    else:
        keys = set(all_data[0].keys())
        for req in fixture.get("all_required_fields", []):
            if req not in keys:
                errors.append(f"missing field in all_data: {req}")

    if "quality" not in summary:
        errors.append("summary missing quality")
    if "counts" not in summary:
        errors.append("summary missing counts")

    if matched:
        keys = set(matched[0].keys())
        for req in fixture.get("matched_required_fields", []):
            if req not in keys:
                errors.append(f"missing field in matched: {req}")
    else:
        msg = "matched data not found or empty"
        if strict_matched:
            errors.append(msg)
        else:
            warnings.append(msg)

    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        for e in errors:
            print(f"[ERR] {e}")
        return 1

    print("[OK] regression check passed")
    print(f"  all: {all_path}")
    print(f"  summary: {summary_path}")
    if matched_path:
        print(f"  matched: {matched_path}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main(strict_matched=args.strict_matched))
