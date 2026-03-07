from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"

REGRESSION_PATH = LOG_DIR / "yangdo_operational_regression_latest.json"
STATUS_PATH = LOG_DIR / "secure_api_status_latest.json"
WP_PAGES_PATH = LOG_DIR / "wp_private_ai_pages_latest.json"
WP_HUB_PATH = LOG_DIR / "wp_private_ai_hub_latest.json"
SETTLEMENT_MATRIX_PATH = LOG_DIR / "special_sector_settlement_matrix_latest.json"

OUT_JSON = LOG_DIR / "yangdo_ops_dashboard_latest.json"
OUT_MD = LOG_DIR / "yangdo_ops_dashboard_latest.md"


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


def _to_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def _round4(value: Any) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    return round(float(num), 4)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_sector_label(raw: Any) -> str:
    text = str(raw or "")
    if "전기" in text or "?꾧린" in text:
        return "전기"
    if "소방" in text or "?뚮갑" in text:
        return "소방"
    if "정보통신" in text or "?뺣낫?듭떊" in text or "?듭떊" in text:
        return "정보통신"
    return text or "unknown"


def _clean_reorg_label(raw: Any) -> str:
    text = str(raw or "")
    if "포괄" in text or "?ш큵" in text or "comprehensive" in text.lower():
        return "포괄"
    if "분할" in text or "합병" in text or "遺꾪븷" in text or "?⑸퀝" in text:
        return "분할/합병"
    return text or "unknown"


def _service_rows(status_snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = status_snapshot.get("rows")
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "api": str(row.get("Api") or ""),
                "port": int(row.get("Port") or 0),
                "status": str(row.get("Status") or ""),
                "health_ok": bool(row.get("HealthOk")),
                "health_status": int(row.get("HealthStatus") or 0),
                "listener_pid": int(row.get("ListenerPid") or 0),
                "worker_count": int(row.get("WorkerCount") or 0),
                "shim_count": int(row.get("ShimCount") or 0),
                "launcher_count": int(row.get("LauncherCount") or 0),
            }
        )
    return out


def _live_cases(regression: Dict[str, Any]) -> List[Dict[str, Any]]:
    smoke = regression.get("live_blackbox_smoke")
    if not isinstance(smoke, dict):
        return []
    cases = smoke.get("cases")
    if not isinstance(cases, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in cases:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "name": str(row.get("name") or ""),
                "ok": bool(row.get("ok")),
                "publication_mode": str(row.get("publication_mode") or ""),
                "selected_mode": str(row.get("selected_mode") or ""),
                "resolved_auto_mode": str(row.get("resolved_auto_mode") or ""),
                "total_transfer_value_eok": _round4(row.get("total_transfer_value_eok")),
                "estimated_cash_due_eok": _round4(row.get("estimated_cash_due_eok")),
                "realizable_balance_eok": _round4(row.get("realizable_balance_eok")),
                "settlement_scenario_count": int(row.get("settlement_scenario_count") or 0),
            }
        )
    return out


def _private_pages(page_report: Dict[str, Any], hub_report: Dict[str, Any]) -> Dict[str, Any]:
    pages = page_report.get("pages") if isinstance(page_report.get("pages"), dict) else {}
    hub = hub_report.get("hub") if isinstance(hub_report.get("hub"), dict) else {}
    children = hub_report.get("children") if isinstance(hub_report.get("children"), dict) else {}
    return {
        "hub": {
            "status": str(hub.get("status") or ""),
            "url": str(hub.get("url") or ""),
            "public_http_status": int(hub.get("public_http_status") or 0),
        },
        "yangdo_owner": {
            "status": str((pages.get("yangdo_owner") or {}).get("wp_status") or ""),
            "url": str((pages.get("yangdo_owner") or {}).get("url") or ""),
            "public_http_status": int((pages.get("yangdo_owner") or {}).get("public_http_status") or 0),
        },
        "permit_private": {
            "status": str((pages.get("permit_private") or {}).get("wp_status") or ""),
            "url": str((pages.get("permit_private") or {}).get("url") or ""),
            "public_http_status": int((pages.get("permit_private") or {}).get("public_http_status") or 0),
        },
        "children": {
            key: {
                "status": str((value or {}).get("status") or ""),
                "parent": int((value or {}).get("parent") or 0),
            }
            for key, value in children.items()
            if isinstance(value, dict)
        },
    }


def _special_sector_snapshot(matrix_report: Dict[str, Any]) -> Dict[str, Any]:
    overall = matrix_report.get("overall") if isinstance(matrix_report.get("overall"), dict) else {}
    summary: Dict[str, Any] = {}
    for reorg_mode, row in overall.items():
        if not isinstance(row, dict):
            continue
        auto = row.get("auto") if isinstance(row.get("auto"), dict) else {}
        credit = row.get("credit_transfer") if isinstance(row.get("credit_transfer"), dict) else {}
        none = row.get("none") if isinstance(row.get("none"), dict) else {}
        summary[_clean_reorg_label(reorg_mode)] = {
            "auto_count": int(auto.get("count") or 0),
            "auto_publication_counts": auto.get("publication_counts") or {},
            "auto_median_cash_due_eok": _round4(auto.get("median_estimated_cash_due_eok")),
            "auto_median_balance_eok": _round4(auto.get("median_realizable_balance_eok")),
            "credit_extra_cash_reduction_eok": _round4(
                (_to_float(auto.get("median_estimated_cash_due_eok")) or 0.0)
                - (_to_float(credit.get("median_estimated_cash_due_eok")) or 0.0)
            ),
            "loan_vs_none_cash_reduction_eok": _round4(
                (_to_float(none.get("median_estimated_cash_due_eok")) or 0.0)
                - (_to_float(auto.get("median_estimated_cash_due_eok")) or 0.0)
            ),
        }
    return summary


