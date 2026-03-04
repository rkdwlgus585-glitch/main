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
TARGET_LINE_RE = re.compile(r"(?:py(?:\s+-\d(?:\.\d+)?)?|python)\s+([^\s]+\.py)\b", re.IGNORECASE)
DELEGATE_BATCH_TOKEN_RE = re.compile(r"([%~A-Za-z0-9_./\\-]+\.bat)\b", re.IGNORECASE)
DELEGATE_PS1_TOKEN_RE = re.compile(r"([%~A-Za-z0-9_./\\-]+\.ps1)\b", re.IGNORECASE)
PY_TOKEN_RE = re.compile(r"([A-Za-z0-9_./\\-]+\.py)\b", re.IGNORECASE)


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


def _find_python_target(lines: list[str]) -> str:
    for line in lines:
        line = line.strip()
        if not line or line.startswith("::") or line.lower().startswith("rem ") or line.startswith("#"):
            continue
        m = TARGET_LINE_RE.search(line)
        if m:
            return m.group(1).strip().strip("\"'")
        token_match = PY_TOKEN_RE.search(line)
        if token_match:
            return (token_match.group(1) or "").strip().strip("\"'")
    return ""


def _find_delegate_scripts(lines: list[str]) -> list[str]:
    delegates = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("::") or line.lower().startswith("rem ") or line.startswith("#"):
            continue
        for patt in (DELEGATE_BATCH_TOKEN_RE, DELEGATE_PS1_TOKEN_RE):
            for m in patt.finditer(line):
                token = (m.group(1) or "").strip().strip("\"'")
                if not token:
                    continue
                key = token.lower()
                if key in seen:
                    continue
                delegates.append(token)
                seen.add(key)
    return delegates


def _resolve_delegate_path(current_batch: pathlib.Path, token: str) -> pathlib.Path | None:
    raw = str(token or "").strip().strip("\"'")
    if not raw:
        return None

    normalized = raw.replace("%~dp0", "").replace("%cd%", "")
    normalized = normalized.replace(".\\", "").replace("./", "")
    normalized = normalized.strip().strip("\"'")
    if not normalized:
        return None

    candidates: list[pathlib.Path] = []
    candidate = pathlib.Path(normalized)
    if candidate.is_absolute():
        candidates.append(candidate.resolve())
    else:
        candidates.append((current_batch.parent / candidate).resolve())
        # Some launcher batches change cwd to repo root, then use .\scripts\... paths.
        candidates.append((ROOT / candidate).resolve())
        if current_batch.parent.parent:
            candidates.append((current_batch.parent.parent / candidate).resolve())

    seen = set()
    for cand in candidates:
        key = str(cand).lower()
        if key in seen:
            continue
        seen.add(key)
        if cand.exists() and cand.is_file():
            return cand
    return None


def _resolve_python_target(batch_path: pathlib.Path, visited: set[str] | None = None, chain: list[str] | None = None) -> tuple[str, list[str]]:
    visited = visited or set()
    chain = chain or []

    key = str(batch_path.resolve()).lower()
    if key in visited:
        return "", chain
    visited.add(key)

    try:
        rel = batch_path.relative_to(ROOT).as_posix()
    except Exception:
        rel = str(batch_path)
    chain.append(rel)

    lines = _safe_read(batch_path).splitlines()
    target = _find_python_target(lines)
    if target:
        return target, chain

    delegates = _find_delegate_scripts(lines)
    for token in delegates:
        delegate_path = _resolve_delegate_path(batch_path, token)
        if not delegate_path:
            continue
        resolved_target, resolved_chain = _resolve_python_target(delegate_path, visited=visited, chain=list(chain))
        if resolved_target:
            return resolved_target, resolved_chain

    return "", chain


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


def _check_one_batch(path: pathlib.Path, strict: bool, timeout_sec: int) -> dict:
    lines = _safe_read(path).splitlines()
    rel_path = path.relative_to(ROOT).as_posix()
    target, delegate_chain = _resolve_python_target(path)
    has_cd = any('cd/d"%~dp0"' in line.lower().replace(" ", "").replace("\t", "") for line in lines)

    row = {
        "batch": rel_path,
        "ok": True,
        "python_target": target,
        "delegate_chain": delegate_chain,
        "has_cd_dp0": has_cd,
        "strict": strict,
    }

    if not target:
        row["ok"] = False
        row["error"] = "python target not found in batch"
        return row

    target_path = (ROOT / target).resolve()
    if not target_path.exists():
        row["ok"] = False
        row["error"] = f"python target missing: {target}"
        return row

    if not strict:
        row["smoke_mode"] = "parse_only"
        return row

    cmd, mode = _build_smoke_cmd(target)
    row["smoke_mode"] = mode
    row["command"] = cmd

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
    except subprocess.TimeoutExpired:
        row["ok"] = False
        row["error"] = f"timeout>{timeout_sec}s"
        return row
    except Exception as exc:
        row["ok"] = False
        row["error"] = str(exc)
        return row

    row["returncode"] = proc.returncode
    row["stdout_tail"] = _decode(proc.stdout).splitlines()[-20:]
    row["stderr_tail"] = _decode(proc.stderr).splitlines()[-20:]
    if proc.returncode != 0:
        row["ok"] = False
        row["error"] = f"smoke command failed (rc={proc.returncode})"
    return row


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Smoke-check Korean batch entrypoints.")
    p.add_argument("--glob", default="*.bat", help="Batch glob under repository root (default: *.bat)")
    p.add_argument("--strict", action="store_true", help="Run actual smoke commands (import/help).")
    p.add_argument("--timeout-sec", type=int, default=30, help="Per-entry smoke timeout (default: 30)")
    p.add_argument("--max-workers", type=int, default=0, help="Parallel workers (0=auto by system capacity)")
    p.add_argument("--json-out", default="", help="Optional output JSON path.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    batches = sorted([p for p in ROOT.glob(args.glob) if p.is_file()])
    if not batches:
        print(f"[batch-smoke] no batch files matched: {args.glob}")
        return 1

    cap = recommend_workers(task="io")
    requested = int(args.max_workers or 0)
    if requested <= 0:
        requested = int(cap.get("effective_workers", 1))
    max_workers = min(max(1, requested), len(batches))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(_check_one_batch, b, bool(args.strict), int(args.timeout_sec)): b for b in batches}
        for fut in concurrent.futures.as_completed(fut_map):
            results.append(fut.result())

    results.sort(key=lambda x: x.get("batch", ""))
    failures = [r for r in results if not r.get("ok")]
    report = {
        "checked_at": dt.datetime.now().isoformat(),
        "strict": bool(args.strict),
        "workers": {
            "requested": int(args.max_workers or 0),
            "effective": int(max_workers),
            "capacity": cap,
        },
        "batch_count": len(results),
        "failed_count": len(failures),
        "failed_batches": [r.get("batch") for r in failures],
        "results": results,
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = pathlib.Path(args.json_out) if args.json_out else (LOG_DIR / f"batch_smoke_{stamp}.json")
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        out_display = out_path.relative_to(ROOT).as_posix()
    except ValueError:
        out_display = str(out_path)

    print(f"[batch-smoke] report: {out_display}")
    print(
        f"[batch-smoke] summary: ok={len(failures)==0} "
        f"checked={len(results)} failed={len(failures)} workers={max_workers}"
    )
    if failures:
        print("[batch-smoke] failed: " + ", ".join(r.get("batch", "?") for r in failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
