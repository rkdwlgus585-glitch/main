import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import py_compile
import shutil
import subprocess
import sys
import time
import threading
import tempfile

from agent_capacity import recommend_workers


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_CONTRACT_DIR = ROOT / "quality_contracts"
COMPILE_LOCK = threading.Lock()
RUNNER_VERSION = "1.1.0"


def _safe_read_text(path: pathlib.Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return (data or b"").decode(enc)
        except UnicodeDecodeError:
            continue
    return (data or b"").decode("utf-8", errors="replace")


def _subprocess_env() -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def _rel_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _tail(text: str, lines: int = 30) -> list[str]:
    rows = (text or "").splitlines()
    return rows[-lines:]


def _get_dotted(payload: object, dotted_key: str):
    value = payload
    for segment in dotted_key.split("."):
        if not isinstance(value, dict) or segment not in value:
            return None, False
        value = value[segment]
    return value, True


def _expand_path_inputs(path_inputs: list[str]) -> tuple[list[pathlib.Path], list[str]]:
    resolved: list[pathlib.Path] = []
    missing: list[str] = []
    seen: set[str] = set()

    for raw in path_inputs:
        has_glob = any(ch in raw for ch in "*?[]")
        if has_glob:
            matches = [p for p in sorted(ROOT.glob(raw)) if p.is_file()]
            if not matches:
                missing.append(raw)
                continue
            for match in matches:
                key = str(match.resolve()).lower()
                if key not in seen:
                    resolved.append(match)
                    seen.add(key)
            continue

        target = (ROOT / raw).resolve()
        key = str(target).lower()
        if key not in seen:
            resolved.append(target)
            seen.add(key)

    return resolved, missing


def _run_file_exists(check: dict) -> tuple[bool, dict]:
    paths = check.get("paths", [])
    if not isinstance(paths, list) or not paths:
        return False, {"error": "paths must be a non-empty list"}

    missing = []
    checked = []
    for raw in paths:
        target = ROOT / raw
        checked.append(raw)
        if not target.exists():
            missing.append(raw)

    return len(missing) == 0, {"checked": checked, "missing": missing}


def _run_python_compile(check: dict) -> tuple[bool, dict]:
    paths = check.get("paths", [])
    if not isinstance(paths, list) or not paths:
        return False, {"error": "paths must be a non-empty list"}

    candidates, missing_patterns = _expand_path_inputs(paths)
    files = [p for p in candidates if p.exists() and p.is_file()]
    missing_files = [raw for raw in paths if not any(ch in raw for ch in "*?[]") and not (ROOT / raw).exists()]
    failures = []

    with tempfile.TemporaryDirectory(prefix="quality_compile_") as td:
        temp_dir = pathlib.Path(td)
        for path in files:
            try:
                # Compile to isolated temp targets to avoid __pycache__ write races.
                digest = hashlib.sha1(str(path).encode("utf-8", errors="ignore")).hexdigest()[:16]
                cfile = temp_dir / f"{path.stem}_{digest}.pyc"
                with COMPILE_LOCK:
                    py_compile.compile(str(path), cfile=str(cfile), doraise=True)
            except Exception as exc:
                failures.append({"file": _rel_path(path), "error": str(exc)})

    ok = (len(failures) == 0) and (len(missing_patterns) == 0) and (len(missing_files) == 0) and (len(files) > 0)
    detail = {
        "checked_count": len(files),
        "checked_files": [_rel_path(p) for p in files],
        "missing_patterns": missing_patterns,
        "missing_files": missing_files,
        "failures": failures,
    }
    return ok, detail


def _run_python_import(check: dict) -> tuple[bool, dict]:
    modules = check.get("modules", [])
    if not isinstance(modules, list) or not modules:
        return False, {"error": "modules must be a non-empty list"}

    timeout_sec = int(check.get("timeout_sec", 20))
    failures = []

    for module_name in modules:
        cmd = [
            sys.executable,
            "-c",
            "import importlib, sys; importlib.import_module(sys.argv[1])",
            module_name,
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                timeout=timeout_sec,
                env=_subprocess_env(),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            failures.append({"module": module_name, "error": f"timeout>{timeout_sec}s"})
            continue

        if proc.returncode != 0:
            failures.append(
                {
                    "module": module_name,
                    "returncode": proc.returncode,
                    "stdout_tail": _tail(_decode_bytes(proc.stdout), 15),
                    "stderr_tail": _tail(_decode_bytes(proc.stderr), 15),
                }
            )

    return len(failures) == 0, {"checked_modules": modules, "failures": failures}


def _run_unittest_discover(check: dict) -> tuple[bool, dict]:
    start_dir = check.get("start_dir", "tests")
    pattern = check.get("pattern", "test_*.py")
    timeout_sec = int(check.get("timeout_sec", 300))
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", start_dir, "-p", pattern, "-q"]

    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            timeout=timeout_sec,
            env=_subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        return False, {"error": f"timeout>{timeout_sec}s", "command": cmd}

    out = _decode_bytes(proc.stdout).strip()
    err = _decode_bytes(proc.stderr).strip()
    return proc.returncode == 0, {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
    }


def _normalize_command(command_value):
    if isinstance(command_value, str):
        return command_value
    if not isinstance(command_value, list):
        return None
    return [sys.executable if token == "{python}" else token for token in command_value]


def _run_command(check: dict) -> tuple[bool, dict]:
    command_value = check.get("command")
    normalized = _normalize_command(command_value)
    if normalized is None:
        return False, {"error": "command must be a string or string list"}

    # String commands are usually shell snippets (for example: "echo hello"),
    # so default shell=True only for that case.
    default_shell = isinstance(normalized, str)
    shell = bool(check.get("shell", default_shell))
    timeout_sec = int(check.get("timeout_sec", 60))

    try:
        proc = subprocess.run(
            normalized,
            cwd=ROOT,
            capture_output=True,
            shell=shell,
            timeout=timeout_sec,
            env=_subprocess_env(),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return False, {"error": f"timeout>{timeout_sec}s", "command": normalized}

    out = _decode_bytes(proc.stdout).strip()
    err = _decode_bytes(proc.stderr).strip()
    return proc.returncode == 0, {
        "command": normalized,
        "shell": shell,
        "returncode": proc.returncode,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
    }


def _run_json_report(check: dict) -> tuple[bool, dict]:
    pattern = check.get("glob")
    if not isinstance(pattern, str) or not pattern:
        return False, {"error": "glob must be a non-empty string"}

    files = [p for p in sorted(ROOT.glob(pattern)) if p.is_file()]
    if not files:
        return False, {"error": "no files matched", "glob": pattern}

    latest = max(files, key=lambda p: p.stat().st_mtime)
    age_hours = (time.time() - latest.stat().st_mtime) / 3600.0

    try:
        payload = json.loads(_safe_read_text(latest))
    except json.JSONDecodeError as exc:
        return False, {"error": f"json decode error: {exc}", "file": _rel_path(latest)}

    missing_keys = []
    for dotted_key in check.get("must_have_keys", []):
        _, found = _get_dotted(payload, dotted_key)
        if not found:
            missing_keys.append(dotted_key)

    max_age_hours = check.get("max_age_hours")
    too_old = False
    if max_age_hours is not None:
        too_old = age_hours > float(max_age_hours)

    ok = (not too_old) and (len(missing_keys) == 0)
    detail = {
        "glob": pattern,
        "latest_file": _rel_path(latest),
        "age_hours": round(age_hours, 3),
        "max_age_hours": max_age_hours,
        "missing_keys": missing_keys,
        "matched_file_count": len(files),
    }
    return ok, detail


CHECK_RUNNERS = {
    "file_exists": _run_file_exists,
    "python_compile": _run_python_compile,
    "python_import": _run_python_import,
    "unittest_discover": _run_unittest_discover,
    "command": _run_command,
    "json_report": _run_json_report,
}


def _run_check(check: dict) -> dict:
    started = time.perf_counter()
    check_id = check.get("id", "<unknown>")
    check_type = check.get("type")
    required = bool(check.get("required", True))

    if check_type not in CHECK_RUNNERS:
        return {
            "id": check_id,
            "type": check_type,
            "required": required,
            "ok": False,
            "duration_sec": round(time.perf_counter() - started, 4),
            "detail": {"error": f"unsupported check type: {check_type}"},
        }

    try:
        ok, detail = CHECK_RUNNERS[check_type](check)
    except Exception as exc:
        ok = False
        detail = {"error": str(exc)}

    return {
        "id": check_id,
        "type": check_type,
        "required": required,
        "ok": bool(ok),
        "duration_sec": round(time.perf_counter() - started, 4),
        "detail": detail,
    }


def _validate_contract(contract: dict) -> list[str]:
    issues = []
    if not isinstance(contract, dict):
        return ["contract root must be an object"]

    automation = contract.get("automation")
    if not isinstance(automation, str) or not automation.strip():
        issues.append("automation must be a non-empty string")

    checks = contract.get("checks")
    if not isinstance(checks, list) or not checks:
        issues.append("checks must be a non-empty list")
        return issues

    seen_ids = set()
    for idx, check in enumerate(checks):
        if not isinstance(check, dict):
            issues.append(f"checks[{idx}] must be an object")
            continue
        check_id = check.get("id")
        check_type = check.get("type")
        if not isinstance(check_id, str) or not check_id.strip():
            issues.append(f"checks[{idx}].id must be a non-empty string")
        elif check_id in seen_ids:
            issues.append(f"duplicate check id: {check_id}")
        else:
            seen_ids.add(check_id)
        if check_type not in CHECK_RUNNERS:
            issues.append(f"checks[{idx}].type unsupported: {check_type}")
        issues.extend(_validate_check_shape(check, idx))

    return issues


def _validate_check_shape(check: dict, idx: int) -> list[str]:
    issues = []
    check_type = check.get("type")

    if check_type in ("file_exists", "python_compile"):
        paths = check.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(x, str) for x in paths):
            issues.append(f"checks[{idx}].paths must be a non-empty string list")

    if check_type == "python_import":
        modules = check.get("modules")
        if not isinstance(modules, list) or not modules or not all(isinstance(x, str) for x in modules):
            issues.append(f"checks[{idx}].modules must be a non-empty string list")

    if check_type == "unittest_discover":
        if not isinstance(check.get("start_dir"), str):
            issues.append(f"checks[{idx}].start_dir must be a string")
        if not isinstance(check.get("pattern"), str):
            issues.append(f"checks[{idx}].pattern must be a string")

    if check_type == "command":
        command_value = check.get("command")
        command_ok = (
            isinstance(command_value, str)
            or (
                isinstance(command_value, list)
                and command_value
                and all(isinstance(token, str) for token in command_value)
            )
        )
        if not command_ok:
            issues.append(f"checks[{idx}].command must be a non-empty string or string list")

    if check_type == "json_report":
        if not isinstance(check.get("glob"), str) or not check.get("glob"):
            issues.append(f"checks[{idx}].glob must be a non-empty string")
        keys = check.get("must_have_keys")
        if keys is not None and (not isinstance(keys, list) or not all(isinstance(k, str) for k in keys)):
            issues.append(f"checks[{idx}].must_have_keys must be a string list")

    timeout = check.get("timeout_sec")
    if timeout is not None:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            issues.append(f"checks[{idx}].timeout_sec must be > 0")

    return issues


def _run_contract(contract_path: pathlib.Path) -> dict:
    started_at = dt.datetime.now()

    try:
        contract = json.loads(_safe_read_text(contract_path))
    except json.JSONDecodeError as exc:
        return {
            "automation": contract_path.name.replace(".contract.json", ""),
            "contract_file": _rel_path(contract_path),
            "description": "",
            "ok": False,
            "error": f"json decode error: {exc}",
            "required_failures": 1,
            "optional_failures": 0,
            "checks": [],
            "started_at": started_at.isoformat(),
            "finished_at": dt.datetime.now().isoformat(),
        }

    validation_issues = _validate_contract(contract)
    if validation_issues:
        return {
            "automation": str(contract.get("automation", contract_path.stem)),
            "contract_file": _rel_path(contract_path),
            "description": str(contract.get("description", "")),
            "ok": False,
            "error": "invalid contract",
            "validation_issues": validation_issues,
            "required_failures": len(validation_issues),
            "optional_failures": 0,
            "checks": [],
            "started_at": started_at.isoformat(),
            "finished_at": dt.datetime.now().isoformat(),
        }

    checks = list(contract["checks"])
    indexed_results = {}
    max_workers = min(8, len(checks)) if checks else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        fut_to_index = {
            executor.submit(_run_check, check): idx for idx, check in enumerate(checks)
        }
        for fut in concurrent.futures.as_completed(fut_to_index):
            idx = fut_to_index[fut]
            indexed_results[idx] = fut.result()

    ordered = [indexed_results[i] for i in sorted(indexed_results)]
    required_failures = sum(1 for row in ordered if row["required"] and not row["ok"])
    optional_failures = sum(1 for row in ordered if (not row["required"]) and (not row["ok"]))

    return {
        "automation": contract["automation"],
        "contract_file": _rel_path(contract_path),
        "description": contract.get("description", ""),
        "ok": required_failures == 0,
        "required_failures": required_failures,
        "optional_failures": optional_failures,
        "checks": ordered,
        "started_at": started_at.isoformat(),
        "finished_at": dt.datetime.now().isoformat(),
    }


def _discover_contracts(contract_dir: pathlib.Path, selected: set[str]) -> tuple[list[pathlib.Path], list[str]]:
    all_paths = sorted(contract_dir.glob("*.contract.json"))
    if not selected:
        return all_paths, []

    by_name = {p.name.replace(".contract.json", ""): p for p in all_paths}
    resolved = []
    missing = []
    for name in sorted(selected):
        path = by_name.get(name)
        if path is None:
            missing.append(name)
        else:
            resolved.append(path)
    return resolved, missing


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run quality contracts in parallel and produce daily report JSON.")
    parser.add_argument(
        "--contract-dir",
        default="quality_contracts",
        help="Contract directory path (default: quality_contracts)",
    )
    parser.add_argument(
        "--contracts",
        default="",
        help="Comma-separated automation names (example: mnakr,gabji). Default: all contracts.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=0,
        help="Max contract-level parallel workers (0=auto by system capacity)",
    )
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Treat optional check failures as gate failures.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print summary only.",
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=30,
        help="Delete quality_daily_*.json older than N days (default: 30, 0=disable cleanup).",
    )
    return parser.parse_args()


def _cleanup_old_reports(keep_days: int, protected: set[pathlib.Path]) -> dict:
    if keep_days <= 0:
        return {"enabled": False, "removed": 0, "removed_files": []}

    cutoff = time.time() - (keep_days * 24 * 3600)
    removed_files = []
    for path in sorted(LOG_DIR.glob("quality_daily_*.json")):
        if not path.is_file():
            continue
        if path.name == "quality_daily_latest.json":
            continue
        if path.resolve() in protected:
            continue
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed_files.append(_rel_path(path))

    return {"enabled": True, "keep_days": keep_days, "removed": len(removed_files), "removed_files": removed_files}


def main() -> int:
    args = _parse_args()
    contract_dir = pathlib.Path(args.contract_dir)
    if not contract_dir.is_absolute():
        contract_dir = ROOT / contract_dir

    if not contract_dir.exists():
        print(f"[quality-daily] contract dir not found: {_rel_path(contract_dir)}")
        return 1

    selected = {part.strip() for part in args.contracts.split(",") if part.strip()}
    contract_paths, missing = _discover_contracts(contract_dir, selected)
    if missing:
        print(f"[quality-daily] missing contracts: {', '.join(missing)}")
        return 1
    if not contract_paths:
        print("[quality-daily] no contract files found")
        return 1

    started_at = dt.datetime.now()
    indexed_results = {}
    cap = recommend_workers(task="mixed")
    requested_workers = int(args.max_workers or 0)
    if requested_workers <= 0:
        requested_workers = int(cap.get("effective_workers", 1))
    max_workers = min(max(1, requested_workers), len(contract_paths))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        fut_to_idx = {
            executor.submit(_run_contract, path): idx for idx, path in enumerate(contract_paths)
        }
        for fut in concurrent.futures.as_completed(fut_to_idx):
            idx = fut_to_idx[fut]
            indexed_results[idx] = fut.result()

    contract_results = [indexed_results[i] for i in sorted(indexed_results)]
    failed_contracts = [r["automation"] for r in contract_results if not r["ok"]]
    required_fail_count = sum(r.get("required_failures", 0) for r in contract_results)
    optional_fail_count = sum(r.get("optional_failures", 0) for r in contract_results)
    optional_warn_contracts = [r["automation"] for r in contract_results if r.get("optional_failures", 0) > 0]

    overall_ok = (len(failed_contracts) == 0) and (not args.fail_on_warn or optional_fail_count == 0)

    report = {
        "started_at": started_at.isoformat(),
        "finished_at": dt.datetime.now().isoformat(),
        "ok": overall_ok,
        "runner_version": RUNNER_VERSION,
        "python_version": sys.version.split()[0],
        "workers": {
            "requested": int(args.max_workers or 0),
            "effective": int(max_workers),
            "capacity": cap,
        },
        "contract_dir": _rel_path(contract_dir),
        "contracts_checked": len(contract_results),
        "selected_contracts": sorted(selected),
        "summary": {
            "failed_contracts": failed_contracts,
            "optional_warn_contracts": optional_warn_contracts,
            "required_fail_count": required_fail_count,
            "optional_fail_count": optional_fail_count,
        },
        "results": contract_results,
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = LOG_DIR / f"quality_daily_{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path = LOG_DIR / "quality_daily_latest.json"
    shutil.copyfile(report_path, latest_path)

    cleanup = _cleanup_old_reports(
        keep_days=int(args.keep_days),
        protected={report_path.resolve(), latest_path.resolve()},
    )
    report["cleanup"] = cleanup
    # Persist cleanup details as part of the same run report.
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(report_path, latest_path)

    print(f"[quality-daily] report: {_rel_path(report_path)}")
    print(
        "[quality-daily] summary: "
        f"ok={overall_ok} "
        f"contracts={len(contract_results)} "
        f"workers={max_workers} "
        f"required_fail={required_fail_count} "
        f"optional_fail={optional_fail_count} "
        f"cleanup_removed={cleanup.get('removed', 0)}"
    )
    if (not args.quiet) and failed_contracts:
        print(f"[quality-daily] failed contracts: {', '.join(failed_contracts)}")
    if (not args.quiet) and optional_warn_contracts:
        print(f"[quality-daily] warn contracts: {', '.join(optional_warn_contracts)}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
