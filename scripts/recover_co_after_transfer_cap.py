import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: List[str], timeout_sec: int = 600) -> Dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "cmd": cmd,
    }


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_transfer_cap_error(text: str) -> bool:
    src = str(text or "").lower()
    return ("transfer cap" in src) or ("gethompy 503" in src) or ("전송량" in src)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retry seoulmna.co.kr banner/content apply until transfer-cap lock clears",
    )
    parser.add_argument("--max-attempts", type=int, default=24)
    parser.add_argument("--interval-sec", type=int, default=900, help="Retry interval in seconds")
    parser.add_argument("--confirm-live", default="", help="실서비스 반영 승인 토큰 (`--confirm-live YES`)")
    parser.add_argument("--report", default="logs/recover_co_after_transfer_cap_latest.json")
    args = parser.parse_args()
    confirm_live = str(args.confirm_live or "").strip().upper()
    if confirm_live != "YES":
        report_path = (ROOT / args.report).resolve()
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "attempts": [],
            "attempt_count": 0,
            "final_error": "confirm_live_missing",
        }
        _save_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[ok] False")
        print("[error] confirm_live_missing")
        return 2

    report_path = (ROOT / args.report).resolve()
    attempts: List[Dict[str, Any]] = []
    ok = False
    final_error = ""

    for idx in range(1, max(1, int(args.max_attempts)) + 1):
        attempt: Dict[str, Any] = {
            "attempt": idx,
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "steps": [],
        }

        step_prepare = _run(["py", "scripts/prepare_co_global_banner_snippet.py"], timeout_sec=240)
        attempt["steps"].append({"name": "prepare_snippet", **step_prepare})

        step_apply = _run(
            ["py", "scripts/apply_co_global_banner_admin.py", "--confirm-live", "YES"],
            timeout_sec=420,
        )
        attempt["steps"].append({"name": "apply_banner_admin", **step_apply})

        apply_report = _read_json(ROOT / "logs" / "co_global_banner_apply_latest.json")
        apply_ok = bool(apply_report.get("ok"))
        apply_error = str(apply_report.get("error", "") or "")

        step_pages = _run(
            ["py", "scripts/deploy_co_content_pages.py", "--confirm-live", "YES"],
            timeout_sec=420,
        )
        attempt["steps"].append({"name": "deploy_co_content_pages", **step_pages})
        pages_report = _read_json(ROOT / "logs" / "co_content_pages_deploy_latest.json")
        pages_ok = bool(pages_report.get("ok"))
        pages_error = str(pages_report.get("error", "") or "")

        attempt["apply_ok"] = apply_ok
        attempt["pages_ok"] = pages_ok
        attempt["apply_error"] = apply_error
        attempt["pages_error"] = pages_error
        attempts.append(attempt)

        _save_json(
            report_path,
            {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ok": bool(apply_ok and pages_ok),
                "attempts": attempts,
                "latest_attempt": attempt,
            },
        )

        if apply_ok and pages_ok:
            ok = True
            break

        merged_error = " | ".join([x for x in [apply_error, pages_error] if x]).strip()
        final_error = merged_error or "unknown_error"
        if not _is_transfer_cap_error(merged_error):
            break
        if idx < int(args.max_attempts):
            time.sleep(max(10, int(args.interval_sec)))

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "attempts": attempts,
        "attempt_count": len(attempts),
        "final_error": final_error,
    }
    _save_json(report_path, report)
    print(f"[saved] {report_path}")
    print(f"[ok] {ok}")
    if final_error and not ok:
        print(f"[error] {final_error}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
