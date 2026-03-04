import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "quality_contracts" / "sustainability_guard.contract.json"
DEFAULT_REPORT = ROOT / "logs" / "sustainability_guard_latest.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, fallback: Optional[dict] = None) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(fallback or {})


def _run_git(args: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _parse_github_remote(remote_url: str) -> Optional[Tuple[str, str]]:
    url = (remote_url or "").strip()
    if not url:
        return None
    m = re.search(r"github\.com[:/]+([^/]+)/([^/.]+)(?:\.git)?$", url, flags=re.I)
    if not m:
        return None
    return m.group(1), m.group(2)


def _github_api_json(url: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        req = Request(url, headers={"User-Agent": "seoulmna-sustainability-guard", "Accept": "application/vnd.github+json"})
        with urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        return payload, None
    except URLError as exc:
        return None, f"url_error:{exc}"
    except Exception as exc:
        return None, f"request_error:{exc}"


def _issue(issues: List[dict], severity: str, code: str, message: str, data: Optional[dict] = None) -> None:
    issues.append(
        {
            "severity": str(severity or "medium").lower(),
            "code": str(code or "unknown"),
            "message": str(message or "").strip(),
            "data": dict(data or {}),
        }
    )


def _file_age_minutes(path: Path) -> Optional[float]:
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    delta = datetime.now(timezone.utc) - mtime
    return max(0.0, delta.total_seconds() / 60.0)


def _directory_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    for dirpath, _, files in os.walk(path):
        for name in files:
            fpath = Path(dirpath) / name
            try:
                total += fpath.stat().st_size
            except OSError:
                continue
    return round(total / (1024 * 1024), 2)


def _count_old_files(path: Path, older_than_days: int) -> int:
    if not path.exists():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - (max(1, int(older_than_days)) * 86400)
    count = 0
    for dirpath, _, files in os.walk(path):
        for name in files:
            fpath = Path(dirpath) / name
            try:
                if fpath.stat().st_mtime < cutoff:
                    count += 1
            except OSError:
                continue
    return count


def _check_confirm_live_scripts(contract: dict, issues: List[dict]) -> None:
    for raw_path in list(contract.get("confirm_live_required_scripts", []) or []):
        rel = str(raw_path or "").strip()
        if not rel:
            continue
        target = (ROOT / rel).resolve()
        if not target.exists():
            _issue(
                issues,
                "medium",
                "confirm_live_script_missing",
                f"confirm-live required script not found: {rel}",
                {"path": rel},
            )
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        if "--confirm-live" not in text:
            _issue(
                issues,
                "high",
                "confirm_live_flag_missing",
                f"confirm-live flag not found in required script: {rel}",
                {"path": rel},
            )


def _check_blocked_tracked_files(contract: dict, issues: List[dict]) -> None:
    rc, out, err = _run_git(["ls-files"])
    if rc != 0:
        _issue(issues, "medium", "git_ls_files_failed", "failed to inspect tracked files", {"stderr": err})
        return
    tracked = set(line.strip() for line in out.splitlines() if line.strip())
    for blocked in list(contract.get("blocked_tracked_files", []) or []):
        entry = str(blocked or "").strip().replace("\\", "/")
        if not entry:
            continue
        if entry in tracked:
            _issue(
                issues,
                "high",
                "blocked_file_tracked",
                f"sensitive file is tracked by git: {entry}",
                {"path": entry},
            )


def _check_critical_files(contract: dict, issues: List[dict]) -> None:
    for item in list(contract.get("critical_files", []) or []):
        rel = str((item or {}).get("path", "")).strip()
        if not rel:
            continue
        severity = str((item or {}).get("severity", "medium")).lower()
        required = bool((item or {}).get("required", True))
        max_age = float((item or {}).get("max_age_minutes", 0) or 0)
        target = (ROOT / rel).resolve()
        age_min = _file_age_minutes(target)
        if age_min is None:
            if required:
                _issue(
                    issues,
                    severity,
                    "critical_file_missing",
                    f"critical file missing: {rel}",
                    {"path": rel},
                )
            continue
        if max_age > 0 and age_min > max_age:
            _issue(
                issues,
                severity,
                "critical_file_stale",
                f"critical file stale: {rel} age={round(age_min, 1)}m > {max_age}m",
                {"path": rel, "age_minutes": round(age_min, 2), "max_age_minutes": max_age},
            )


def _check_log_capacity(contract: dict, issues: List[dict]) -> Dict[str, float]:
    log_dir = ROOT / "logs"
    soft_limit_mb = float(contract.get("log_dir_soft_limit_mb", 2048) or 2048)
    retention_days = int(contract.get("log_file_retention_days", 45) or 45)
    max_old = int(contract.get("max_old_log_files", 2000) or 2000)
    size_mb = _directory_size_mb(log_dir)
    old_count = _count_old_files(log_dir, retention_days)
    if size_mb > soft_limit_mb:
        _issue(
            issues,
            "medium",
            "log_dir_over_soft_limit",
            f"log directory size is high: {size_mb}MB > {soft_limit_mb}MB",
            {"size_mb": size_mb, "soft_limit_mb": soft_limit_mb},
        )
    if old_count > max_old:
        _issue(
            issues,
            "low",
            "old_log_files_high",
            f"old log files exceed threshold: {old_count} > {max_old}",
            {"old_files": old_count, "threshold": max_old, "older_than_days": retention_days},
        )
    return {"log_size_mb": size_mb, "log_old_files": old_count}


def _check_repo_security(issues: List[dict]) -> Dict[str, object]:
    result: Dict[str, object] = {
        "origin_url": "",
        "branch": "",
        "github_owner": "",
        "github_repo": "",
        "repo_private": None,
        "default_branch": "",
        "default_branch_protected": None,
    }

    rc, out, err = _run_git(["config", "--get", "remote.origin.url"])
    if rc != 0:
        _issue(issues, "medium", "git_remote_missing", "failed to read git remote", {"stderr": err})
        return result
    origin = out.strip()
    result["origin_url"] = origin

    rc, branch, _ = _run_git(["branch", "--show-current"])
    if rc == 0:
        result["branch"] = branch.strip()

    parsed = _parse_github_remote(origin)
    if not parsed:
        _issue(issues, "low", "non_github_remote", f"origin is not github: {origin}", {"origin_url": origin})
        return result

    owner, repo = parsed
    result["github_owner"] = owner
    result["github_repo"] = repo

    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    repo_payload, repo_err = _github_api_json(repo_url)
    if repo_payload is None:
        _issue(issues, "medium", "github_repo_api_failed", "failed to query github repo metadata", {"error": repo_err})
        return result

    repo_private = bool(repo_payload.get("private"))
    result["repo_private"] = repo_private
    default_branch = str(repo_payload.get("default_branch", "")).strip()
    result["default_branch"] = default_branch
    result["repo_size_kb"] = int(repo_payload.get("size", 0) or 0)

    if not repo_private:
        _issue(
            issues,
            "high",
            "github_repo_public",
            "repository is public; code and operational logic are copyable by anyone",
            {"repository": f"{owner}/{repo}"},
        )

    if default_branch:
        branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{default_branch}"
        branch_payload, branch_err = _github_api_json(branch_url)
        if branch_payload is None:
            _issue(
                issues,
                "medium",
                "github_branch_api_failed",
                "failed to query default branch protection",
                {"error": branch_err, "branch": default_branch},
            )
        else:
            protected = bool(branch_payload.get("protected"))
            result["default_branch_protected"] = protected
            if not protected:
                _issue(
                    issues,
                    "high",
                    "github_default_branch_unprotected",
                    "default branch is not protected",
                    {"branch": default_branch},
                )
    return result


def _severity_counts(issues: List[dict]) -> Dict[str, int]:
    counter = Counter(str(item.get("severity", "medium")).lower() for item in issues)
    return {
        "high": int(counter.get("high", 0)),
        "medium": int(counter.get("medium", 0)),
        "low": int(counter.get("low", 0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sustainability guard for long-term SeoulMNA operations")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--strict", action="store_true", help="exit non-zero when high severity issues are found")
    args = parser.parse_args()

    contract_path = Path(args.contract).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    contract = _read_json(contract_path, fallback={})
    issues: List[dict] = []

    repo_security = _check_repo_security(issues)
    _check_blocked_tracked_files(contract, issues)
    _check_confirm_live_scripts(contract, issues)
    _check_critical_files(contract, issues)
    capacity = _check_log_capacity(contract, issues)
    counts = _severity_counts(issues)

    payload = {
        "ok": counts["high"] == 0,
        "generated_at_utc": _utc_now_iso(),
        "contract": str(contract_path),
        "repo_security": repo_security,
        "capacity": capacity,
        "severity_counts": counts,
        "issues": issues,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[saved] {report_path}")
    print(f"[summary] high={counts['high']} medium={counts['medium']} low={counts['low']}")
    if issues:
        top = issues[:5]
        for item in top:
            print(f"[issue:{item.get('severity')}] {item.get('code')} :: {item.get('message')}")

    if args.strict and counts["high"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
