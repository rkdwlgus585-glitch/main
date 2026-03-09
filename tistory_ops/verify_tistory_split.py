from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TISTORY_TOKENS = [
    "tistory_ops",
    "seoulmna.tistory.com",
    "tistory.com/apis",
]

LEGACY_ENTRY_FILES = list(ROOT.glob("*.bat")) + list((ROOT / "launchers").glob("*.bat")) + list((ROOT / "scripts").glob("*.cmd"))
ALLOWED_TISTORY_ENTRYPOINTS = {
    (ROOT / "티스토리자동발행.bat").resolve(),
    (ROOT / "launchers" / "launch_tistory_publish.bat").resolve(),
}
LEGACY_CORE_FILES = [
    ROOT / "all.py",
    ROOT / "mnakr.py",
    ROOT / "gabji.py",
    ROOT / "premium_auto.py",
    ROOT / "run.py",
    ROOT / "paid_ops" / "run.py",
]


def _read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(errors="ignore")


def _check_legacy_entries() -> dict:
    violations = []
    for path in LEGACY_ENTRY_FILES:
        try:
            if path.resolve() in ALLOWED_TISTORY_ENTRYPOINTS:
                continue
        except Exception:
            pass
        text = _read_text(path).lower()
        for token in TISTORY_TOKENS:
            if token.lower() in text:
                violations.append({"file": str(path), "token": token})
    return {
        "check": "legacy_entrypoints_do_not_reference_tistory_ops",
        "ok": len(violations) == 0,
        "violations": violations,
    }


def _check_legacy_core_imports() -> dict:
    patterns = [
        re.compile(r"\bimport\s+tistory_ops\b"),
        re.compile(r"\bfrom\s+tistory_ops\b"),
        re.compile(r"seoulmna\.tistory\.com"),
        re.compile(r"tistory\.com/apis"),
    ]
    violations = []
    for path in LEGACY_CORE_FILES:
        if not path.exists():
            continue
        text = _read_text(path)
        for pat in patterns:
            if pat.search(text):
                violations.append({"file": str(path), "pattern": pat.pattern})
    return {
        "check": "legacy_core_has_no_tistory_imports",
        "ok": len(violations) == 0,
        "violations": violations,
    }


def _check_entrypoint_contract() -> dict:
    cmd = [sys.executable, str(ROOT / "scripts" / "show_entrypoints.py"), "--strict"]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120, check=False)
    except Exception as exc:
        return {
            "check": "entrypoint_contract_strict",
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
        }
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    summary_line = ""
    for line in out.splitlines():
        if line.strip().startswith("[SUMMARY]"):
            summary_line = line.strip()
            break
    ok = proc.returncode == 0 and ("unclassified=0" in summary_line.lower() or "(none)" in out)
    return {
        "check": "entrypoint_contract_strict",
        "ok": ok,
        "returncode": proc.returncode,
        "summary": summary_line,
    }


def run_checks() -> dict:
    checks = [_check_legacy_entries(), _check_legacy_core_imports(), _check_entrypoint_contract()]
    return {
        "ok": all(bool(c.get("ok")) for c in checks),
        "checks": checks,
        "workspace": str(ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify tistory automation isolation from legacy flows")
    parser.add_argument("--out", default="", help="output JSON path")
    args = parser.parse_args()
    result = run_checks()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        path = Path(args.out)
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"[saved] {path}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
