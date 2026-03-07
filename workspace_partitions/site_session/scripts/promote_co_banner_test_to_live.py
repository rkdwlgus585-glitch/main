import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote tested co banner working snippet to live co.kr."
    )
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--snippet-file", default="snapshots/co_global_banner_test_working.html")
    parser.add_argument("--confirm-live", default="", help="실반영 승인 토큰 (YES)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report", default="logs/co_global_banner_promote_test_latest.json")
    args = parser.parse_args()

    snippet = (ROOT / str(args.snippet_file)).resolve()
    if not snippet.exists():
        raise SystemExit(f"snippet file not found: {snippet}")

    cmd = [
        sys.executable,
        str((ROOT / "scripts" / "apply_co_global_banner_admin.py").resolve()),
        "--base-url",
        str(args.base_url).strip(),
        "--snippet-file",
        str(args.snippet_file).strip(),
        "--confirm-live",
        str(args.confirm_live).strip(),
        "--report",
        str(args.report).strip(),
    ]
    if bool(args.force):
        cmd.append("--force")

    print("[promote] snippet:", snippet)
    print("[run]", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(ROOT))
    return int(res.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

