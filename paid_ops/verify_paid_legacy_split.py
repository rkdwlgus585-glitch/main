import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAID_TOKENS = [
    "gabji-report",
    "gb2-audit",
    "paid_ops/run.py",
    "build_gabji_analysis_report.py",
    "audit_gb2_v3_integration.py",
    "verify_paid_legacy_split.py",
]

LEGACY_ENTRY_BAT = list(ROOT.glob("*.bat")) + list((ROOT / "launchers").glob("*.bat")) + list((ROOT / "scripts").glob("*.cmd"))
LEGACY_CORE_FILES = [
    ROOT / "all.py",
    ROOT / "mnakr.py",
    ROOT / "gabji.py",
    ROOT / "premium_auto.py",
    ROOT / "maemul.py",
    ROOT / "match.py",
    ROOT / "quote_engine.py",
    ROOT / "sales_pipeline.py",
    ROOT / "consult_match_scheduler.py",
]


def _read_text(path: Path):
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(errors="ignore")


def _check_run_py_legacy():
    path = ROOT / "run.py"
    text = _read_text(path)
    hits = [tok for tok in ("gabji-report", "gb2-audit", "paid_ops/run.py") if tok in text]
    return {
        "check": "run_py_has_no_paid_commands",
        "ok": len(hits) == 0,
        "file": str(path),
        "hits": hits,
    }


def _check_no_paid_tokens_in_legacy_launchers():
    violations = []
    for path in LEGACY_ENTRY_BAT:
        text = _read_text(path).lower()
        for tok in PAID_TOKENS:
            if tok.lower() in text:
                violations.append({"file": str(path), "token": tok})
    return {
        "check": "legacy_launchers_do_not_call_paid_paths",
        "ok": len(violations) == 0,
        "violations": violations,
    }


def _check_core_does_not_import_paid():
    patterns = [
        re.compile(r"\bimport\s+paid_ops\.run\b"),
        re.compile(r"\bfrom\s+paid_ops\.run\s+import\b"),
        re.compile(r"\bimport\s+run_paid\b"),
        re.compile(r"\bfrom\s+run_paid\s+import\b"),
        re.compile(r"\bbuild_gabji_analysis_report\b"),
        re.compile(r"\baudit_gb2_v3_integration\b"),
        re.compile(r"\bverify_paid_legacy_split\b"),
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
        "check": "legacy_core_has_no_paid_imports",
        "ok": len(violations) == 0,
        "violations": violations,
    }


def _check_entrypoint_contract():
    cmd = [sys.executable, str(ROOT / "scripts" / "show_entrypoints.py"), "--strict"]
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120, check=False)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except Exception as exc:
        return {
            "check": "entrypoint_contract_strict",
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
            "output": "",
        }
    unknown_line = ""
    for line in out.splitlines():
        if line.strip().startswith("[UNCLASSIFIED_ENTRYPOINTS]"):
            unknown_line = line.strip()
            break
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
        "unclassified_line": unknown_line,
    }


def run_checks():
    checks = [
        _check_run_py_legacy(),
        _check_no_paid_tokens_in_legacy_launchers(),
        _check_core_does_not_import_paid(),
        _check_entrypoint_contract(),
    ]
    ok = all(bool(item.get("ok")) for item in checks)
    return {"ok": ok, "checks": checks, "workspace": str(ROOT)}


def main():
    parser = argparse.ArgumentParser(description="Verify paid/new-business and legacy automation separation")
    parser.add_argument("--out", default="", help="Output JSON path")
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
