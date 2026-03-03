#!/usr/bin/env python3
"""
Unified launcher for common automation entrypoints in this workspace.

Usage:
  python run.py help
  python run.py all
  python run.py maemul --pages 3
  python run.py notice-monthly --year 2026 --month 2 --min-uid 7684
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run_python(script: str, extra_args: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / script), *extra_args]
    return subprocess.call(cmd)


def _print_help() -> None:
    print("=" * 64)
    print(" SeoulMNA Automation Runner")
    print("=" * 64)
    print("python run.py [command] [extra args]")
    print("")
    print("Commands:")
    print("  all             Run listing collection/sync pipeline (all.py)")
    print("  maemul          Generate MNA list HTML links (maemul.py)")
    print("  match           Run consult-listing matcher (match.py)")
    print("  premium         Run premium article automation (premium_auto.py)")
    print("  blog-cli        Run blog scheduler once (mnakr.py --cli)")
    print("  notice-monthly  Generate monthly notice draft HTML")
    print("  notice-archive  Refresh rolling monthly notice archive")
    print("  notice-sync     Sync monthly notice archive to seoul notice board")
    print("  help            Show this help")
    print("")
    print("Examples:")
    print("  python run.py maemul --pages 5")
    print("  python run.py notice-monthly --year 2026 --month 2 --min-uid 7684")
    print("  python run.py notice-monthly --monthly-archive --min-uid 7684")
    print("  python run.py notice-sync --dry-run")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"help", "-h", "--help"}:
        _print_help()
        return 0

    command = sys.argv[1]
    extra = sys.argv[2:]

    if command == "all":
        return _run_python("all.py", extra)
    if command == "maemul":
        return _run_python("maemul.py", extra)
    if command == "match":
        return _run_python("match.py", extra)
    if command == "premium":
        return _run_python("premium_auto.py", extra)
    if command == "blog-cli":
        return _run_python("mnakr.py", ["--cli", *extra])
    if command == "notice-monthly":
        return _run_python("scripts/build_monthly_notice_from_maemul.py", extra)
    if command == "notice-archive":
        return _run_python("scripts/build_monthly_notice_from_maemul.py", ["--monthly-archive", *extra])
    if command == "notice-sync":
        return _run_python("scripts/publish_monthly_notice_archive.py", extra)

    print(f"Unknown command: {command}")
    _print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
