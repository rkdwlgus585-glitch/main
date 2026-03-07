#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "logs" / "yangdo_consult_requests.sqlite3"
DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_THRESHOLDS = ROOT / "tenant_config" / "plan_thresholds.json"
DEFAULT_REPORT = ROOT / "logs" / "tenant_usage_billing_latest.json"


@dataclass
class TenantProfile:
    tenant_id: str
    display_name: str
    enabled: bool
    plan: str
    hosts: Tuple[str, ...]


def _normalize_host(raw: str) -> str:
    src = str(raw or "").strip().lower()
    if not src:
        return ""
    if "://" in src:
        src = urlparse(src).netloc.lower()
    if "@" in src:
        src = src.split("@", 1)[1]
    if ":" in src:
        src = src.split(":", 1)[0]
    return src.strip()


def _host_from_url(raw: str) -> str:
    src = str(raw or "").strip()
    if not src:
        return ""
    if "://" not in src and "." in src and " " not in src:
        src = f"https://{src}"
    try:
        parsed = urlparse(src)
    except Exception:
        return ""
    return _normalize_host(parsed.netloc)


def _load_registry(path: Path) -> Tuple[str, Dict[str, TenantProfile], Dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    default_tenant_id = str(data.get("default_tenant_id") or "").strip().lower()
    tenants_raw = data.get("tenants") if isinstance(data, dict) else []

    by_id: Dict[str, TenantProfile] = {}
    by_host: Dict[str, str] = {}
    if isinstance(tenants_raw, list):
        for raw in tenants_raw:
            if not isinstance(raw, dict):
                continue
            tenant_id = str(raw.get("tenant_id") or "").strip().lower()
            if not tenant_id:
                continue
            hosts: List[str] = []
            for h in (raw.get("hosts") or []):
                nh = _normalize_host(str(h))
                if nh:
                    hosts.append(nh)
            profile = TenantProfile(
                tenant_id=tenant_id,
                display_name=str(raw.get("display_name") or tenant_id).strip() or tenant_id,
                enabled=bool(raw.get("enabled", True)),
                plan=str(raw.get("plan") or "standard").strip().lower() or "standard",
                hosts=tuple(hosts),
            )
            by_id[tenant_id] = profile
            for host in profile.hosts:
                if host not in by_host:
                    by_host[host] = tenant_id
    return default_tenant_id, by_id, by_host


def _load_thresholds(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _month_range(year: int, month: int) -> Tuple[str, str]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start.strftime("%Y-%m-%dT00:00:00"), end.strftime("%Y-%m-%dT00:00:00")


def _normalize_mode(page_mode: str, source: str, page_url: str, raw_json: str = "") -> str:
    parts = [str(page_mode or ""), str(source or ""), str(page_url or ""), str(raw_json or "")]
    try:
        loaded = json.loads(str(raw_json or "")) if str(raw_json or "").strip() else {}
    except Exception:
        loaded = {}
    if isinstance(loaded, dict):
        parts.extend(
            [
                str(loaded.get("service_track", "")),
                str(loaded.get("business_domain", "")),
                str(loaded.get("source_mode", "")),
                str(loaded.get("legacy_page_mode", "")),
                str(loaded.get("legacy_source", "")),
            ]
        )
    blob = " ".join(parts).lower()
    if any(k in blob for k in ["permit_precheck", "acquisition", "permit", "newreg", "인허가", "신규등록"]):
        return "permit"
    if any(k in blob for k in ["yangdo", "transfer_price_estimation", "yangdo_transfer", "양도"]):
        return "yangdo"
    return "unknown"


def _is_ok_status(status: str) -> bool:
    s = str(status or "").strip().lower()
    if not s:
        return True
    return s in {"ok", "success", "done", "200"}


def _estimate_tokens(mode: str, ok: bool, token_model: Dict[str, int]) -> int:
    if not ok:
        return int(token_model.get("error", 200))
    if mode == "yangdo":
        return int(token_model.get("yangdo_ok", 1200))
    if mode == "permit":
        return int(token_model.get("permit_ok", 900))
    return int(token_model.get("unknown_ok", 700))


def _resolve_tenant_id(
    source: str,
    page_url: str,
    default_tenant_id: str,
    host_to_tenant: Dict[str, str],
    raw_json: str = "",
) -> str:
    try:
        loaded = json.loads(str(raw_json or "")) if str(raw_json or "").strip() else {}
    except Exception:
        loaded = {}
    if isinstance(loaded, dict):
        raw_tenant_id = str(loaded.get("tenant_id") or "").strip().lower()
        if raw_tenant_id:
            return raw_tenant_id

    host = _host_from_url(page_url)
    if not host:
        host = _host_from_url(source)

    tenant_id = host_to_tenant.get(host)
    if tenant_id:
        return tenant_id

    src = str(source or "").lower()
    if "seoulmna" in src and default_tenant_id:
        return default_tenant_id

    return "unknown"


def build_report(
    *,
    db_path: Path,
    registry_path: Path,
    thresholds_path: Path,
    year: int,
    month: int,
) -> Dict[str, object]:
    default_tenant_id, tenants_by_id, host_to_tenant = _load_registry(registry_path)
    thresholds = _load_thresholds(thresholds_path)

    token_model = dict((thresholds.get("token_estimates") or {}))
    pricing = dict((thresholds.get("pricing") or {}))
    plans = dict((thresholds.get("plans") or {}))

    month_start, month_end = _month_range(year, month)

    usage_rows: List[Tuple[str, str, str, str, str, str]] = []
    monthly_rows: List[Tuple[str, str, int, int, int, int]] = []
    data_warning = ""
    if db_path.exists():
        conn = sqlite3.connect(str(db_path), timeout=30)
        try:
            try:
                usage_rows = conn.execute(
                    """
                    SELECT COALESCE(page_mode, ''), COALESCE(status, ''), COALESCE(source, ''),
                           COALESCE(page_url, ''), COALESCE(received_at, ''), COALESCE(raw_json, '')
                    FROM usage_events
                    WHERE received_at >= ? AND received_at < ?
                    """,
                    (month_start, month_end),
                ).fetchall()
            except sqlite3.OperationalError:
                try:
                    usage_rows_legacy = conn.execute(
                        """
                        SELECT COALESCE(page_mode, ''), COALESCE(status, ''), COALESCE(source, ''),
                               COALESCE(page_url, ''), COALESCE(received_at, '')
                        FROM usage_events
                        WHERE received_at >= ? AND received_at < ?
                        """,
                        (month_start, month_end),
                    ).fetchall()
                    usage_rows = [(a, b, c, d, e, "") for a, b, c, d, e in usage_rows_legacy]
                except sqlite3.OperationalError:
                    usage_rows = []
                    data_warning = "usage_events table not found"
            try:
                monthly_rows = conn.execute(
                    """
                    SELECT COALESCE(tenant_id, ''), COALESCE(service, ''),
                           COALESCE(SUM(usage_events), 0), COALESCE(SUM(estimated_tokens), 0),
                           COALESCE(SUM(ok_events), 0), COALESCE(SUM(error_events), 0)
                    FROM tenant_usage_monthly
                    WHERE year_month = ?
                    GROUP BY tenant_id, service
                    """,
                    (f"{year:04d}-{month:02d}",),
                ).fetchall()
            except sqlite3.OperationalError:
                try:
                    monthly_rows_legacy = conn.execute(
                        """
                        SELECT COALESCE(tenant_id, ''), COALESCE(service, ''),
                               COALESCE(SUM(usage_events), 0), COALESCE(SUM(estimated_tokens), 0)
                        FROM tenant_usage_monthly
                        WHERE year_month = ?
                        GROUP BY tenant_id, service
                        """,
                        (f"{year:04d}-{month:02d}",),
                    ).fetchall()
                    monthly_rows = [(a, b, c, d, 0, 0) for a, b, c, d in monthly_rows_legacy]
                except sqlite3.OperationalError:
                    monthly_rows = []
        finally:
            conn.close()

    tenant_stats: Dict[str, Dict[str, object]] = {}
    for tenant_id, profile in tenants_by_id.items():
        tenant_stats[tenant_id] = {
            "tenant_id": tenant_id,
            "display_name": profile.display_name,
            "enabled": bool(profile.enabled),
            "plan": profile.plan,
            "usage_events": 0,
            "ok_events": 0,
            "error_events": 0,
            "estimated_tokens": 0,
            "estimated_input_tokens": 0,
            "estimated_output_tokens": 0,
            "unknown_host_events": 0,
        }

    if "unknown" not in tenant_stats:
        tenant_stats["unknown"] = {
            "tenant_id": "unknown",
            "display_name": "Unknown Tenant",
            "enabled": False,
            "plan": "unknown",
            "usage_events": 0,
            "ok_events": 0,
            "error_events": 0,
            "estimated_tokens": 0,
            "estimated_input_tokens": 0,
            "estimated_output_tokens": 0,
            "unknown_host_events": 0,
        }

    input_ratio = float(pricing.get("input_token_ratio", 0.7))
    input_ratio = max(0.0, min(1.0, input_ratio))

    for page_mode, status, source, page_url, _received_at, raw_json in usage_rows:
        tenant_id = _resolve_tenant_id(source, page_url, default_tenant_id, host_to_tenant, raw_json)
        bucket = tenant_stats.get(tenant_id)
        if bucket is None:
            bucket = tenant_stats["unknown"]

        mode = _normalize_mode(page_mode, source, page_url, raw_json)
        ok = _is_ok_status(status)
        tokens = _estimate_tokens(mode, ok, token_model)

        bucket["usage_events"] = int(bucket["usage_events"]) + 1
        if ok:
            bucket["ok_events"] = int(bucket["ok_events"]) + 1
        else:
            bucket["error_events"] = int(bucket["error_events"]) + 1

        bucket["estimated_tokens"] = int(bucket["estimated_tokens"]) + tokens
        in_tokens = int(round(tokens * input_ratio))
        out_tokens = max(0, int(tokens) - in_tokens)
        bucket["estimated_input_tokens"] = int(bucket["estimated_input_tokens"]) + in_tokens
        bucket["estimated_output_tokens"] = int(bucket["estimated_output_tokens"]) + out_tokens

        if tenant_id == "unknown":
            bucket["unknown_host_events"] = int(bucket["unknown_host_events"]) + 1

    monthly_rollups: Dict[str, Dict[str, Dict[str, int]]] = {}
    for tenant_id, service, usage_events, estimated_tokens, ok_events, error_events in monthly_rows:
        tenant_key = str(tenant_id or "").strip().lower() or "unknown"
        service_key = str(service or "").strip().lower() or "unknown"
        tenant_bucket = monthly_rollups.setdefault(tenant_key, {})
        tenant_bucket[service_key] = {
            "usage_events": int(usage_events or 0),
            "estimated_tokens": int(estimated_tokens or 0),
            "ok_events": int(ok_events or 0),
            "error_events": int(error_events or 0),
        }
        if tenant_key not in tenant_stats:
            tenant_stats[tenant_key] = {
                "tenant_id": tenant_key,
                "display_name": tenant_key,
                "enabled": False,
                "plan": str((tenants_by_id.get(tenant_key).plan if tenant_key in tenants_by_id else "unknown") or "unknown"),
                "usage_events": 0,
                "ok_events": 0,
                "error_events": 0,
                "estimated_tokens": 0,
                "estimated_input_tokens": 0,
                "estimated_output_tokens": 0,
                "unknown_host_events": 0,
            }

    rows: List[Dict[str, object]] = []
    total_tokens = 0
    total_api_cost = 0.0
    total_overage = 0.0

    in_rate = float(pricing.get("input_rate_per_1m", 0.4))
    out_rate = float(pricing.get("output_rate_per_1m", 1.6))

    for tenant_id, stats in tenant_stats.items():
        legacy_usage_events = int(stats["usage_events"])
        legacy_ok_events = int(stats["ok_events"])
        legacy_error_events = int(stats["error_events"])
        legacy_estimated_tokens = int(stats["estimated_tokens"])
        rollups = monthly_rollups.get(tenant_id) or {}
        authoritative_source = "usage_events"
        if rollups:
            stats["usage_events"] = sum(int((svc.get("usage_events", 0) or 0)) for svc in rollups.values())
            stats["ok_events"] = sum(int((svc.get("ok_events", 0) or 0)) for svc in rollups.values())
            stats["error_events"] = sum(int((svc.get("error_events", 0) or 0)) for svc in rollups.values())
            stats["estimated_tokens"] = sum(int((svc.get("estimated_tokens", 0) or 0)) for svc in rollups.values())
            in_tokens = int(round(int(stats["estimated_tokens"]) * input_ratio))
            out_tokens = max(0, int(stats["estimated_tokens"]) - in_tokens)
            stats["estimated_input_tokens"] = in_tokens
            stats["estimated_output_tokens"] = out_tokens
            authoritative_source = "tenant_usage_monthly"

        plan = str(stats.get("plan") or "unknown").strip().lower()
        policy = dict((plans.get(plan) or {}))

        included_tokens = int(policy.get("included_tokens", 0) or 0)
        warn_ratio = float(policy.get("warn_ratio", 0.8) or 0.8)
        max_events = int(policy.get("max_usage_events", 0) or 0)
        overage_per_1k = float(policy.get("overage_price_per_1k_usd", 0.0) or 0.0)
        upgrade_target = str(policy.get("upgrade_target") or "").strip()

        usage_events = int(stats["usage_events"])
        est_tokens = int(stats["estimated_tokens"])
        in_tokens = int(stats["estimated_input_tokens"])
        out_tokens = int(stats["estimated_output_tokens"])

        api_cost = (in_tokens / 1_000_000.0) * in_rate + (out_tokens / 1_000_000.0) * out_rate
        usage_ratio = (est_tokens / included_tokens) if included_tokens > 0 else 0.0
        overage_tokens = max(0, est_tokens - included_tokens) if included_tokens > 0 else 0
        overage_cost = (overage_tokens / 1000.0) * overage_per_1k if overage_per_1k > 0 else 0.0

        action = "normal"
        reason = ""
        if tenant_id == "unknown" and usage_events > 0:
            action = "investigate_unknown_host"
            reason = "host/origin 매핑 누락"
        elif not bool(stats.get("enabled", False)) and usage_events > 0:
            action = "disabled_tenant_activity"
            reason = "비활성 테넌트 트래픽 감지"
        elif max_events > 0 and usage_events > max_events:
            action = "review_limit_exceeded"
            reason = f"event 한도 초과({usage_events}>{max_events})"
        elif included_tokens > 0 and usage_ratio >= 1.0:
            action = "upgrade_or_overage_charge"
            reason = "포함 토큰 초과"
        elif included_tokens > 0 and usage_ratio >= warn_ratio:
            action = "usage_warning"
            reason = "임계치 경고 구간"

        row = {
            **stats,
            "legacy_usage_events": legacy_usage_events,
            "legacy_ok_events": legacy_ok_events,
            "legacy_error_events": legacy_error_events,
            "legacy_estimated_tokens": legacy_estimated_tokens,
            "authoritative_source": authoritative_source,
            "service_rollups": rollups,
            "included_tokens": included_tokens,
            "usage_ratio": round(usage_ratio, 4),
            "overage_tokens": int(overage_tokens),
            "api_cost_usd": round(api_cost, 4),
            "overage_cost_usd": round(overage_cost, 4),
            "recommended_action": action,
            "action_reason": reason,
            "upgrade_target": upgrade_target,
        }
        rows.append(row)

        total_tokens += est_tokens
        total_api_cost += api_cost
        total_overage += overage_cost

    rows.sort(key=lambda x: (str(x.get("recommended_action")) != "normal", int(x.get("estimated_tokens", 0))), reverse=True)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "period": {
            "year": int(year),
            "month": int(month),
            "range_start": month_start,
            "range_end": month_end,
        },
        "summary": {
            "tenant_count": len(rows),
            "usage_row_count": len(usage_rows),
            "monthly_rollup_row_count": len(monthly_rows),
            "total_estimated_tokens": int(total_tokens),
            "total_api_cost_usd": round(total_api_cost, 4),
            "total_overage_cost_usd": round(total_overage, 4),
            "action_required_count": sum(1 for r in rows if r.get("recommended_action") not in {"normal", "usage_warning"}),
            "warning_count": sum(1 for r in rows if r.get("recommended_action") == "usage_warning"),
            "data_warning": data_warning,
        },
        "tenants": rows,
    }


def run_report(
    *,
    db_path: Path,
    registry_path: Path,
    thresholds_path: Path,
    report_path: Path,
    year: Optional[int],
    month: Optional[int],
    strict: bool,
) -> int:
    now = datetime.now()
    y = int(year or now.year)
    m = int(month or now.month)

    report = build_report(
        db_path=db_path,
        registry_path=registry_path,
        thresholds_path=thresholds_path,
        year=y,
        month=m,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "report": str(report_path), "summary": report.get("summary")}, ensure_ascii=False))

    if strict and int(report["summary"]["action_required_count"]) > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build monthly tenant usage/billing report")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--year", type=int, default=0)
    parser.add_argument("--month", type=int, default=0)
    parser.add_argument("--strict", action="store_true", default=False)
    args = parser.parse_args()

    return run_report(
        db_path=Path(str(args.db)).resolve(),
        registry_path=Path(str(args.registry)).resolve(),
        thresholds_path=Path(str(args.thresholds)).resolve(),
        report_path=Path(str(args.report)).resolve(),
        year=int(args.year or 0) or None,
        month=int(args.month or 0) or None,
        strict=bool(args.strict),
    )


if __name__ == "__main__":
    raise SystemExit(main())
