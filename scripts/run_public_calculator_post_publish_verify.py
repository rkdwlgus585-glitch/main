#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
VERIFY_RUNTIME_REPORT = LOG_DIR / "verify_calculator_runtime_latest.json"
DEFAULT_REPORT = LOG_DIR / "public_calculator_post_publish_verify_latest.json"
DEFAULT_SUMMARY_JSON = LOG_DIR / "public_calculator_publish_summary_latest.json"
DEFAULT_SUMMARY_MD = LOG_DIR / "public_calculator_publish_summary_latest.md"
FIRST_PRINCIPLES_REPORT = LOG_DIR / "ai_platform_first_principles_review_latest.json"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _load_release_checklist() -> Dict[str, str]:
    data = _load_json(FIRST_PRINCIPLES_REPORT)
    checklist = data.get("release_checklist") if isinstance(data.get("release_checklist"), dict) else {}
    return {
        "do_now": str(checklist.get("do_now") or "").strip(),
        "hold": str(checklist.get("hold") or "").strip(),
        "falsification_test": str(checklist.get("falsification_test") or "").strip(),
    }


def _run(cmd: List[str], *, timeout: int = 1800) -> Dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(1, int(timeout)),
    )
    return {
        "command": cmd,
        "returncode": int(proc.returncode),
        "ok": proc.returncode == 0,
        "stdout": str(proc.stdout or ""),
        "stderr": str(proc.stderr or ""),
    }


