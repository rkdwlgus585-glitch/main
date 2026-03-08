from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"
DEFAULT_REPORT = LOG_DIR / "yangdo_operational_regression_latest.json"
STATUS_JSON = LOG_DIR / "secure_api_status_latest.json"
SMOKE_JSON = LOG_DIR / "calculator_browser_smoke_latest.json"
PERMIT_WIZARD_JSON = LOG_DIR / "permit_wizard_sanity_latest.json"
PERMIT_STEP_SMOKE_JSON = LOG_DIR / "permit_step_transition_smoke_latest.json"
PARTNER_API_SMOKE_JSON = LOG_DIR / "partner_api_contract_smoke_latest.json"
ENV_PATH = ROOT / ".env"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _elapsed_seconds(started_at: float) -> float:
    return round(time.perf_counter() - started_at, 3)


def _run_command(cmd: List[str], *, cwd: Path | None = None, timeout: int = 240) -> Dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(1, int(timeout)),
    )
    return {
        "command": cmd,
        "returncode": int(proc.returncode),
        "stdout": str(proc.stdout or ""),
        "stderr": str(proc.stderr or ""),
        "ok": proc.returncode == 0,
    }


def _run_powershell(script_path: Path, *args: str, timeout: int = 240) -> Dict[str, Any]:
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        *[str(x) for x in args if str(x or "").strip()],
    ]
    return _run_command(cmd, cwd=ROOT, timeout=timeout)


def _load_json(path: Path) -> Dict[str, Any]:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except Exception:
            continue
    return {}


def _load_json_retry(path: Path, *, retries: int = 5, delay_seconds: float = 0.35) -> Dict[str, Any]:
    import time

    for _ in range(max(1, int(retries))):
        loaded = _load_json(path)
        if loaded:
            return loaded
        time.sleep(max(0.05, float(delay_seconds)))
    return {}


def _read_env_value(key: str) -> str:
    raw = str(os.getenv(key) or "").strip()
    if raw:
        return raw
    if not ENV_PATH.exists():
        return ""
    try:
        for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            txt = str(line or "").strip()
            if not txt or txt.startswith("#") or "=" not in txt:
                continue
            env_key, env_val = txt.split("=", 1)
            if str(env_key).strip() != key:
                continue
            return str(env_val).strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
    timeout: int = 20,
) -> Tuple[int, Dict[str, str], Dict[str, Any], str]:
    req_headers = dict(headers or {})
    body = None
    if payload is not None:
        req_headers.setdefault("Content-Type", "application/json; charset=utf-8")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=max(1, int(timeout))) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), dict(resp.headers.items()), _safe_json(raw), raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), dict(exc.headers.items()), _safe_json(raw), raw
    except urllib.error.URLError as exc:
        message = str(exc.reason or exc)
        return 0, {}, {"ok": False, "error": "request_failed", "details": message}, message
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        return 0, {}, {"ok": False, "error": "request_failed", "details": message}, message


