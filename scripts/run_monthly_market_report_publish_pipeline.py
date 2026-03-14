#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_JSON = ROOT / "logs" / "monthly_notice_keyword_report_latest.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "monthly_market_report"
DEFAULT_STATE_FILE = ROOT / "logs" / "monthly_market_report_publish_state.json"
DEFAULT_REVIEW_JSON = ROOT / "logs" / "monthly_market_report_review_latest.json"
DEFAULT_REVIEW_MD = ROOT / "logs" / "monthly_market_report_review_latest.md"


def _month_key(now: datetime) -> str:
    return f"{now.year:04d}-{now.month:02d}"


def _parse_month_key(month_key: str) -> tuple[int, int]:
    txt = str(month_key or "").strip()
    if not txt or "-" not in txt:
        now = datetime.now()
        return now.year, now.month
    year_txt, month_txt = txt.split("-", 1)
    return int(year_txt), int(month_txt)


def _run_command(args: list[str]) -> int:
    return subprocess.call(args, cwd=str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run build/publish pipeline for monthly market report.")
    parser.add_argument("--month-key", default="", help="Override target month key (YYYY-MM).")
    parser.add_argument("--report-json", default=str(DEFAULT_SOURCE_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    parser.add_argument("--review-report-json", default=str(DEFAULT_REVIEW_JSON))
    parser.add_argument("--review-report-md", default=str(DEFAULT_REVIEW_MD))
    parser.add_argument("--discover-pages", type=int, default=5)
    parser.add_argument("--write-buffer", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_month = str(args.month_key or "").strip() or _month_key(datetime.now())
    year, month = _parse_month_key(target_month)
    py = sys.executable

    build_cmd = [
        py,
        str(ROOT / "scripts" / "build_monthly_market_report_html.py"),
        "--year",
        str(year),
        "--month",
        str(month),
        "--report-json",
        str(args.report_json),
        "--output-dir",
        str(args.output_dir),
    ]
    publish_cmd = [
        py,
        str(ROOT / "scripts" / "publish_monthly_market_report.py"),
        "--year",
        str(year),
        "--month",
        str(month),
        "--output-dir",
        str(args.output_dir),
        "--state-file",
        str(args.state_file),
        "--review-report-json",
        str(args.review_report_json),
        "--review-report-md",
        str(args.review_report_md),
        "--discover-pages",
        str(int(args.discover_pages)),
        "--write-buffer",
        str(int(args.write_buffer)),
    ]

    print(f"[pipeline] target_month={target_month}")
    build_rc = _run_command(build_cmd)
    if build_rc != 0:
        print(f"[fail] build rc={build_rc}")
        return build_rc

    publish_rc = _run_command(publish_cmd)
    print(f"[publish] rc={publish_rc}")
    return publish_rc


if __name__ == "__main__":
    raise SystemExit(main())