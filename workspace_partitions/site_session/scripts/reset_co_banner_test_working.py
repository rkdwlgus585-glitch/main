import argparse
import hashlib
import json
import os
import stat
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset test working snippet from baseline-1."
    )
    parser.add_argument("--baseline-file", default="snapshots/co_global_banner_baseline_1.html")
    parser.add_argument("--working-file", default="snapshots/co_global_banner_test_working.html")
    parser.add_argument("--report", default="logs/co_global_banner_test_reset_latest.json")
    args = parser.parse_args()

    baseline = (ROOT / str(args.baseline_file)).resolve()
    working = (ROOT / str(args.working_file)).resolve()
    report_path = (ROOT / str(args.report)).resolve()

    if not baseline.exists():
        raise SystemExit(f"baseline not found: {baseline}")

    working.parent.mkdir(parents=True, exist_ok=True)
    if working.exists():
        try:
            os.chmod(str(working), stat.S_IWRITE | stat.S_IREAD)
        except Exception:
            pass
    working.write_bytes(baseline.read_bytes())

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": True,
        "baseline": str(baseline).replace("\\", "/"),
        "working": str(working).replace("\\", "/"),
        "working_sha256": _sha256(working),
        "working_bytes": int(working.stat().st_size),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[reset] done")
    print("[working]", working)
    print("[report]", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
