import argparse
import concurrent.futures
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

from agent_capacity import recommend_workers


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
IMPORT_ONLY = {"mnakr.py", "gabji.py", "premium_auto.py"}
PY_REF_RE = re.compile(r"([A-Za-z0-9_./\\-]+\.py)\b")
PS1_REF_RE = re.compile(r"([%~A-Za-z0-9_./\\-]+\.ps1)\b", re.IGNORECASE)


def _safe_read(path: pathlib.Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _decode(data: bytes) -> str:
    raw = data or b""
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _has_argparse(py_path: pathlib.Path) -> bool:
    text = _safe_read(py_path)
    return ("argparse" in text) or ("ArgumentParser" in text)


def _build_import_cmd(py_rel: str) -> list[str]:
    if ("/" in py_rel) or ("\\" in py_rel):
        return [
            sys.executable,
            "-c",
            "import runpy,sys; runpy.run_path(sys.argv[1], run_name='__smoke__')",
            py_rel,
        ]
    module_name = pathlib.Path(py_rel).stem
    return [
        sys.executable,
        "-c",
        "import importlib,sys; importlib.import_module(sys.argv[1])",
        module_name,
    ]


def _build_smoke_cmd(py_rel: str) -> tuple[list[str], str]:
    file_name = pathlib.Path(py_rel).name.lower()
    if file_name in IMPORT_ONLY:
        return (_build_import_cmd(py_rel), "import")

    py_path = ROOT / py_rel
    if _has_argparse(py_path):
        return [sys.executable, py_rel, "--help"], "help"

    return (_build_import_cmd(py_rel), "import")


def _normalize_ref_token(token: str) -> str:
    normalized = str(token or "").strip().strip("\"'")
    normalized = normalized.replace("%cd%\\", "").replace("%cd%/", "")
    normalized = normalized.replace("%~dp0", "")
    normalized = normalized.replace("\\", "/").lstrip("./")
    normalized = normalized.lstrip("/")
    return normalized


def _extract_python_refs(lines: list[str]) -> list[str]:
    refs = []
    seen = set()
    for line in lines:
        raw = line.strip()
        lower = raw.lower()
        if not raw or raw.startswith("::") or lower.startswith("rem "):
            continue
        for m in PY_REF_RE.finditer(raw):
            token = _normalize_ref_token(m.group(1) or "")
            if not token:
                continue
            key = token.lower()
            if key not in seen:
                refs.append(token)
                seen.add(key)
    return refs


def _extract_ps1_refs(lines: list[str]) -> list[str]:
    refs = []
    seen = set()
    for line in lines:
        raw = line.strip()
        lower = raw.lower()
        if not raw or raw.startswith("::") or lower.startswith("rem "):
            continue
        for m in PS1_REF_RE.finditer(raw):
            token = _normalize_ref_token(m.group(1) or "")
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            refs.append(token)
            seen.add(key)
    return refs


def _check_one_cmd(path: pathlib.Path, strict: bool, timeout_sec: int) -> dict:
    lines = _safe_read(path).splitlines()
    rel_path = path.relative_to(ROOT).as_posix()
    refs = _extract_python_refs(lines)
    ps1_refs = _extract_ps1_refs(lines)

    row = {
        "cmd": rel_path,
        "ok": True,
        "python_refs": refs,
        "ps1_refs": ps1_refs,
        "strict": strict,
        "checks": [],
    }

    if not refs:
        if not ps1_refs:
            row["ok"] = False
            row["error"] = "python/ps1 target not found in cmd"
            return row
        for ref in ps1_refs:
            target_path = (ROOT / ref).resolve()
            exists = target_path.exists()
            check_row = {
                "target": ref,
                "kind": "ps1",
                "ok": bool(exists),
                "smoke_mode": "exists_only",
            }
            if not exists:
                check_row["error"] = "missing"
                row["ok"] = False
            row["checks"].append(check_row)
        return row

    for ref in refs:
        target_path = (ROOT / ref).resolve()
        if not target_path.exists():
            row["ok"] = False
            row["checks"].append({"target": ref, "ok": False, "error": "missing"})
            continue

        check_row = {"target": ref, "ok": True}
        if strict:
            cmd, mode = _build_smoke_cmd(ref)
            check_row["smoke_mode"] = mode
            check_row["command"] = cmd
            env = dict(os.environ)
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    capture_output=True,
                    timeout=max(1, int(timeout_sec)),
                    env=env,
                )
                check_row["returncode"] = proc.returncode
                check_row["stdout_tail"] = _decode(proc.stdout).splitlines()[-20:]
                check_row["stderr_tail"] = _decode(proc.stderr).splitlines()[-20:]
                if proc.returncode != 0:
                    check_row["ok"] = False
                    check_row["error"] = f"smoke command failed (rc={proc.returncode})"
            except subprocess.TimeoutExpired:
                check_row["ok"] = False
                check_row["error"] = f"timeout>{timeout_sec}s"
            except Exception as exc:
                check_row["ok"] = False
                check_row["error"] = str(exc)

        if not check_row.get("ok", False):
            row["ok"] = False
        row["checks"].append(check_row)

    return row


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Smoke-check script/*.cmd entrypoints.")
    p.add_argument("--glob", default="scripts/*.cmd", help="CMD glob under repository root (default: scripts/*.cmd)")
    p.add_argument("--strict", action="store_true", help="Run actual smoke commands (import/help).")
    p.add_argument("--timeout-sec", type=int, default=30, help="Per-target smoke timeout (default: 30)")
    p.add_argument("--max-workers", type=int, default=0, help="Parallel workers (0=auto by system capacity)")
    p.add_argument("--json-out", default="", help="Optional output JSON path.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    files = sorted([p for p in ROOT.glob(args.glob) if p.is_file()])
    if not files:
        print(f"[cmd-smoke] no cmd files matched: {args.glob}")
        return 1

    cap = recommend_workers(task="io")
    requested = int(args.max_workers or 0)
    if requested <= 0:
        requested = int(cap.get("effective_workers", 1))
    max_workers = min(max(1, requested), len(files))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(_check_one_cmd, p, bool(args.strict), int(args.timeout_sec)): p for p in files}
        for fut in concurrent.futures.as_completed(fut_map):
            results.append(fut.result())

    results.sort(key=lambda x: x.get("cmd", ""))
    failures = [r for r in results if not r.get("ok")]
    report = {
        "checked_at": dt.datetime.now().isoformat(),
        "strict": bool(args.strict),
        "workers": {
            "requested": int(args.max_workers or 0),
            "effective": int(max_workers),
            "capacity": cap,
        },
        "cmd_count": len(results),
        "failed_count": len(failures),
        "failed_cmds": [r.get("cmd") for r in failures],
        "results": results,
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = pathlib.Path(args.json_out) if args.json_out else (LOG_DIR / f"cmd_smoke_{stamp}.json")
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        out_display = out_path.relative_to(ROOT).as_posix()
    except ValueError:
        out_display = str(out_path)

    print(f"[cmd-smoke] report: {out_display}")
    print(
        f"[cmd-smoke] summary: ok={len(failures)==0} "
        f"checked={len(results)} failed={len(failures)} workers={max_workers}"
    )
    if failures:
        print("[cmd-smoke] failed: " + ", ".join(r.get("cmd", "?") for r in failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
