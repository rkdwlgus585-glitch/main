import argparse
import collections
import concurrent.futures
import csv
import datetime as dt
import json
import pathlib
import py_compile
import re
import subprocess
import sys
import time

from agent_capacity import recommend_workers


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"


def _safe_read_text(path: pathlib.Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            pass
    return path.read_text(encoding="utf-8", errors="replace")


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return (data or b"").decode(enc)
        except Exception:
            pass
    return (data or b"").decode("utf-8", errors="replace")


def task_file_inventory():
    counts = collections.Counter()
    total = 0
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        ext = p.suffix.lower() or "<noext>"
        counts[ext] += 1
        total += 1
    top = [{"ext": k, "count": v} for k, v in counts.most_common(30)]
    return {
        "ok": True,
        "total_files": total,
        "by_extension": top,
    }


def task_python_compile():
    failures = []
    py_files = sorted(ROOT.rglob("*.py"))
    for p in py_files:
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            failures.append({"file": str(p.relative_to(ROOT)), "error": str(e)})
    return {
        "ok": len(failures) == 0,
        "checked": len(py_files),
        "failures": failures,
    }


def task_unittest():
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
    )
    out = _decode_bytes(proc.stdout).strip()
    err = _decode_bytes(proc.stderr).strip()
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": out.splitlines()[-30:],
        "stderr_tail": err.splitlines()[-30:],
    }


def task_json_validate():
    bad = []
    checked = 0
    for p in sorted(ROOT.rglob("*.json")):
        checked += 1
        try:
            json.loads(_safe_read_text(p))
        except Exception as e:
            bad.append({"file": str(p.relative_to(ROOT)), "error": str(e)})
    return {"ok": len(bad) == 0, "checked": checked, "failures": bad}


def task_csv_validate():
    bad = []
    checked = 0
    for p in sorted(ROOT.rglob("*.csv")):
        checked += 1
        try:
            with p.open("r", encoding="utf-8-sig", newline="") as f:
                list(csv.reader(f))
        except Exception as e:
            bad.append({"file": str(p.relative_to(ROOT)), "error": str(e)})
    return {"ok": len(bad) == 0, "checked": checked, "failures": bad}


def task_batch_scan():
    warnings = []
    files = sorted(ROOT.glob("*.bat")) + sorted((ROOT / "scripts").glob("*.cmd"))
    hardcoded_python = re.compile(r"[A-Za-z]:\\Users\\[^\\]+\\.*python(?:\.exe)?", re.IGNORECASE)
    for p in files:
        txt = _safe_read_text(p)
        if txt.count('"') % 2 != 0:
            warnings.append({"file": str(p.relative_to(ROOT)), "warning": "odd_quote_count"})
        if hardcoded_python.search(txt):
            warnings.append({"file": str(p.relative_to(ROOT)), "warning": "hardcoded_python_path"})
    return {"ok": True, "checked": len(files), "warnings": warnings}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run parallel debug checks with capacity-aware workers.")
    parser.add_argument("--max-workers", type=int, default=0, help="Parallel workers (0=auto by system capacity)")
    return parser.parse_args()


def run_parallel_debug(max_workers=0):
    LOG_DIR.mkdir(exist_ok=True)
    started_at = dt.datetime.now()

    tasks = {
        "inventory": task_file_inventory,
        "python_compile": task_python_compile,
        "unittest": task_unittest,
        "json_validate": task_json_validate,
        "csv_validate": task_csv_validate,
        "batch_scan": task_batch_scan,
    }

    cap = recommend_workers(task="mixed")
    requested = int(max_workers or 0)
    if requested <= 0:
        requested = int(cap.get("effective_workers", 1))
    effective_workers = min(max(1, requested), len(tasks))

    results = {}
    durations = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers) as ex:
        fut_map = {}
        started_map = {}
        for name, fn in tasks.items():
            fut = ex.submit(fn)
            fut_map[fut] = name
            started_map[fut] = time.perf_counter()
        for fut in concurrent.futures.as_completed(fut_map):
            name = fut_map[fut]
            try:
                results[name] = fut.result()
            except Exception as e:
                results[name] = {"ok": False, "error": str(e)}
            durations[name] = round(time.perf_counter() - started_map[fut], 4)

    hard_fail_keys = ["python_compile", "unittest", "json_validate", "csv_validate"]
    ok = all(results.get(k, {}).get("ok", False) for k in hard_fail_keys)
    report = {
        "started_at": started_at.isoformat(),
        "finished_at": dt.datetime.now().isoformat(),
        "ok": ok,
        "workers": {
            "requested": int(max_workers or 0),
            "effective": int(effective_workers),
            "capacity": cap,
        },
        "durations_sec": durations,
        "results": results,
    }

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = LOG_DIR / f"parallel_debug_report_{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[parallel-debug] report: {report_path}")
    print(f"[parallel-debug] ok={ok}")
    print(f"[parallel-debug] workers={effective_workers}")
    print(
        "[parallel-debug] summary: "
        f"py={results.get('python_compile', {}).get('checked', 0)} "
        f"tests_rc={results.get('unittest', {}).get('returncode', -1)} "
        f"json={results.get('json_validate', {}).get('checked', 0)} "
        f"csv={results.get('csv_validate', {}).get('checked', 0)} "
        f"batch={results.get('batch_scan', {}).get('checked', 0)}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(run_parallel_debug(max_workers=args.max_workers))
