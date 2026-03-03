import argparse
import shlex
import subprocess
import sys
from datetime import datetime


def _run(cmd):
    print(f"\n$ {' '.join(shlex.quote(c) for c in cmd)}")
    started = datetime.now()
    result = subprocess.run(cmd, check=False)
    ended = datetime.now()
    elapsed = (ended - started).total_seconds()
    print(f"-> exit={result.returncode} ({elapsed:.1f}s)")
    return result.returncode


def _build_parser():
    p = argparse.ArgumentParser(description="Sales pipeline runner: match -> listing recommendation -> quote")
    p.add_argument("--lead-id", default="", help="lead id from 상담관리")
    p.add_argument("--consult-row", type=int, default=0, help="row number in 상담관리")
    p.add_argument("--top", type=int, default=5, help="top listings for recommendation")

    p.add_argument("--run-match", action="store_true", help="run match.py before recommendation")
    p.add_argument("--skip-recommend", action="store_true", help="skip listing_matcher.py")
    p.add_argument("--skip-quote", action="store_true", help="skip quote_engine.py")
    p.add_argument("--dry-run", action="store_true", help="dry-run mode for downstream scripts")
    p.add_argument("--no-files", action="store_true", help="skip file outputs where supported")
    p.add_argument("--no-sheet", action="store_true", help="skip sheet writes where supported")
    return p


def main():
    args = _build_parser().parse_args()
    py = sys.executable

    codes = {}

    if args.run_match:
        codes["match"] = _run([py, "match.py"])

    if not args.skip_recommend:
        cmd = [py, "listing_matcher.py", "--top", str(max(1, args.top))]
        if args.lead_id:
            cmd += ["--lead-id", args.lead_id]
        if args.consult_row > 0:
            cmd += ["--consult-row", str(args.consult_row)]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.no_files:
            cmd.append("--no-files")
        if args.no_sheet:
            cmd.append("--no-sheet")
        codes["recommend"] = _run(cmd)

    if not args.skip_quote:
        cmd = [py, "quote_engine.py"]
        if args.lead_id:
            cmd += ["--lead-id", args.lead_id]
        if args.consult_row > 0:
            cmd += ["--consult-row", str(args.consult_row)]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.no_files:
            cmd.append("--no-files")
        if args.no_sheet:
            cmd.append("--no-sheet")
        codes["quote"] = _run(cmd)

    print("\n" + "=" * 62)
    print("pipeline summary")
    for k, v in codes.items():
        print(f"- {k}: exit={v}")
    print("=" * 62)

    if any(v != 0 for v in codes.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