def _trim(text: str, limit: int = 1600) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    head = max(250, limit // 2)
    return value[:head] + "\n... [trimmed] ...\n" + value[-head:]


def _select_checks(checks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    picked: Dict[str, Dict[str, Any]] = {}
    for row in checks:
        url = str(row.get("url") or "")
        kind = str(row.get("kind") or "")
        mode = str(row.get("mode") or "")
        if url.endswith("/yangdo-ai-customer/"):
            key = f"customer_{kind}"
        elif url.endswith("/ai-license-acquisition-calculator/"):
            key = f"permit_{kind}"
        else:
            continue
        if kind == "interaction" and mode:
            key = f"{key}_{mode}"
        picked[key] = {
            "ok": bool(row.get("ok")),
            "url": url,
            "kind": kind,
            "mode": mode,
            "status_code": int(row.get("status_code") or 0) if row.get("status_code") is not None else 0,
            "length": int(row.get("length") or 0) if row.get("length") is not None else 0,
            "error": str(row.get("error") or ""),
            "preflight": dict(row.get("preflight") or {}) if isinstance(row.get("preflight"), dict) else {},
        }
    return picked


def _surface_ok(selected: Dict[str, Dict[str, Any]], keys: List[str]) -> bool:
    rows = [selected.get(key) or {} for key in keys]
    return bool(rows) and all(bool(row.get("ok")) for row in rows)


def _summary_markdown(summary: Dict[str, Any]) -> str:
    release = summary.get("release_checklist") if isinstance(summary.get("release_checklist"), dict) else {}
    customer = summary.get("customer") if isinstance(summary.get("customer"), dict) else {}
    permit = summary.get("permit") if isinstance(summary.get("permit"), dict) else {}
    health = summary.get("health_contract") if isinstance(summary.get("health_contract"), dict) else {}
    lines = [
        "# Public Calculator Publish Summary",
        "",
        f"Updated: {summary.get('generated_at') or ''}",
        "",
        f"- Verdict: `{summary.get('one_line_verdict') or '(missing)'}`",
        f"- Overall ok: `{summary.get('ok')}`",
        f"- Health contract: `{health.get('text') or '(missing)'}`",
        "",
        "## Customer",
        f"- static: `{customer.get('static_ok')}`",
        f"- runtime: `{customer.get('runtime_ok')}`",
        f"- interaction: `{customer.get('interaction_ok')}`",
        f"- url: `{customer.get('url') or '(missing)'}`",
        "",
        "## Permit",
        f"- static: `{permit.get('static_ok')}`",
        f"- runtime: `{permit.get('runtime_ok')}`",
        f"- interaction: `{permit.get('interaction_ok')}`",
        f"- url: `{permit.get('url') or '(missing)'}`",
        f"- category_count: `{permit.get('category_count')}`",
        f"- focus_quick_count: `{permit.get('focus_quick_count')}`",
        f"- industry_count_after_search: `{permit.get('industry_count_after_search')}`",
        "",
        "## Release Checklist",
        f"- Do now: {release.get('do_now') or '(missing)'}",
        f"- Hold: {release.get('hold') or '(missing)'}",
        f"- Falsification test: {release.get('falsification_test') or '(missing)'}",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live public SeoulMNA calculator pages immediately after deploy.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--summary-json", default=str(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--summary-md", default=str(DEFAULT_SUMMARY_MD))
    parser.add_argument("--customer-url", default="https://seoulmna.kr/yangdo-ai-customer/")
    parser.add_argument("--permit-url", default="https://seoulmna.kr/ai-license-acquisition-calculator/")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "verify_calculator_runtime.py"),
        "--kr-only",
        "--kr-customer-url",
        str(args.customer_url),
        "--kr-acquisition-url",
        str(args.permit_url),
        "--report",
        str(VERIFY_RUNTIME_REPORT),
    ]
    run = _run(cmd, timeout=1800)
    verify = _load_json(VERIFY_RUNTIME_REPORT)
    checks = list(verify.get("checks") or []) if isinstance(verify.get("checks"), list) else []
    selected = _select_checks([row for row in checks if isinstance(row, dict)])
    blocking_issues: List[str] = []
    if not bool(run.get("ok")):
        blocking_issues.append("verify_runtime_command_failed")
    if not bool(verify.get("ok")):
        blocking_issues.append("verify_runtime_report_failed")
    for name, row in selected.items():
        if not bool(row.get("ok")):
            blocking_issues.append(f"{name}_failed")

    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": not blocking_issues,
        "blocking_issues": blocking_issues,
        "command": cmd,
        "command_ok": bool(run.get("ok")),
        "command_returncode": int(run.get("returncode") or 0),
        "stdout_preview": _trim(str(run.get("stdout") or "")),
        "stderr_preview": _trim(str(run.get("stderr") or "")),
        "verify_report_path": str(VERIFY_RUNTIME_REPORT),
        "health_contract": dict(verify.get("health_contract") or {}),
        "selected_checks": selected,
        "brainstorming": {
            "goal": "public deploy 직후 live URL이 실제로 살아 있는지, permit/customer 양쪽을 같은 계약으로 즉시 검증",
            "design": [
                "public deploy 성공과 public runtime 정상은 별개로 본다",
                "post-publish 검증은 기존 verify_calculator_runtime 결과를 재사용해 중복 구현을 피한다",
                "운영자에게는 customer/permit 핵심 체크만 축약해서 보여준다",
            ],
        },
    }
    customer_ok = _surface_ok(selected, ["customer_static", "customer_runtime", "customer_interaction_customer"])
    permit_ok = _surface_ok(selected, ["permit_static", "permit_runtime", "permit_interaction_acquisition"])
    health_contract = dict(verify.get("health_contract") or {})
    health_ok = bool(health_contract.get("ok"))
    permit_preflight = dict((selected.get("permit_interaction_acquisition") or {}).get("preflight") or {})
    release_checklist = _load_release_checklist()
    summary: Dict[str, Any] = {
        "generated_at": report["generated_at"],
        "ok": bool(report["ok"]) and customer_ok and permit_ok and health_ok,
        "one_line_verdict": (
            ("GREEN" if bool(report["ok"]) and customer_ok and permit_ok and health_ok else "CHECK")
            + " | "
            + f"publicCustomer={'ok' if customer_ok else 'check'} "
            + f"publicPermit={'ok' if permit_ok else 'check'} "
            + f"health={'ok' if health_ok else 'check'}"
        ),
        "health_contract": {
            "ok": health_ok,
            "text": str(health_contract.get("text") or ""),
            "generated_at": str(health_contract.get("generated_at") or ""),
        },
        "customer": {
            "url": str(args.customer_url),
            "static_ok": bool((selected.get("customer_static") or {}).get("ok")),
            "runtime_ok": bool((selected.get("customer_runtime") or {}).get("ok")),
            "interaction_ok": bool((selected.get("customer_interaction_customer") or {}).get("ok")),
        },
        "permit": {
            "url": str(args.permit_url),
            "static_ok": bool((selected.get("permit_static") or {}).get("ok")),
            "runtime_ok": bool((selected.get("permit_runtime") or {}).get("ok")),
            "interaction_ok": bool((selected.get("permit_interaction_acquisition") or {}).get("ok")),
            "category_count": int(permit_preflight.get("category_count") or 0),
            "focus_quick_count": int(permit_preflight.get("focus_quick_count") or 0),
            "industry_count_after_search": int(permit_preflight.get("industry_count_after_search") or 0),
            "step_title": str(permit_preflight.get("step_title") or ""),
        },
        "release_checklist": release_checklist,
        "sources": {
            "verify_report_path": str(VERIFY_RUNTIME_REPORT),
            "first_principles_path": str(FIRST_PRINCIPLES_REPORT),
        },
    }
    summary_json_path = Path(str(args.summary_json)).resolve()
    summary_md_path = Path(str(args.summary_md)).resolve()
    _save_json(summary_json_path, summary)
    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.write_text(_summary_markdown(summary), encoding="utf-8")
    report["summary_json_path"] = str(summary_json_path)
    report["summary_md_path"] = str(summary_md_path)
    report["summary"] = summary
    _save_json(Path(str(args.report)).resolve(), report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    try:
        sys.stdout.write(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8", errors="replace"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
