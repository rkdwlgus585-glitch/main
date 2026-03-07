import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_REL = "snapshots/co_global_banner_baseline_1.html"
META_REL = "snapshots/co_global_banner_baseline_1.meta.json"


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
        description="Rollback co_global_banner to fixed Baseline-1 snapshot."
    )
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--confirm-live", default="", help="실반영 승인 토큰 (YES)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-modified-snapshot", action="store_true")
    parser.add_argument("--report", default="logs/co_global_banner_rollback_baseline1_latest.json")
    args = parser.parse_args()

    snapshot = (ROOT / SNAPSHOT_REL).resolve()
    meta_path = (ROOT / META_REL).resolve()
    if not snapshot.exists():
        raise SystemExit(f"baseline snapshot not found: {snapshot}")
    if not meta_path.exists():
        raise SystemExit(f"baseline meta not found: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected = str(meta.get("sha256", "")).strip().lower()
    actual = _sha256(snapshot).lower()
    if expected and expected != actual and not args.allow_modified_snapshot:
        raise SystemExit(
            "baseline snapshot hash mismatch. "
            "refuse rollback for safety. "
            "If intentional, re-freeze baseline or use --allow-modified-snapshot."
        )

    cmd = [
        sys.executable,
        str((ROOT / "scripts" / "apply_co_global_banner_admin.py").resolve()),
        "--base-url",
        str(args.base_url).strip(),
        "--snippet-file",
        SNAPSHOT_REL,
        "--confirm-live",
        str(args.confirm_live).strip(),
        "--report",
        str(args.report).strip(),
    ]
    if bool(args.force):
        cmd.append("--force")

    print("[baseline-1] snapshot:", snapshot)
    print("[baseline-1] sha256:", actual)
    print("[run]", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(ROOT))
    return int(res.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