def build_dashboard() -> Dict[str, Any]:
    regression = _load_json(REGRESSION_PATH)
    status_snapshot = _load_json(STATUS_PATH)
    page_report = _load_json(WP_PAGES_PATH)
    hub_report = _load_json(WP_HUB_PATH)
    matrix_report = _load_json(SETTLEMENT_MATRIX_PATH)

    services = _service_rows(status_snapshot)
    live_cases = _live_cases(regression)
    combo = ((regression.get("combo_sanity") or {}).get("result") or {}) if isinstance(regression.get("combo_sanity"), dict) else {}
    browser = ((regression.get("browser_smoke") or {}).get("result") or {}) if isinstance(regression.get("browser_smoke"), dict) else {}

    dashboard = {
        "generated_at": _now(),
        "overall_ok": bool(regression.get("ok")) and all(row.get("status") == "OK" for row in services),
        "sources": {
            "regression": str(REGRESSION_PATH),
            "status": str(STATUS_PATH),
            "wp_pages": str(WP_PAGES_PATH),
            "wp_hub": str(WP_HUB_PATH),
            "special_sector_matrix": str(SETTLEMENT_MATRIX_PATH),
        },
        "regression": {
            "ok": bool(regression.get("ok")),
            "generated_at": regression.get("generated_at"),
            "blocking_issues": list(regression.get("blocking_issues") or []),
        },
        "services": services,
        "live_blackbox_cases": live_cases,
        "combo_sanity": combo,
        "browser_smoke": {
            "ok": bool(browser.get("ok")),
            "generated_at": browser.get("generated_at"),
            "yangdo_ok": bool((((browser.get("checks") or {}).get("yangdo") or {}).get("ok"))),
            "permit_ok": bool((((browser.get("checks") or {}).get("permit") or {}).get("ok"))),
        },
        "private_pages": _private_pages(page_report, hub_report),
        "special_sector_snapshot": _special_sector_snapshot(matrix_report),
    }
    return dashboard


def to_markdown(dashboard: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Yangdo Operational Dashboard")
    lines.append("")
    lines.append(f"- generated_at: {dashboard.get('generated_at')}")
    lines.append(f"- overall_ok: {dashboard.get('overall_ok')}")
    reg = dashboard.get("regression") or {}
    lines.append(f"- regression_ok: {reg.get('ok')}")
    lines.append(f"- regression_generated_at: {reg.get('generated_at')}")
    lines.append(f"- blocking_issues: {reg.get('blocking_issues')}")
    lines.append("")
    lines.append("## Services")
    for row in dashboard.get("services") or []:
        lines.append(
            f"- {row.get('api')}: status={row.get('status')} health={row.get('health_status')} "
            f"pid={row.get('listener_pid')} workers={row.get('worker_count')} shims={row.get('shim_count')} launchers={row.get('launcher_count')}"
        )
    lines.append("")
    lines.append("## Live Blackbox Cases")
    for row in dashboard.get("live_blackbox_cases") or []:
        lines.append(
            f"- {row.get('name')}: ok={row.get('ok')} publication={row.get('publication_mode')} "
            f"selected={row.get('selected_mode')} auto={row.get('resolved_auto_mode')} "
            f"total={row.get('total_transfer_value_eok')} cash={row.get('estimated_cash_due_eok')} balance={row.get('realizable_balance_eok')}"
        )
    lines.append("")
    lines.append("## Private Pages")
    private_pages = dashboard.get("private_pages") or {}
    hub = private_pages.get("hub") or {}
    lines.append(
        f"- hub: status={hub.get('status')} public_http_status={hub.get('public_http_status')} url={hub.get('url')}"
    )
    for key in ("yangdo_owner", "permit_private"):
        row = private_pages.get(key) or {}
        lines.append(
            f"- {key}: status={row.get('status')} public_http_status={row.get('public_http_status')} url={row.get('url')}"
        )
    lines.append("")
    lines.append("## Special Sector Snapshot")
    for reorg_mode, row in (dashboard.get("special_sector_snapshot") or {}).items():
        lines.append(
            f"- {reorg_mode}: auto_count={row.get('auto_count')} auto_publication={row.get('auto_publication_counts')} "
            f"auto_cash={row.get('auto_median_cash_due_eok')} auto_balance={row.get('auto_median_balance_eok')} "
            f"loan_vs_none_reduction={row.get('loan_vs_none_cash_reduction_eok')} credit_extra={row.get('credit_extra_cash_reduction_eok')}"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    dashboard = build_dashboard()
    OUT_JSON.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(to_markdown(dashboard), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(OUT_JSON), "md": str(OUT_MD)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
