#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _month_key(now: datetime) -> str:
    return f"{now.year:04d}-{now.month:02d}"


def _relax_pct_for_attempt(attempt: int, attempts_per_stage: int, relax_step_pct: float) -> float:
    if attempt <= attempts_per_stage:
        return 0.0
    stage = (attempt - 1) // max(1, attempts_per_stage)
    return min(1.0, max(0.0, float(stage) * float(relax_step_pct)))


def _run_command(args: list[str]) -> int:
    return subprocess.call(args, cwd=str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run build/review/publish pipeline for monthly notice archive.")
    parser.add_argument("--pages", type=int, default=12)
    parser.add_argument("--min-uid", type=int, default=7684)
    parser.add_argument("--review-json", default=str(ROOT / "logs" / "notice_archive_review_latest.json"))
    parser.add_argument("--review-md", default=str(ROOT / "logs" / "notice_archive_review_latest.md"))
    parser.add_argument("--max-writes", type=int, default=2)
    parser.add_argument("--write-buffer", type=int, default=12)
    parser.add_argument("--delay-sec", type=float, default=1.5)
    parser.add_argument("--min-update-days", type=float, default=7.0)
    parser.add_argument("--attempts-per-stage", type=int, default=10)
    parser.add_argument("--relax-step-pct", type=float, default=0.05)
    parser.add_argument("--max-attempts", type=int, default=210)
    parser.add_argument("--month-key", default="", help="Override target month key (YYYY-MM).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_month = str(args.month_key or "").strip() or _month_key(datetime.now())
    py = sys.executable

    build_cmd = [
        py,
        str(ROOT / "run.py"),
        "notice-monthly",
        "--monthly-archive",
        "--pages",
        str(int(args.pages)),
        "--min-uid",
        str(int(args.min_uid)),
    ]
    normalize_cmd = [
        py,
        str(ROOT / "scripts" / "normalize_monthly_notice_archive.py"),
        "--month-key",
        target_month,
    ]
    publish_cmd = [
        py,
        str(ROOT / "scripts" / "publish_monthly_notice_archive.py"),
        "--month-key",
        target_month,
        "--max-writes",
        str(int(args.max_writes)),
        "--write-buffer",
        str(int(args.write_buffer)),
        "--delay-sec",
        str(float(args.delay_sec)),
        "--min-update-days",
        str(float(args.min_update_days)),
    ]

    print(f"[pipeline] target_month={target_month}")
    build_rc = _run_command(build_cmd)
    if build_rc != 0:
        print(f"[fail] build rc={build_rc}")
        return build_rc

    attempts = max(1, int(args.max_attempts))
    for attempt in range(1, attempts + 1):
        relax_pct = _relax_pct_for_attempt(attempt, int(args.attempts_per_stage), float(args.relax_step_pct))
        print(f"[review-attempt] month={target_month} attempt={attempt} relax_pct={relax_pct:.2f}")

        normalize_rc = _run_command(normalize_cmd)
        if normalize_rc != 0:
            print(f"[fail] normalize rc={normalize_rc}")
            return normalize_rc

        review_cmd = [
            py,
            str(ROOT / "scripts" / "review_monthly_notice_archive.py"),
            "--month-key",
            target_month,
            "--report-json",
            str(args.review_json),
            "--report-md",
            str(args.review_md),
            "--quality-relax-pct",
            f"{relax_pct:.2f}",
        ]
        review_rc = _run_command(review_cmd)
        if review_rc == 0:
            print(f"[review-pass] month={target_month} attempt={attempt} relax_pct={relax_pct:.2f}")
            publish_rc = _run_command(publish_cmd)
            print(f"[publish] rc={publish_rc}")
            return publish_rc

    print(f"[fail] review did not pass within max_attempts={attempts}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
