import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _run(cmd: List[str], timeout_sec: int = 420) -> Dict[str, Any]:
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


def _read_env(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip().lstrip("\ufeff")
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _write_env(path: Path, updates: Dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    seen = set()
    out_lines: List[str] = []
    for line in lines:
        raw = line
        s = raw.strip().lstrip("\ufeff")
        if not s or s.startswith("#") or "=" not in s:
            out_lines.append(raw)
            continue
        k, _v = s.split("=", 1)
        key = k.strip()
        if key in updates:
            out_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out_lines.append(raw)
    for k, v in updates.items():
        if k not in seen:
            out_lines.append(f"{k}={v}")
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def _check_url(url: str, required: List[str]) -> Dict[str, Any]:
    out = {
        "url": url,
        "ok": False,
        "status_code": 0,
        "length": 0,
        "found": {},
        "error": "",
    }
    try:
        r = requests.get(url, timeout=25)
        txt = r.text or ""
        out["status_code"] = int(r.status_code)
        out["length"] = len(txt)
        for key in required:
            if key.startswith("re:"):
                out["found"][key] = bool(re.search(key[3:], txt, flags=re.I))
            else:
                out["found"][key] = key in txt
        out["ok"] = r.status_code == 200 and all(bool(v) for v in out["found"].values())
    except Exception as e:
        out["error"] = str(e)
    return out


def _looks_like_gas_url(url: str) -> bool:
    s = str(url or "").strip().lower()
    if not s:
        return False
    return ("script.google.com" in s or "script.googleusercontent.com" in s) and "/exec" in s


def _is_kr_only_mode() -> bool:
    raw = str(os.getenv("SMNA_KR_ONLY_DEV", "")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    return (ROOT / "logs/kr_only_mode.lock").exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="B-plan masterpiece deploy: GAS bundle + co.kr content + global banner")
    parser.add_argument("--co-base", default="https://seoulmna.co.kr")
    parser.add_argument("--customer-co-id", default="ai_calc")
    parser.add_argument("--acquisition-co-id", default="ai_acq")
    parser.add_argument("--gas-exec-url", default="")
    parser.add_argument("--gas-customer-url", default="")
    parser.add_argument("--gas-acquisition-url", default="")
    parser.add_argument("--persist-env", action="store_true", help="Write resolved GAS URLs into .env")
    parser.add_argument(
        "--require-gas",
        action="store_true",
        help="Fail if frame URLs are not GAS /exec URLs (prevents fallback domain shipping).",
    )
    parser.add_argument("--skip-gas-bundle", action="store_true")
    parser.add_argument("--max-train-rows", type=int, default=260)
    parser.add_argument("--show-main-banner", action="store_true", help="Show floating banner on co.kr main page")
    parser.add_argument("--skip-runtime-verify", action="store_true")
    parser.add_argument("--report", default="logs/b_plan_masterpiece_latest.json")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    co_base = str(args.co_base).rstrip("/")
    customer_page = f"{co_base}/bbs/content.php?co_id={args.customer_co_id}"
    acquisition_page = f"{co_base}/bbs/content.php?co_id={args.acquisition_co_id}"
    kr_only_mode = _is_kr_only_mode()

    env = _read_env(ROOT / ".env")
    gas_exec = str(args.gas_exec_url or env.get("GAS_WEBAPP_URL", "")).strip()

    frame_customer = str(args.gas_customer_url or "").strip()
    frame_acquisition = str(args.gas_acquisition_url or "").strip()
    if not frame_customer and gas_exec:
        frame_customer = f"{gas_exec}?mode=customer"
    if not frame_acquisition and gas_exec:
        frame_acquisition = f"{gas_exec}?mode=acquisition"

    if not frame_customer:
        frame_customer = str(env.get("GAS_YANGDO_WEBAPP_URL", "")).strip() or "https://seoulmna.kr/yangdo-ai-customer/"
    if not frame_acquisition:
        frame_acquisition = str(env.get("GAS_ACQUISITION_WEBAPP_URL", "")).strip() or "https://seoulmna.kr/ai-license-acquisition-calculator/"

    report: Dict[str, Any] = {
        "generated_at": now,
        "ok": True,
        "kr_only_mode": bool(kr_only_mode),
        "resolved": {
            "customer_page": customer_page,
            "acquisition_page": acquisition_page,
            "frame_customer": frame_customer,
            "frame_acquisition": frame_acquisition,
        },
        "steps": [],
        "checks": [],
        "blocking_issues": [],
        "warnings": [],
    }

    using_gas_frames = _looks_like_gas_url(frame_customer) and _looks_like_gas_url(frame_acquisition)
    if not using_gas_frames:
        report["warnings"].append("frame_urls_not_gas_exec_using_fallback_or_custom_domain")
        if args.require_gas:
            report["ok"] = False
            report["blocking_issues"].append("require_gas_enabled_but_frame_urls_not_gas_exec")
            out_path = (ROOT / args.report).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[saved] {out_path}")
            print("[ok] False")
            print("[blocking] require_gas_enabled_but_frame_urls_not_gas_exec")
            return 1

    if kr_only_mode:
        report["warnings"].append("kr_only_mode_enabled_co_steps_skipped")

    if not args.skip_gas_bundle:
        step = _run(
            _py_cmd(
                [
                    "scripts/generate_gas_masterpiece_bundle.py",
                    "--max-train-rows",
                    str(max(1, int(args.max_train_rows))),
                    "--report",
                    "logs/gas_masterpiece_bundle_latest.json",
                ]
            ),
            timeout_sec=720,
        )
        step["name"] = "generate_gas_bundle"
        report["steps"].append(step)
        if not step.get("ok"):
            report["ok"] = False
            report["blocking_issues"].append("generate_gas_bundle_failed")

    if not kr_only_mode:
        step_content = _run(
            _py_cmd(
                [
                    "scripts/deploy_co_content_pages.py",
                    "--base-url",
                    co_base,
                    "--customer-co-id",
                    str(args.customer_co_id),
                    "--acquisition-co-id",
                    str(args.acquisition_co_id),
                    "--report",
                    "logs/co_content_pages_deploy_latest.json",
                ]
            ),
            timeout_sec=240,
        )
        step_content["name"] = "deploy_co_content_pages"
        report["steps"].append(step_content)
        if not step_content.get("ok"):
            report["ok"] = False
            report["blocking_issues"].append("deploy_co_content_pages_failed")

        step_snippet = _run(
            _py_cmd(
                ([
                    "scripts/prepare_co_global_banner_snippet.py",
                    "--target-url",
                    customer_page,
                    "--acquisition-url",
                    acquisition_page,
                    "--frame-customer-url",
                    frame_customer,
                    "--frame-acquisition-url",
                    frame_acquisition,
                    "--snippet-out",
                    "logs/co_global_banner_snippet.html",
                    "--guide-out",
                    "logs/co_global_banner_apply_guide.md",
                ] + (["--show-main-banner"] if args.show_main_banner else []))
            ),
            timeout_sec=120,
        )
        step_snippet["name"] = "prepare_banner_snippet"
        report["steps"].append(step_snippet)
        if not step_snippet.get("ok"):
            report["ok"] = False
            report["blocking_issues"].append("prepare_banner_snippet_failed")

        step_apply = _run(
            _py_cmd(
                [
                    "scripts/apply_co_global_banner_admin.py",
                    "--base-url",
                    co_base,
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
            report["ok"] = False
            report["blocking_issues"].append("apply_banner_admin_failed")

    if args.persist_env:
        updates = {
            "GAS_YANGDO_WEBAPP_URL": frame_customer,
            "GAS_ACQUISITION_WEBAPP_URL": frame_acquisition,
        }
        if gas_exec:
            updates["GAS_WEBAPP_URL"] = gas_exec
        _write_env(ROOT / ".env", updates)
        report["env_updated"] = updates

    checks: List[Dict[str, Any]] = []
    if not kr_only_mode:
        # Verification
        checks = [
            _check_url(
                f"{co_base}/",
                [
                    "SEOULMNA GLOBAL BANNER START",
                    frame_customer,
                    frame_acquisition,
                    customer_page,
                    "smna-global-banner-rail",
                ],
            ),
            _check_url(
                customer_page,
                [
                    "smna-calc-bridge",
                    frame_customer,
                    "AI 양도가 산정 계산기",
                ],
            ),
            _check_url(
                acquisition_page,
                [
                    "smna-calc-bridge",
                    frame_acquisition,
                    "AI 건설업 신규등록 비용 산정 계산기",
                ],
            ),
        ]
    report["checks"] = checks
    if not all(bool(c.get("ok")) for c in checks):
        report["ok"] = False
        report["blocking_issues"].append("post_deploy_verify_failed")

    if not args.skip_runtime_verify:
        runtime_cmd = [
            "scripts/verify_calculator_runtime.py",
            "--allow-no-browser",
            "--report",
            "logs/verify_calculator_runtime_latest.json",
        ]
        if kr_only_mode:
            runtime_cmd.append("--kr-only")
        else:
            runtime_cmd.extend(
                [
                    "--co-base",
                    co_base,
                    "--customer-co-id",
                    str(args.customer_co_id),
                    "--acquisition-co-id",
                    str(args.acquisition_co_id),
                    "--frame-customer",
                    frame_customer + ("?from=co" if "?" not in frame_customer else "&from=co"),
                    "--frame-acquisition",
                    frame_acquisition + ("?from=co" if "?" not in frame_acquisition else "&from=co"),
                ]
            )
        runtime_step = _run(
            _py_cmd(runtime_cmd),
            timeout_sec=240,
        )
        runtime_step["name"] = "runtime_verify"
        report["steps"].append(runtime_step)
        if not runtime_step.get("ok"):
            report["ok"] = False
            report["blocking_issues"].append("runtime_verify_failed")

    out_path = (ROOT / args.report).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[saved] {out_path}")
    print(f"[ok] {report.get('ok')}")
    for step in report["steps"]:
        print(f"- {step.get('name')}: ok={step.get('ok')} rc={step.get('returncode')}")
    for chk in checks:
        print(f"- verify {chk.get('url')}: ok={chk.get('ok')} status={chk.get('status_code')} len={chk.get('length')}")
    if report["blocking_issues"]:
        print("[blocking]", ", ".join(report["blocking_issues"]))

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
