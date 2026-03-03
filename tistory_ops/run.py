#!/usr/bin/env python3
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
    print(" SeoulMNA Tistory Ops Runner")
    print("=" * 64)
    print("python tistory_ops/run.py [command] [extra args]")
    print("")
    print("Commands:")
    print("  publish-listing      Publish listing table post to tistory (browser automation)")
    print("  daily-once           Publish one listing/day from sheet (sequential; start 7540)")
    print("  publish-listing-api  Publish listing via Open API (legacy/diagnostic)")
    print("  categories-api       List tistory categories via Open API")
    print("  posts-api            List recent tistory posts via Open API")
    print("  info-api             Show tistory blog info via Open API")
    print("  oauth               OAuth helper (authorize URL / token exchange)")
    print("  verify-split        Verify isolation from legacy flows")
    print("  help                Show this help")
    print("")
    print("Note:")
    print("  Tistory Open API is legacy/deprecated. Use publish-listing as default.")
    print("")
    print("Examples:")
    print("  python tistory_ops/run.py categories-api")
    print("  python tistory_ops/run.py oauth authorize-url")
    print("  python tistory_ops/run.py publish-listing --registration 7540 --dry-run --out-html output/tistory_7540.html")
    print("  python tistory_ops/run.py daily-once --start-registration 7540")
    print("  python tistory_ops/run.py verify-split --out logs/tistory_split_verify_latest.json")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"help", "-h", "--help"}:
        _print_help()
        return 0

    command = sys.argv[1]
    extra = sys.argv[2:]

    if command == "publish-listing":
        return _run_python("publish_browser.py", extra)
    if command == "daily-once":
        return _run_python("daily_publish.py", extra)
    if command == "publish-listing-api":
        return _run_python("publish_listing.py", extra)
    if command == "categories-api":
        return _run_python("tistory_admin.py", ["categories", *extra])
    if command == "posts-api":
        return _run_python("tistory_admin.py", ["posts", *extra])
    if command == "info-api":
        return _run_python("tistory_admin.py", ["info", *extra])
    if command == "oauth":
        return _run_python("oauth_helper.py", extra)
    if command == "verify-split":
        return _run_python("verify_tistory_split.py", extra)

    print(f"Unknown command: {command}")
    _print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
