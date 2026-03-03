import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]


def _is_kr_only_mode() -> bool:
    raw = str(os.getenv("SMNA_KR_ONLY_DEV", "")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    return (ROOT / "logs/kr_only_mode.lock").exists()


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _run(cmd: List[str], timeout_sec: int = 240) -> Dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        env=env,
    )
    return {
        "ok": p.returncode == 0,
        "returncode": int(p.returncode),
        "command": cmd,
        "stdout_tail": "\n".join((p.stdout or "").splitlines()[-120:]),
        "stderr_tail": "\n".join((p.stderr or "").splitlines()[-120:]),
    }


def _probe(base_url: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "status_code": 0, "length": 0, "blocked": True, "error": ""}
    try:
        r = requests.get(base_url, timeout=20)
        txt = r.text or ""
        out["status_code"] = int(r.status_code)
        out["length"] = len(txt)
        blocked = ("일일 데이터 전송량 초과안내" in txt) or ("daily data transfer exceeded" in txt.lower())
        out["blocked"] = bool(blocked)
        out["ok"] = (r.status_code == 200) and (not blocked)
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until co.kr is available, then apply hidden-main banner snippet")
    parser.add_argument("--co-base", default="https://seoulmna.co.kr")
    parser.add_argument("--check-interval-sec", type=int, default=180)
    parser.add_argument("--max-wait-minutes", type=int, default=720)
    parser.add_argument("--report", default="logs/wait_apply_hidden_main_banner_latest.json")
    args = parser.parse_args()

    out_path = (ROOT / str(args.report)).resolve()
    if _is_kr_only_mode() and "seoulmna.co.kr" in str(args.co_base).lower():
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "base_url": str(args.co_base).rstrip("/") + "/",
            "probes": [],
            "steps": [],
            "blocking_issues": ["kr_only_mode_enabled"],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(blocked, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[saved] {out_path}")
        print("[ok] False")
        print("[blocking] kr_only_mode_enabled")
        return 2

    base = str(args.co_base).rstrip("/") + "/"
    interval = max(30, int(args.check_interval_sec))
    deadline = time.time() + (max(1, int(args.max_wait_minutes)) * 60)

    report: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": False,
        "base_url": base,
        "probes": [],
        "steps": [],
        "blocking_issues": [],
    }

    while time.time() < deadline:
        probe = _probe(base)
        probe["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report["probes"].append(probe)
        if probe.get("ok"):
            break
        time.sleep(interval)

    if not report["probes"] or not report["probes"][-1].get("ok"):
        report["blocking_issues"].append("co_not_recovered_within_window")
    else:
        step_prepare = _run(
            _py_cmd(
                [
                    "scripts/prepare_co_global_banner_snippet.py",
                    "--target-url",
                    "https://seoulmna.co.kr/bbs/content.php?co_id=ai_calc",
                    "--acquisition-url",
                    "https://seoulmna.co.kr/bbs/content.php?co_id=ai_acq",
                    "--frame-customer-url",
                    "https://seoulmna.kr/yangdo-ai-customer/",
                    "--frame-acquisition-url",
                    "https://seoulmna.kr/ai-license-acquisition-calculator/",
                    "--snippet-out",
                    "logs/co_global_banner_snippet.html",
                    "--guide-out",
                    "logs/co_global_banner_apply_guide.md",
                ]
            ),
            timeout_sec=120,
        )
        step_prepare["name"] = "prepare_hidden_main_snippet"
        report["steps"].append(step_prepare)

        if step_prepare.get("ok"):
            step_apply = _run(
                _py_cmd(
                    [
                        "scripts/apply_co_global_banner_admin.py",
                        "--base-url",
                        "https://seoulmna.co.kr",
                        "--snippet-file",
                        "logs/co_global_banner_snippet.html",
                        "--report",
                        "logs/co_global_banner_apply_latest.json",
                    ]
                ),
                timeout_sec=180,
            )
            step_apply["name"] = "apply_banner_admin"
            report["steps"].append(step_apply)
            if not step_apply.get("ok"):
                report["blocking_issues"].append("apply_banner_admin_failed")
        else:
            report["blocking_issues"].append("prepare_hidden_main_snippet_failed")

    report["ok"] = not report["blocking_issues"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {out_path}")
    print(f"[ok] {report.get('ok')}")
    if report["blocking_issues"]:
        print("[blocking]", ", ".join(report["blocking_issues"]))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
