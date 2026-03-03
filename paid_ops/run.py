#!/usr/bin/env python3
"""
Isolated launcher for paid/new-business automation commands.

This file intentionally keeps paid workflows separate from legacy run.py.
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
    print(" SeoulMNA Paid Ops Runner")
    print("=" * 64)
    print("python paid_ops/run.py [command] [extra args]")
    print("")
    print("Commands:")
    print("  gabji-report    Build paid diagnostic report PDF")
    print("  gb2-audit       Audit gb2_v3/gabji backend integration")
    print("  verify-split    Verify paid/legacy isolation contracts")
    print("  help            Show this help")
    print("")
    print("Examples:")
    print("  python paid_ops/run.py gb2-audit")
    print("  python paid_ops/run.py gabji-report --registration 7737 --output output/7737_report.pdf")
    print("  python paid_ops/run.py verify-split")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"help", "-h", "--help"}:
        _print_help()
        return 0

    command = sys.argv[1]
    extra = sys.argv[2:]

    if command == "gabji-report":
        return _run_python("build_gabji_analysis_report.py", extra)
    if command == "gb2-audit":
        return _run_python("audit_gb2_v3_integration.py", extra)
    if command == "verify-split":
        return _run_python("verify_paid_legacy_split.py", extra)

    print(f"Unknown command: {command}")
    _print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