def _safe_json(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_live_case_payload(case: Dict[str, Any]) -> Dict[str, Any]:
    sales3 = float(case.get("sales3_eok") or 0.0)
    return {
        "mode": "owner",
        "channel_id": "seoul_web",
        "source": "yangdo_operational_regression",
        "request_id": f"ops_{uuid.uuid4().hex[:12]}",
        "requested_at": _now(),
        "license_text": str(case.get("license_text") or ""),
        "reorg_mode": str(case.get("reorg_mode") or ""),
        "scale_search_mode": "sales",
        "sales_input_mode": "sales3",
        "specialty": float(case.get("specialty_eok") or 0.0),
        "sales3_eok": sales3,
        "sales5_eok": round(max(sales3, 0.0) * 1.45, 4),
        "balance_eok": float(case.get("balance_eok") or 0.0),
        "balance_usage_mode": str(case.get("balance_usage_mode") or "auto"),
        "capital_eok": float(case.get("capital_eok") or 3.5),
        "surplus_eok": float(case.get("surplus_eok") or 0.8),
        "debt_ratio": float(case.get("debt_ratio") or 120.0),
        "liq_ratio": float(case.get("liq_ratio") or 180.0),
        "company_type": "주식회사",
        "credit_level": "B",
        "admin_history": "",
        "ok_capital": True,
        "ok_engineer": True,
        "ok_office": True,
        "missing_critical": [],
        "missing_guide": [],
        "provided_signals": 4,
    }


def _special_sector_live_smoke(*, api_base_url: str, api_key: str) -> Dict[str, Any]:
    cases = [
        {
            "name": "electric_auto_wrap",
            "license_text": "전기공사업",
            "reorg_mode": "포괄",
            "specialty_eok": 18.0,
            "sales3_eok": 12.0,
            "balance_eok": 0.8,
            "balance_usage_mode": "auto",
            "expected_auto_mode": "loan_withdrawal",
        },
        {
            "name": "telecom_auto_wrap",
            "license_text": "정보통신공사업",
            "reorg_mode": "포괄",
            "specialty_eok": 14.0,
            "sales3_eok": 9.5,
            "balance_eok": 0.55,
            "balance_usage_mode": "auto",
            "expected_auto_mode": "loan_withdrawal",
        },
        {
            "name": "telecom_auto_low_balance_none",
            "license_text": "정보통신공사업",
            "reorg_mode": "포괄",
            "specialty_eok": 15.0,
            "sales3_eok": 8.0,
            "balance_eok": 0.02,
            "balance_usage_mode": "auto",
            "expected_auto_mode": "none",
        },
        {
            "name": "fire_auto_tiny_balance",
            "license_text": "소방시설공사업",
            "reorg_mode": "포괄",
            "specialty_eok": 11.0,
            "sales3_eok": 6.0,
            "balance_eok": 0.05,
            "balance_usage_mode": "auto",
            "expected_auto_mode": "none",
        },
        {
            "name": "fire_split_auto_low_balance_none",
            "license_text": "소방시설공사업",
            "reorg_mode": "분할/합병",
            "specialty_eok": 11.0,
            "sales3_eok": 6.0,
            "balance_eok": 0.09,
            "balance_usage_mode": "auto",
            "expected_auto_mode": "none",
        },
        {
            "name": "electric_credit_transfer",
            "license_text": "전기공사업",
            "reorg_mode": "포괄",
            "specialty_eok": 18.0,
            "sales3_eok": 12.0,
            "balance_eok": 0.8,
            "balance_usage_mode": "credit_transfer",
            "expected_selected_mode": "credit_transfer",
        },
    ]
    out: Dict[str, Any] = {
        "base_url": str(api_base_url or "").rstrip("/"),
        "ok": False,
        "api_key_present": bool(str(api_key or "").strip()),
        "cases": [],
        "blocking_issues": [],
    }
    if not out["api_key_present"]:
        out["blocking_issues"].append("missing_blackbox_api_key")
        return out

    headers = {
        "X-API-Key": str(api_key or ""),
        "Origin": "https://seoulmna.kr",
        "X-Request-Id": f"ops_{uuid.uuid4().hex[:12]}",
    }

    for case in cases:
        payload = _build_live_case_payload(case)
        status, resp_headers, data, raw_text = _request_json(
            f"{out['base_url']}/estimate",
            method="POST",
            payload=payload,
            headers=headers,
            timeout=20,
        )
        settlement_policy = data.get("settlement_policy") if isinstance(data.get("settlement_policy"), dict) else {}
        settlement_scenarios = data.get("settlement_scenarios") if isinstance(data.get("settlement_scenarios"), list) else []
        selected_mode = str(data.get("balance_usage_mode") or "")
        requested_mode = str(data.get("balance_usage_mode_requested") or "")
        resolved_auto_mode = str(settlement_policy.get("resolved_auto_mode") or "")
        total_value = _to_float(data.get("total_transfer_value_eok"))
        cash_due = _to_float(data.get("estimated_cash_due_eok"))
        realizable_balance = _to_float(data.get("realizable_balance_eok"))
        credit_case = next((row for row in settlement_scenarios if str(row.get("input_mode") or "") == "credit_transfer"), {})
        auto_case = next((row for row in settlement_scenarios if str(row.get("input_mode") or "") == "auto"), {})
        none_case = next((row for row in settlement_scenarios if str(row.get("input_mode") or "") == "none"), {})
        credit_cash = _to_float(credit_case.get("estimated_cash_due_eok"))
        auto_cash = _to_float(auto_case.get("estimated_cash_due_eok"))
        none_cash = _to_float(none_case.get("estimated_cash_due_eok"))

        checks = [
            {"name": "http_status_ok", "ok": 200 <= status < 300, "details": f"status={status}"},
            {"name": "body_ok", "ok": bool(data.get("ok"))},
            {"name": "publication_mode_present", "ok": bool(str(data.get("publication_mode") or "").strip())},
            {"name": "settlement_scenarios_present", "ok": len(settlement_scenarios) >= 2, "details": f"count={len(settlement_scenarios)}"},
            {"name": "cash_not_above_total", "ok": cash_due is None or total_value is None or cash_due <= total_value + 1e-9},
            {
                "name": "balance_not_negative",
                "ok": realizable_balance is None or realizable_balance >= -1e-9,
            },
            {
                "name": "scenario_cash_order",
                "ok": (
                    credit_cash is None
                    or auto_cash is None
                    or none_cash is None
                    or (credit_cash <= auto_cash + 1e-9 and auto_cash <= none_cash + 1e-9)
                ),
            },
        ]
        expected_auto_mode = str(case.get("expected_auto_mode") or "").strip()
        if expected_auto_mode:
            checks.append(
                {
                    "name": "resolved_auto_mode_match",
                    "ok": resolved_auto_mode == expected_auto_mode,
                    "details": f"expected={expected_auto_mode} actual={resolved_auto_mode}",
                }
            )
        expected_selected_mode = str(case.get("expected_selected_mode") or "").strip()
        if expected_selected_mode:
            checks.append(
                {
                    "name": "selected_mode_match",
                    "ok": selected_mode == expected_selected_mode,
                    "details": f"expected={expected_selected_mode} actual={selected_mode}",
                }
            )
        case_ok = all(bool(item.get("ok")) for item in checks)
        case_row = {
            "name": str(case.get("name") or ""),
            "request": {
                "license_text": payload.get("license_text"),
                "reorg_mode": payload.get("reorg_mode"),
                "specialty": payload.get("specialty"),
                "sales3_eok": payload.get("sales3_eok"),
                "balance_eok": payload.get("balance_eok"),
                "balance_usage_mode": payload.get("balance_usage_mode"),
            },
            "status": status,
            "ok": case_ok,
            "requested_mode": requested_mode,
            "selected_mode": selected_mode,
            "resolved_auto_mode": resolved_auto_mode,
            "publication_mode": data.get("publication_mode"),
            "confidence": data.get("confidence"),
            "total_transfer_value_eok": total_value,
            "estimated_cash_due_eok": cash_due,
            "realizable_balance_eok": realizable_balance,
            "settlement_scenario_count": len(settlement_scenarios),
            "checks": checks,
            "raw_excerpt": raw_text[:500],
            "response_headers": {
                "X-Api-Version": resp_headers.get("X-Api-Version"),
                "X-Service-Name": resp_headers.get("X-Service-Name"),
                "X-Response-Tier": resp_headers.get("X-Response-Tier"),
                "X-Request-Id": resp_headers.get("X-Request-Id"),
            },
        }
        out["cases"].append(case_row)
        if not case_ok:
            out["blocking_issues"].append(f"live_case_failed:{case_row['name']}")

    out["ok"] = not out["blocking_issues"]
    return out


def _to_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Yangdo operational loop: restart, health, live estimate, partner API contract smoke, combo sanity, browser smoke")
    parser.add_argument("--skip-restart", action="store_true", default=False)
    parser.add_argument("--skip-build", action="store_true", default=False)
    parser.add_argument("--headful", action="store_true", default=False)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "blocking_issues": [],
        "timings": {},
        "restart": {},
        "secure_status": {},
        "live_blackbox_smoke": {},
        "partner_api_contract_smoke": {},
        "combo_sanity": {},
        "permit_wizard_sanity": {},
        "permit_step_transition_smoke": {},
        "browser_smoke": {},
        "brainstorming": {
            "goal": "Keep the operational gate anchored on one loop: secure status, permit sanity, live estimate smoke, partner contract smoke, combo sanity, and browser smoke.",
            "design": [
                "Use PowerShell helpers for secure stack state so worker and launcher drift is caught first.",
                "Run permit sanity before browser smoke so broken generated HTML fails fast.",
                "Run permit step smoke separately from full browser smoke to isolate wizard transition regressions.",
                "Use special-sector live estimate cases for electric, telecom, and fire scenarios.",
                "Keep partner contract smoke explicit because it validates headers and health contract parity not covered by browser smoke.",
                "Record per-step timing so gate cost decisions are evidence-based.",
            ]
        },
    }

    try:
        total_started = time.perf_counter()
        if not args.skip_restart:
            started = time.perf_counter()
            report["restart"] = _run_powershell(ROOT / "scripts" / "restart_secure_api_stack.ps1", "-Target", "all", timeout=240)
            report["restart"]["duration_sec"] = _elapsed_seconds(started)
            report["timings"]["restart_sec"] = report["restart"]["duration_sec"]
            if not report["restart"].get("ok"):
                report["blocking_issues"].append("secure_restart_failed")

        started = time.perf_counter()
        status_cmd = _run_powershell(
            ROOT / "scripts" / "show_secure_api_stack_status.ps1",
            "-JsonPath",
            str(STATUS_JSON),
            timeout=120,
        )
        report["secure_status"]["command"] = status_cmd
        report["secure_status"]["snapshot"] = _load_json_retry(STATUS_JSON)
        report["secure_status"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["secure_status_sec"] = report["secure_status"]["duration_sec"]
        rows = report["secure_status"]["snapshot"].get("rows") if isinstance(report["secure_status"]["snapshot"], dict) else []
        if not rows or any(str(row.get("Status") or "") != "OK" for row in rows if isinstance(row, dict)):
            report["blocking_issues"].append("secure_status_not_ok")

        blackbox_key = _read_env_value("YANGDO_BLACKBOX_API_KEY")
        started = time.perf_counter()
        report["live_blackbox_smoke"] = _special_sector_live_smoke(api_base_url="http://127.0.0.1:8790", api_key=blackbox_key)
        report["live_blackbox_smoke"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["live_blackbox_smoke_sec"] = report["live_blackbox_smoke"]["duration_sec"]
        if not report["live_blackbox_smoke"].get("ok"):
            report["blocking_issues"].append("live_blackbox_smoke_failed")

        started = time.perf_counter()
        partner_cmd = _run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_partner_api_contract_smoke.py"),
                "--report",
                str(PARTNER_API_SMOKE_JSON),
            ],
            cwd=ROOT,
            timeout=240,
        )
        report["partner_api_contract_smoke"]["command"] = partner_cmd
        report["partner_api_contract_smoke"]["result"] = _load_json(PARTNER_API_SMOKE_JSON)
        report["partner_api_contract_smoke"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["partner_api_contract_smoke_sec"] = report["partner_api_contract_smoke"]["duration_sec"]
        if not partner_cmd.get("ok") or not bool((report["partner_api_contract_smoke"].get("result") or {}).get("ok")):
            report["blocking_issues"].append("partner_api_contract_smoke_failed")

        started = time.perf_counter()
        combo_cmd = _run_command(
            [sys.executable, str(ROOT / "scripts" / "run_calculator_combo_sanity.py"), "--acq-cases", "120", "--yangdo-cases", "200"],
            cwd=ROOT,
            timeout=240,
        )
        report["combo_sanity"]["command"] = combo_cmd
        report["combo_sanity"]["result"] = _safe_json(combo_cmd.get("stdout") or "")
        report["combo_sanity"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["combo_sanity_sec"] = report["combo_sanity"]["duration_sec"]
        if not combo_cmd.get("ok"):
            report["blocking_issues"].append("combo_sanity_failed")

        started = time.perf_counter()
        permit_cmd = _run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_permit_wizard_sanity.py"),
                *(["--skip-build"] if args.skip_build else []),
                "--report",
                str(PERMIT_WIZARD_JSON),
            ],
            cwd=ROOT,
            timeout=180,
        )
        report["permit_wizard_sanity"]["command"] = permit_cmd
        report["permit_wizard_sanity"]["result"] = _load_json(PERMIT_WIZARD_JSON)
        report["permit_wizard_sanity"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["permit_wizard_sanity_sec"] = report["permit_wizard_sanity"]["duration_sec"]
        if not permit_cmd.get("ok") or not bool((report["permit_wizard_sanity"].get("result") or {}).get("ok")):
            report["blocking_issues"].append("permit_wizard_sanity_failed")

        started = time.perf_counter()
        permit_step_cmd = _run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_permit_step_transition_smoke.py"),
                *(["--skip-build"] if args.skip_build else []),
                *(["--headful"] if args.headful else []),
                "--report",
                str(PERMIT_STEP_SMOKE_JSON),
            ],
            cwd=ROOT,
            timeout=300,
        )
        report["permit_step_transition_smoke"]["command"] = permit_step_cmd
        report["permit_step_transition_smoke"]["result"] = _load_json(PERMIT_STEP_SMOKE_JSON)
        report["permit_step_transition_smoke"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["permit_step_transition_smoke_sec"] = report["permit_step_transition_smoke"]["duration_sec"]
        if not permit_step_cmd.get("ok") or not bool((report["permit_step_transition_smoke"].get("result") or {}).get("ok")):
            report["blocking_issues"].append("permit_step_transition_smoke_failed")

        started = time.perf_counter()
        browser_cmd = _run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_calculator_browser_smoke.py"),
                *(["--skip-build"] if args.skip_build else []),
                *(["--headful"] if args.headful else []),
                "--report",
                str(SMOKE_JSON),
            ],
            cwd=ROOT,
            timeout=420,
        )
        report["browser_smoke"]["command"] = browser_cmd
        report["browser_smoke"]["result"] = _load_json(SMOKE_JSON)
        report["browser_smoke"]["duration_sec"] = _elapsed_seconds(started)
        report["timings"]["browser_smoke_sec"] = report["browser_smoke"]["duration_sec"]
        if not browser_cmd.get("ok") or not bool((report["browser_smoke"].get("result") or {}).get("ok")):
            report["blocking_issues"].append("browser_smoke_failed")

        report["total_duration_sec"] = _elapsed_seconds(total_started)
    except Exception as exc:  # noqa: BLE001
        report["blocking_issues"].append(str(exc))
        if "total_started" in locals():
            report["total_duration_sec"] = _elapsed_seconds(total_started)

    report["ok"] = not report["blocking_issues"]
    out_path = Path(str(args.report)).resolve()
    _save_json(out_path, report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    try:
        sys.stdout.write(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8", errors="replace"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
