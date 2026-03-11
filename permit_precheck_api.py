import argparse
import json
import math
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from core_engine.api_contract import normalize_v1_request
from core_engine.api_response import _compact, build_response_envelope, now_iso
from core_engine.sandbox import is_sandbox_request, sandbox_permit_response
from core_engine.tenant_gateway import TenantGateway
from core_engine.channel_profiles import ChannelRouter
from permit_diagnosis_calculator import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_RULES_PATH,
    _build_rule_index,
    _load_catalog,
    _load_rule_catalog,
    _prepare_ui_payload,
    _resolve_rule_for_industry,
    evaluate_registration_diagnosis,
)
from security_http import (
    DEFAULT_SECURITY_HEADERS,
    SecurityEventLogger,
    SlidingWindowRateLimiter,
    header_token,
    is_authorized_any,
    parse_key_values,
    parse_origin_allowlist,
    resolve_allow_origin,
    safe_client_ip,
)
from tenant_config.loader import load_channel_router, load_gateway
from scripts.widget_health_contract import load_widget_health_contract
from utils import load_config, setup_logger

CONFIG = load_config(
    {
        "PERMIT_PRECHECK_API_HOST": "0.0.0.0",
        "PERMIT_PRECHECK_API_PORT": "8792",
        "PERMIT_PRECHECK_ALLOW_ORIGINS": "https://seoulmna.kr,https://www.seoulmna.kr,https://seoulmna.co.kr,https://www.seoulmna.co.kr",
        "PERMIT_PRECHECK_API_KEY": "",
        "PERMIT_PRECHECK_ADMIN_API_KEY": "",
        "PERMIT_PRECHECK_MAX_BODY_BYTES": "65536",
        "PERMIT_PRECHECK_RATE_LIMIT_PER_MIN": "90",
        "PERMIT_PRECHECK_TRUST_X_FORWARDED_FOR": "false",
        "PERMIT_PRECHECK_SECURITY_LOG_FILE": "logs/security_permit_precheck_events.jsonl",
        "PERMIT_PRECHECK_USAGE_DB": "logs/permit_precheck_usage.sqlite3",
        "PLAN_THRESHOLDS_CONFIG": "tenant_config/plan_thresholds.json",
        "TENANT_GATEWAY_ENABLED": "true",
        "TENANT_GATEWAY_STRICT": "false",
        "TENANT_GATEWAY_CONFIG": "tenant_config/tenant_registry.json",
        "TENANT_GATEWAY_DEFAULT_TENANT": "",
        "CHANNEL_ROUTER_STRICT": "false",
        "CHANNEL_PROFILES_CONFIG": "tenant_config/channel_profiles.json",
    }
)

logger = setup_logger(name="permit_precheck_api")

SERVICE_NAME = "permit_precheck_api"

# ── Field truncation limits (chars) ──────────────────────────────────
_LIM_SERVICE_CODE: int = 80       # service_code, rule_id, request_id, etc.
_LIM_SERVICE_NAME: int = 200      # service_name, industry_name, missing_critical
_LIM_COVERAGE: int = 120          # coverage_status, mapping_confidence
_LIM_SOURCE: int = 100            # source field
_LIM_ERROR_TEXT: int = 1000       # error_text
_LIM_PAGE_URL: int = 500          # page_url
_LIM_RESPONSE_TIER: int = 30      # response_tier
_LIM_X_RESPONSE_TIER: int = 40    # X-Response-Tier header value
_LIM_X_TENANT_PLAN: int = 60      # X-Tenant-Plan header value


def _json_dumps_compact(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError):
        return "{}"


def _first_present(mapping: Dict[str, Any], *keys: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if key in mapping and mapping.get(key) is not None:
            return mapping.get(key)
    return None


def _coerce_bool_flag(value: Any) -> int | None:
    if isinstance(value, bool):
        return 1 if value else 0
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value == 1:
            return 1
        if value == 0:
            return 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return 1
    if text in {"0", "false", "no", "off", "n"}:
        return 0
    return None


def _coerce_int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(float(value))
    except (ValueError, TypeError, OverflowError):
        return None


def _coerce_float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if math.isnan(out):
        return None
    return out


def _canonical_permit_input_snapshot(inputs: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = {
        "service_code": _compact(_first_present(inputs, "service_code"), _LIM_SERVICE_CODE),
        "service_name": _compact(_first_present(inputs, "service_name", "industry_name"), _LIM_SERVICE_NAME),
        "industry_name": _compact(_first_present(inputs, "industry_name", "service_name"), _LIM_SERVICE_NAME),
        "rule_id": _compact(_first_present(inputs, "rule_id", "group_rule_id"), _LIM_SERVICE_CODE),
        "capital_eok": _coerce_float_or_none(_first_present(inputs, "capital_eok", "current_capital_eok")),
        "raw_capital_input": _compact(_first_present(inputs, "raw_capital_input", "capital_eok"), _LIM_SERVICE_CODE),
        "technicians_count": _coerce_int_or_none(
            _first_present(inputs, "technicians_count", "technicians", "current_technicians")
        ),
        "equipment_count": _coerce_int_or_none(
            _first_present(inputs, "equipment_count", "current_equipment_count")
        ),
        "deposit_days": _coerce_int_or_none(_first_present(inputs, "deposit_days", "current_deposit_days")),
        "qualification_count": _coerce_int_or_none(
            _first_present(inputs, "qualification_count", "current_qualification_count")
        ),
        "office_secured": _coerce_bool_flag(_first_present(inputs, "office_secured", "current_office_secured")),
        "facility_secured": _coerce_bool_flag(
            _first_present(inputs, "facility_secured", "current_facility_secured")
        ),
        "guarantee_secured": _coerce_bool_flag(
            _first_present(inputs, "guarantee_secured", "current_guarantee_secured")
        ),
        "insurance_secured": _coerce_bool_flag(
            _first_present(inputs, "insurance_secured", "current_insurance_secured")
        ),
        "qualification_secured": _coerce_bool_flag(
            _first_present(inputs, "qualification_secured", "current_qualification_secured")
        ),
        "document_ready": _coerce_bool_flag(_first_present(inputs, "document_ready", "current_document_ready")),
        "safety_secured": _coerce_bool_flag(_first_present(inputs, "safety_secured", "current_safety_secured")),
    }
    if not snapshot["industry_name"]:
        snapshot["industry_name"] = _compact(result.get("industry_name"), _LIM_SERVICE_NAME)
    if not snapshot["service_name"]:
        snapshot["service_name"] = snapshot["industry_name"]
    return snapshot


def _required_ok_flag(required_summary: Dict[str, Any], key: str) -> str:
    block = dict((required_summary or {}).get(key) or {})
    parsed = _coerce_bool_flag(block.get("ok"))
    if parsed is not None:
        return str(parsed)
    return "0"


def _result_summary_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "industry_name": _compact(result.get("industry_name"), _LIM_SERVICE_NAME),
        "group_rule_id": _compact(result.get("group_rule_id"), _LIM_SERVICE_CODE),
        "overall_status": _compact(result.get("overall_status"), _LIM_SERVICE_CODE),
        "overall_ok": bool(result.get("overall_ok")),
        "manual_review_required": bool(result.get("manual_review_required")),
        "coverage_status": _compact(result.get("coverage_status"), _LIM_COVERAGE),
        "mapping_confidence": result.get("mapping_confidence"),
        "typed_criteria_total": _coerce_int_or_none(result.get("typed_criteria_total")),
        "pending_criteria_count": _coerce_int_or_none(result.get("pending_criteria_count")),
        "blocking_failure_count": _coerce_int_or_none(result.get("blocking_failure_count")),
        "unknown_blocking_count": _coerce_int_or_none(result.get("unknown_blocking_count")),
        "capital_input_suspicious": bool(result.get("capital_input_suspicious")),
        "next_actions": list(result.get("next_actions") or []),
    }


def _partner_health_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "message": "healthy",
        "health_contract": load_widget_health_contract(),
    }


def _env_str(key: str, default: str = "") -> str:
    raw = CONFIG.get(key, default)
    return str(raw or "").strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(str(CONFIG.get(key, default) or default).strip())
    except (ValueError, TypeError):
        return int(default)


def _env_bool(key: str, default: bool = False) -> bool:
    raw = str(CONFIG.get(key, "1" if default else "0") or "").strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    if raw in {"0", "false", "no", "off", "n"}:
        return False
    return bool(default)


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _tenant_plan_key(resolution: Any) -> str:
    tenant = getattr(resolution, "tenant", None)
    if tenant is None:
        return ""
    return _compact(getattr(tenant, "plan", "")).lower()


def _tenant_id_value(resolution: Any) -> str:
    tenant = getattr(resolution, "tenant", None)
    if tenant is None:
        return ""
    return _compact(getattr(tenant, "tenant_id", ""))


def _tenant_has_feature(server: Any, resolution: Any, feature: str) -> bool:
    if not bool(getattr(server, "tenant_gateway_enabled", False)):
        return True
    return bool(server.tenant_gateway.check_feature(resolution, feature))


def _tenant_has_system(server: Any, resolution: Any, system: str) -> bool:
    if not bool(getattr(server, "tenant_gateway_enabled", False)):
        return True
    return bool(server.tenant_gateway.check_system(resolution, system))


def _channel_id_value(resolution: Any) -> str:
    profile = getattr(resolution, "profile", None)
    if profile is None:
        return ""
    return _compact(getattr(profile, "channel_id", ""))


def _channel_exposes_system(server: Any, resolution: Any, system: str) -> bool:
    if not bool(getattr(server, "channel_router", None)):
        return True
    try:
        return bool(server.channel_router.check_system(resolution, system))
    except (AttributeError, KeyError, TypeError, ValueError):
        return True


def _permit_response_tier(server: Any, resolution: Any) -> str:
    if not bool(getattr(server, "tenant_gateway_enabled", False)):
        return "internal"
    if _tenant_has_feature(server, resolution, "permit_precheck_internal"):
        return "internal"
    if _tenant_has_feature(server, resolution, "permit_precheck_detail"):
        return "detail"
    plan = _tenant_plan_key(resolution)
    if plan == "pro_internal":
        return "internal"
    if plan == "pro":
        return "detail"
    return "summary"


def _project_precheck_result(server: Any, resolution: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(result or {})
    tier = _permit_response_tier(server, resolution)
    tenant_plan = _tenant_plan_key(resolution)
    tenant_id = _tenant_id_value(resolution)
    policy = {
        "tier": tier,
        "detail_included": tier in {"detail", "internal"},
        "internal_meta_included": tier == "internal",
        "tenant_plan": tenant_plan or "unscoped",
    }

    if not bool(payload.get("ok")):
        payload["response_policy"] = policy
        if tier != "internal":
            payload.pop("tenant_id", None)
        return payload

    if tier == "summary":
        allowed = {
            "ok",
            "service_code",
            "industry_name",
            "overall_status",
            "overall_ok",
            "manual_review_required",
            "coverage_status",
            "required_summary",
            "typed_overall_status",
            "typed_criteria_total",
            "pending_criteria_count",
            "blocking_failure_count",
            "unknown_blocking_count",
            "capital_input_suspicious",
            "next_actions",
        }
        trimmed = {k: payload.get(k) for k in allowed if k in payload}
        trimmed["next_actions"] = list(trimmed.get("next_actions") or [])[:3]
        trimmed["response_policy"] = policy
        return trimmed

    if tier == "detail":
        payload.pop("pending_criteria_lines", None)
        payload["response_policy"] = policy
        return payload

    payload["tenant_id"] = tenant_id
    payload["response_policy"] = policy
    return payload


_SAFE_SQL_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_sql_identifier(name: str) -> str:
    """Validate and return *name* as a safe SQL identifier.

    Raises ``ValueError`` for names that do not match ``[A-Za-z_][A-Za-z0-9_]*``.
    This prevents SQL injection even though callers only pass hardcoded values.
    """
    if not _SAFE_SQL_IDENT_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


class PermitUsageStore:
    def __init__(self, db_path: str = "", thresholds_path: str = "") -> None:
        self.db_path = str(db_path or "").strip()
        self.thresholds_path = str(thresholds_path or "").strip()
        self._thresholds = self._load_thresholds()
        if self.db_path:
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self._init_db()

    def _load_thresholds(self) -> Dict[str, Any]:
        path = Path(self.thresholds_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TEXT NOT NULL,
                    source TEXT,
                    page_mode TEXT,
                    status TEXT,
                    error_text TEXT,
                    license_text TEXT,
                    input_specialty TEXT,
                    input_y23 TEXT,
                    input_y24 TEXT,
                    input_y25 TEXT,
                    input_balance TEXT,
                    input_capital TEXT,
                    input_surplus TEXT,
                    input_debt_level TEXT,
                    input_liq_level TEXT,
                    ok_capital TEXT,
                    ok_engineer TEXT,
                    ok_office TEXT,
                    output_center TEXT,
                    output_range TEXT,
                    output_confidence TEXT,
                    output_neighbors TEXT,
                    missing_critical TEXT,
                    page_url TEXT,
                    requested_at TEXT,
                    raw_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS permit_precheck_inputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    usage_event_id INTEGER,
                    received_at TEXT NOT NULL,
                    requested_at TEXT,
                    tenant_id TEXT NOT NULL,
                    tenant_plan TEXT,
                    response_tier TEXT,
                    source TEXT,
                    page_url TEXT,
                    service_code TEXT,
                    service_name TEXT,
                    industry_name TEXT,
                    rule_id TEXT,
                    group_rule_id TEXT,
                    capital_eok REAL,
                    raw_capital_input TEXT,
                    technicians_count INTEGER,
                    equipment_count INTEGER,
                    deposit_days INTEGER,
                    qualification_count INTEGER,
                    office_secured INTEGER,
                    facility_secured INTEGER,
                    guarantee_secured INTEGER,
                    insurance_secured INTEGER,
                    qualification_secured INTEGER,
                    document_ready INTEGER,
                    safety_secured INTEGER,
                    overall_status TEXT,
                    coverage_status TEXT,
                    typed_criteria_total INTEGER,
                    pending_criteria_count INTEGER,
                    blocking_failure_count INTEGER,
                    unknown_blocking_count INTEGER,
                    manual_review_required INTEGER,
                    capital_input_suspicious INTEGER,
                    request_json TEXT,
                    result_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_permit_precheck_inputs_request_id ON permit_precheck_inputs(request_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_permit_precheck_inputs_tenant_received ON permit_precheck_inputs(tenant_id, received_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tenant_usage_monthly (
                    tenant_id TEXT NOT NULL,
                    year_month TEXT NOT NULL,
                    service TEXT NOT NULL,
                    usage_events INTEGER NOT NULL DEFAULT 0,
                    estimated_tokens INTEGER NOT NULL DEFAULT 0,
                    ok_events INTEGER NOT NULL DEFAULT 0,
                    error_events INTEGER NOT NULL DEFAULT 0,
                    last_received_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (tenant_id, year_month, service)
                )
                """
            )
            self._ensure_usage_event_columns(conn)
            self._ensure_monthly_columns(conn)
            conn.commit()
        finally:
            conn.close()

    def _ensure_usage_event_columns(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(usage_events)").fetchall()
        columns = {str(row[1]).strip().lower() for row in rows if len(row) > 1}
        required_columns = {
            "received_at": "TEXT",
            "source": "TEXT",
            "page_mode": "TEXT",
            "status": "TEXT",
            "error_text": "TEXT",
            "license_text": "TEXT",
            "input_specialty": "TEXT",
            "input_y23": "TEXT",
            "input_y24": "TEXT",
            "input_y25": "TEXT",
            "input_balance": "TEXT",
            "input_capital": "TEXT",
            "input_surplus": "TEXT",
            "input_debt_level": "TEXT",
            "input_liq_level": "TEXT",
            "ok_capital": "TEXT",
            "ok_engineer": "TEXT",
            "ok_office": "TEXT",
            "output_center": "TEXT",
            "output_range": "TEXT",
            "output_confidence": "TEXT",
            "output_neighbors": "TEXT",
            "missing_critical": "TEXT",
            "page_url": "TEXT",
            "requested_at": "TEXT",
            "raw_json": "TEXT",
        }
        for column, column_type in required_columns.items():
            if column not in columns:
                col = _safe_sql_identifier(column)
                ctype = _safe_sql_identifier(column_type)
                conn.execute(f"ALTER TABLE usage_events ADD COLUMN {col} {ctype}")

    def _ensure_monthly_columns(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("PRAGMA table_info(tenant_usage_monthly)").fetchall()
        columns = {str(row[1]).strip().lower() for row in rows if len(row) > 1}
        if "ok_events" not in columns:
            conn.execute("ALTER TABLE tenant_usage_monthly ADD COLUMN ok_events INTEGER NOT NULL DEFAULT 0")
        if "error_events" not in columns:
            conn.execute("ALTER TABLE tenant_usage_monthly ADD COLUMN error_events INTEGER NOT NULL DEFAULT 0")
        if "last_received_at" not in columns:
            conn.execute("ALTER TABLE tenant_usage_monthly ADD COLUMN last_received_at TEXT NOT NULL DEFAULT ''")

    def _plan_config(self, plan: str) -> Dict[str, Any]:
        plans = self._thresholds.get("plans") if isinstance(self._thresholds, dict) else {}
        if not isinstance(plans, dict):
            return {}
        return dict(plans.get(str(plan or "").strip().lower()) or {})

    def _protected_tenants(self) -> set[str]:
        policy = self._thresholds.get("policy") if isinstance(self._thresholds, dict) else {}
        raw = policy.get("protected_tenants") if isinstance(policy, dict) else []
        out = set()
        if isinstance(raw, list):
            for item in raw:
                key = _compact(item).lower()
                if key:
                    out.add(key)
        return out

    def _token_estimate(self, ok: bool) -> int:
        token_model = self._thresholds.get("token_estimates") if isinstance(self._thresholds, dict) else {}
        if not isinstance(token_model, dict):
            token_model = {}
        if ok:
            return int(token_model.get("permit_ok", 900) or 900)
        return int(token_model.get("error", 200) or 200)

    def usage_snapshot(self, tenant_id: str, plan: str) -> Dict[str, Any]:
        key = _compact(tenant_id).lower() or "unknown"
        month = _month_key()
        limit = int(self._plan_config(plan).get("max_usage_events", 0) or 0)
        used = 0
        ok_events = 0
        error_events = 0
        if self.db_path:
            conn = sqlite3.connect(self.db_path, timeout=30)
            try:
                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(usage_events), 0), COALESCE(SUM(ok_events), 0), COALESCE(SUM(error_events), 0)
                    FROM tenant_usage_monthly
                    WHERE tenant_id=? AND year_month=? AND service='permit_precheck'
                    """,
                    (key, month),
                ).fetchone()
                used = int((row[0] if row else 0) or 0)
                ok_events = int((row[1] if row and len(row) > 1 else 0) or 0)
                error_events = int((row[2] if row and len(row) > 2 else 0) or 0)
            finally:
                conn.close()
        protected = key in self._protected_tenants()
        blocked = bool(limit > 0 and used >= limit and not protected)
        remaining = 0 if limit <= 0 else max(0, limit - used)
        return {
            "tenant_id": key,
            "plan": _compact(plan).lower() or "unknown",
            "year_month": month,
            "usage_events": used,
            "ok_events": ok_events,
            "error_events": error_events,
            "max_usage_events": limit,
            "remaining_usage_events": remaining,
            "protected": protected,
            "blocked": blocked,
        }

    def insert_precheck_usage(
        self,
        *,
        tenant_id: str,
        plan: str,
        request_id: str,
        source: str,
        page_url: str,
        requested_at: str,
        inputs: Dict[str, Any],
        result: Dict[str, Any],
        response_tier: str,
    ) -> Dict[str, Any]:
        key = _compact(tenant_id).lower() or "unknown"
        status = "ok" if bool(result.get("ok")) else "error"
        estimated_tokens = self._token_estimate(status == "ok")
        request_key = _compact(request_id, _LIM_SERVICE_CODE) or uuid.uuid4().hex
        received_at = now_iso()
        input_snapshot = _canonical_permit_input_snapshot(inputs, result)
        result_summary = _result_summary_payload(result)
        required_summary = dict(result.get("required_summary") or {})
        row = {
            "received_at": received_at,
            "source": _compact(source, _LIM_SOURCE) or "permit_precheck_api",
            "page_mode": "permit_precheck",
            "status": status,
            "error_text": _compact(result.get("error") or "", _LIM_ERROR_TEXT),
            "license_text": _compact(input_snapshot.get("industry_name") or input_snapshot.get("service_name") or "", _LIM_SERVICE_NAME),
            "input_specialty": _compact(input_snapshot.get("service_code") or input_snapshot.get("service_name") or "", _LIM_SERVICE_CODE),
            "input_y23": "",
            "input_y24": "",
            "input_y25": "",
            "input_balance": "",
            "input_capital": _compact(
                input_snapshot.get("raw_capital_input")
                if input_snapshot.get("raw_capital_input") not in {"", None}
                else input_snapshot.get("capital_eok"),
                _LIM_SERVICE_CODE,
            ),
            "input_surplus": "",
            "input_debt_level": "",
            "input_liq_level": "",
            "ok_capital": _required_ok_flag(required_summary, "capital"),
            "ok_engineer": _required_ok_flag(required_summary, "technicians"),
            "ok_office": str(input_snapshot.get("office_secured", 0) or 0),
            "output_center": _compact(result_summary.get("overall_status"), _LIM_SERVICE_CODE),
            "output_range": _compact(result_summary.get("coverage_status"), _LIM_COVERAGE),
            "output_confidence": _compact(result_summary.get("mapping_confidence"), _LIM_COVERAGE),
            "output_neighbors": _compact(result_summary.get("typed_criteria_total"), _LIM_SERVICE_CODE),
            "missing_critical": _compact(result_summary.get("pending_criteria_count"), _LIM_SERVICE_NAME),
            "page_url": _compact(page_url, _LIM_PAGE_URL),
            "requested_at": _compact(requested_at, _LIM_SERVICE_CODE),
            "raw_json": _json_dumps_compact(
                {
                    "request_id": request_key,
                    "tenant_id": key,
                    "tenant_plan": _compact(plan).lower() or "unknown",
                    "response_tier": _compact(response_tier),
                    "service_track": "permit_precheck_api",
                    "business_domain": "permit_precheck",
                    "source": _compact(source, _LIM_SOURCE) or "permit_precheck_api",
                    "page_mode": "permit_precheck",
                    "status": status,
                    "inputs": input_snapshot,
                    "result": result_summary,
                },
            ),
        }
        detail_row = {
            "request_id": request_key,
            "usage_event_id": None,
            "received_at": received_at,
            "requested_at": _compact(requested_at, _LIM_SERVICE_CODE),
            "tenant_id": key,
            "tenant_plan": _compact(plan).lower() or "unknown",
            "response_tier": _compact(response_tier, _LIM_RESPONSE_TIER),
            "source": row["source"],
            "page_url": row["page_url"],
            "service_code": _compact(input_snapshot.get("service_code"), _LIM_SERVICE_CODE),
            "service_name": _compact(input_snapshot.get("service_name"), _LIM_SERVICE_NAME),
            "industry_name": _compact(input_snapshot.get("industry_name"), _LIM_SERVICE_NAME),
            "rule_id": _compact(input_snapshot.get("rule_id"), _LIM_SERVICE_CODE),
            "group_rule_id": _compact(result_summary.get("group_rule_id"), _LIM_SERVICE_CODE),
            "capital_eok": input_snapshot.get("capital_eok"),
            "raw_capital_input": _compact(input_snapshot.get("raw_capital_input"), _LIM_SERVICE_CODE),
            "technicians_count": input_snapshot.get("technicians_count"),
            "equipment_count": input_snapshot.get("equipment_count"),
            "deposit_days": input_snapshot.get("deposit_days"),
            "qualification_count": input_snapshot.get("qualification_count"),
            "office_secured": input_snapshot.get("office_secured"),
            "facility_secured": input_snapshot.get("facility_secured"),
            "guarantee_secured": input_snapshot.get("guarantee_secured"),
            "insurance_secured": input_snapshot.get("insurance_secured"),
            "qualification_secured": input_snapshot.get("qualification_secured"),
            "document_ready": input_snapshot.get("document_ready"),
            "safety_secured": input_snapshot.get("safety_secured"),
            "overall_status": _compact(result_summary.get("overall_status"), _LIM_SERVICE_CODE),
            "coverage_status": _compact(result_summary.get("coverage_status"), _LIM_COVERAGE),
            "typed_criteria_total": result_summary.get("typed_criteria_total"),
            "pending_criteria_count": result_summary.get("pending_criteria_count"),
            "blocking_failure_count": result_summary.get("blocking_failure_count"),
            "unknown_blocking_count": result_summary.get("unknown_blocking_count"),
            "manual_review_required": _coerce_bool_flag(result_summary.get("manual_review_required")),
            "capital_input_suspicious": _coerce_bool_flag(result_summary.get("capital_input_suspicious")),
            "request_json": _json_dumps_compact(dict(inputs or {})),
            "result_json": _json_dumps_compact(result),
        }
        if not self.db_path:
            snap = self.usage_snapshot(key, plan)
            snap["estimated_tokens"] = estimated_tokens
            return snap
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            cur = conn.execute(
                """
                INSERT INTO usage_events (
                    received_at, source, page_mode, status, error_text,
                    license_text, input_specialty, input_y23, input_y24, input_y25,
                    input_balance, input_capital, input_surplus, input_debt_level, input_liq_level,
                    ok_capital, ok_engineer, ok_office,
                    output_center, output_range, output_confidence, output_neighbors,
                    missing_critical, page_url, requested_at, raw_json
                ) VALUES (
                    :received_at, :source, :page_mode, :status, :error_text,
                    :license_text, :input_specialty, :input_y23, :input_y24, :input_y25,
                    :input_balance, :input_capital, :input_surplus, :input_debt_level, :input_liq_level,
                    :ok_capital, :ok_engineer, :ok_office,
                    :output_center, :output_range, :output_confidence, :output_neighbors,
                    :missing_critical, :page_url, :requested_at, :raw_json
                )
                """,
                row,
            )
            detail_row["usage_event_id"] = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO permit_precheck_inputs (
                    request_id, usage_event_id, received_at, requested_at,
                    tenant_id, tenant_plan, response_tier, source, page_url,
                    service_code, service_name, industry_name, rule_id, group_rule_id,
                    capital_eok, raw_capital_input, technicians_count, equipment_count, deposit_days, qualification_count,
                    office_secured, facility_secured, guarantee_secured, insurance_secured, qualification_secured,
                    document_ready, safety_secured,
                    overall_status, coverage_status, typed_criteria_total, pending_criteria_count,
                    blocking_failure_count, unknown_blocking_count, manual_review_required, capital_input_suspicious,
                    request_json, result_json
                ) VALUES (
                    :request_id, :usage_event_id, :received_at, :requested_at,
                    :tenant_id, :tenant_plan, :response_tier, :source, :page_url,
                    :service_code, :service_name, :industry_name, :rule_id, :group_rule_id,
                    :capital_eok, :raw_capital_input, :technicians_count, :equipment_count, :deposit_days, :qualification_count,
                    :office_secured, :facility_secured, :guarantee_secured, :insurance_secured, :qualification_secured,
                    :document_ready, :safety_secured,
                    :overall_status, :coverage_status, :typed_criteria_total, :pending_criteria_count,
                    :blocking_failure_count, :unknown_blocking_count, :manual_review_required, :capital_input_suspicious,
                    :request_json, :result_json
                )
                """,
                detail_row,
            )
            conn.execute(
                """
                INSERT INTO tenant_usage_monthly (
                    tenant_id, year_month, service, usage_events, estimated_tokens, ok_events, error_events, last_received_at
                ) VALUES (?, ?, 'permit_precheck', 1, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, year_month, service) DO UPDATE SET
                    usage_events = usage_events + 1,
                    estimated_tokens = estimated_tokens + excluded.estimated_tokens,
                    ok_events = ok_events + excluded.ok_events,
                    error_events = error_events + excluded.error_events,
                    last_received_at = excluded.last_received_at
                """,
                (
                    key,
                    received_at[:7],
                    int(estimated_tokens),
                    1 if status == "ok" else 0,
                    1 if status != "ok" else 0,
                    received_at,
                ),
            )
            conn.commit()
            snap = self.usage_snapshot(key, plan)
            snap["usage_id"] = int(cur.lastrowid)
            snap["estimated_tokens"] = int(estimated_tokens)
            return snap
        finally:
            conn.close()


class PermitPrecheckEngine:
    def __init__(self, catalog_path: str | None = None, rules_path: str | None = None) -> None:
        self.catalog_path = str(catalog_path or DEFAULT_CATALOG_PATH)
        self.rules_path = str(rules_path or DEFAULT_RULES_PATH)
        self.catalog: Dict[str, Any] = {}
        self.rule_catalog: Dict[str, Any] = {}
        self.rule_index: Dict[str, Any] = {}
        self.payload: Dict[str, Any] = {}
        self._meta: Dict[str, Any] = {}
        self.refresh()

    def refresh(self) -> Dict[str, Any]:
        self.catalog = _load_catalog(DEFAULT_CATALOG_PATH.__class__(self.catalog_path))
        self.rule_catalog = _load_rule_catalog(DEFAULT_RULES_PATH.__class__(self.rules_path))
        self.rule_index = _build_rule_index(self.rule_catalog)
        self.payload = _prepare_ui_payload(self.catalog, self.rule_catalog)
        summary = dict(self.payload.get("summary") or {})
        rule_meta = dict(self.payload.get("rule_catalog_meta") or {})
        self._meta = {
            "industry_total": int(summary.get("industry_total", 0) or 0),
            "with_registration_rule_total": int(summary.get("with_registration_rule_total", 0) or 0),
            "coverage_pct": float(summary.get("coverage_pct", 0.0) or 0.0),
            "pending_rule_total": int(summary.get("pending_rule_total", 0) or 0),
            "rule_catalog_version": str(rule_meta.get("version", "") or ""),
            "rule_catalog_effective_date": str(rule_meta.get("effective_date", "") or ""),
            "public_claim_level": str(summary.get("public_claim_level", "") or ""),
            "public_claim_message": str(summary.get("public_claim_message", "") or ""),
        }
        return dict(self._meta)

    @property
    def meta(self) -> Dict[str, Any]:
        return dict(self._meta)

    def _resolve_rule(self, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        service_code = _compact(payload.get("service_code"))
        service_name = _compact(payload.get("service_name") or payload.get("industry_name"))
        industry = {
            "service_code": service_code,
            "service_name": service_name,
        }
        rule = _resolve_rule_for_industry(industry, self.rule_index)
        if rule is not None:
            return rule
        rule_id = _compact(payload.get("rule_id"))
        if not rule_id:
            return None
        for item in list(self.rule_index.get("rules") or []):
            if _compact(item.get("rule_id")) == rule_id or _compact(item.get("group_rule_id")) == rule_id:
                return item
        return None

    def precheck(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            payload = {}
        if not self.rule_index:
            self.refresh()
        inputs = dict(payload.get("inputs") or {})
        if not inputs:
            inputs = {
                k: v
                for k, v in payload.items()
                if k
                not in {
                    "service_code",
                    "service_name",
                    "industry_name",
                    "rule_id",
                    "source",
                    "tenant_id",
                }
            }
        rule = self._resolve_rule(payload)
        if rule is None:
            return {
                "ok": False,
                "error": "mapping_required",
                "manual_review_required": True,
                "overall_status": "manual_review",
                "message": "법령 기준 매핑이 확정되지 않은 업종입니다. 전문가 검토가 필요합니다.",
            }

        current_capital = inputs.get("capital_eok", inputs.get("current_capital_eok", 0))
        current_technicians = inputs.get("technicians_count", inputs.get("technicians", inputs.get("current_technicians", 0)))
        current_equipment = inputs.get("equipment_count", inputs.get("current_equipment_count", 0))
        raw_capital_input = inputs.get("raw_capital_input", inputs.get("capital_eok", ""))

        diagnosis = evaluate_registration_diagnosis(
            rule,
            current_capital,
            current_technicians,
            current_equipment,
            raw_capital_input=str(raw_capital_input or ""),
            extra_inputs=inputs,
        )

        overall_status = "pass" if bool(diagnosis.get("overall_ok")) else "shortfall"
        if bool(diagnosis.get("manual_review_required")) and overall_status == "pass":
            overall_status = "manual_review"

        return {
            "ok": True,
            "service_code": _compact(payload.get("service_code")),
            "industry_name": str(rule.get("industry_name", "") or "").strip(),
            "group_rule_id": str(rule.get("group_rule_id", "") or "").strip(),
            "overall_status": overall_status,
            "overall_ok": bool(diagnosis.get("overall_ok")),
            "manual_review_required": bool(diagnosis.get("manual_review_required", False)),
            "coverage_status": str(diagnosis.get("coverage_status", "") or ""),
            "mapping_confidence": diagnosis.get("mapping_confidence"),
            "required_summary": {
                "capital": diagnosis.get("capital"),
                "technicians": diagnosis.get("technicians"),
                "equipment": diagnosis.get("equipment"),
                "deposit_days": diagnosis.get("deposit_days"),
                "expected_diagnosis_date": diagnosis.get("expected_diagnosis_date"),
            },
            "criterion_results": list(diagnosis.get("criterion_results") or []),
            "evidence_checklist": list(diagnosis.get("evidence_checklist") or []),
            "typed_overall_status": str(diagnosis.get("typed_overall_status", "") or ""),
            "typed_criteria_total": int(diagnosis.get("typed_criteria_total", 0) or 0),
            "pending_criteria_count": int(diagnosis.get("pending_criteria_count", 0) or 0),
            "blocking_failure_count": int(diagnosis.get("blocking_failure_count", 0) or 0),
            "unknown_blocking_count": int(diagnosis.get("unknown_blocking_count", 0) or 0),
            "capital_input_suspicious": bool(diagnosis.get("capital_input_suspicious", False)),
            "next_actions": list(diagnosis.get("next_actions") or []),
            "pending_criteria_lines": list(rule.get("pending_criteria_lines") or []),
            "document_templates": list(rule.get("document_templates") or []),
            "legal_basis": list(rule.get("legal_basis") or []),
        }


class PermitApiServer(ThreadingHTTPServer):
    def __init__(
        self,
        addr: tuple[str, int],
        handler_cls: type,
        engine: "PermitPrecheckEngine",
        allowed_origins: set[str] | None,
        api_key: str,
        admin_api_key: str,
        max_body_bytes: int,
        rate_limit_per_min: int,
        trust_x_forwarded_for: bool,
        security_log_file: str,
        tenant_gateway_enabled: bool,
        tenant_gateway: Any,
        usage_store: Any,
        channel_router: Any,
        channel_router_strict: bool,
    ) -> None:
        super().__init__(addr, handler_cls)
        self.engine = engine
        self.allowed_origins = set(allowed_origins or set())
        self.api_keys = parse_key_values(str(api_key or ""))
        self.admin_api_keys = parse_key_values(str(admin_api_key or ""))
        self.max_body_bytes = max(1024, int(max_body_bytes or 65536))
        self.rate_limiter = SlidingWindowRateLimiter(limit=max(1, min(10000, int(rate_limit_per_min or 90))), window_seconds=60)
        self.trust_x_forwarded_for = bool(trust_x_forwarded_for)
        self.security_events = SecurityEventLogger(str(security_log_file or ""))
        self.tenant_gateway_enabled = bool(tenant_gateway_enabled)
        self.tenant_gateway = tenant_gateway if isinstance(tenant_gateway, TenantGateway) else TenantGateway([], strict=False, default_tenant_id="")
        self.usage_store = usage_store if isinstance(usage_store, PermitUsageStore) else PermitUsageStore("", "")
        self.channel_router = channel_router if isinstance(channel_router, ChannelRouter) else ChannelRouter([], strict=False, default_channel_id="")
        self.channel_router_strict = bool(channel_router_strict)


class Handler(BaseHTTPRequestHandler):
    server_version = "PermitPrecheckAPI/1.0"

    def _allow_origin(self) -> str:
        req_origin = _compact(self.headers.get("Origin"))
        return resolve_allow_origin(req_origin, self.server.allowed_origins)

    def _client_ip(self) -> str:
        return safe_client_ip(self, trust_x_forwarded_for=bool(self.server.trust_x_forwarded_for))

    def _tenant_resolution(self) -> Any:
        return self.server.tenant_gateway.resolve(
            host=_compact(self.headers.get("Host")),
            origin=_compact(self.headers.get("Origin")),
        )

    def _channel_resolution(self) -> Any:
        cached = getattr(self, "_cached_channel_resolution", None)
        if cached is not None:
            return cached
        resolution = self.server.channel_router.resolve(
            host=_compact(self.headers.get("Host")),
            origin=_compact(self.headers.get("Origin")),
        )
        setattr(self, "_cached_channel_resolution", resolution)
        return resolution

    def _channel_headers(self) -> Dict[str, str]:
        resolution = self._channel_resolution()
        headers: Dict[str, str] = {}
        channel_id = _channel_id_value(resolution)
        if channel_id:
            headers["X-Channel-Id"] = channel_id
        if getattr(resolution, "source", ""):
            headers["X-Channel-Source"] = str(resolution.source)
        return headers

    def _require_channel_hint_match(self, request_meta: Dict[str, Any]) -> bool:
        hinted = _compact((request_meta or {}).get("channel_id_hint"), _LIM_SERVICE_CODE).lower()
        if not hinted:
            return True
        resolved = _compact(_channel_id_value(self._channel_resolution()), _LIM_SERVICE_CODE).lower()
        if hinted == resolved:
            return True
        self._write_json(
            400,
            {
                "ok": False,
                "error": "channel_id_mismatch",
                "hinted_channel_id": hinted,
                "resolved_channel_id": resolved,
            },
        )
        return False

    def _require_channel_ready(self) -> bool:
        resolution = self._channel_resolution()
        profile = getattr(resolution, "profile", None)
        if profile is None:
            if bool(getattr(self.server, "channel_router_strict", False)):
                self._write_json(403, {"ok": False, "error": "channel_not_allowed"})
                return False
            return True
        if bool(getattr(profile, "enabled", True)):
            return True
        self.server.security_events.append(
            {
                "event": "channel_blocked",
                "service": "permit_precheck_api",
                "path": self.path.split("?", 1)[0],
                "ip": self._client_ip(),
                "host": _compact(self.headers.get("Host")),
                "origin": _compact(self.headers.get("Origin")),
                "channel_id": _channel_id_value(resolution),
                "request_id": self._request_id(),
            }
        )
        self._write_json(403, {"ok": False, "error": "channel_not_allowed"})
        return False

    def _require_channel_system(self, system: str) -> bool:
        resolution = self._channel_resolution()
        if _channel_exposes_system(self.server, resolution, system):
            return True
        self.server.security_events.append(
            {
                "event": "channel_blocked",
                "service": "permit_precheck_api",
                "host": _compact(self.headers.get("Host")),
                "origin": _compact(self.headers.get("Origin")),
                "channel_id": _channel_id_value(resolution),
                "required_system": str(system or ""),
                "request_id": self._request_id(),
            }
        )
        self._write_json(403, {"ok": False, "error": "channel_system_not_allowed", "required_system": str(system or "")})
        return False

    def _usage_headers(self, usage_snapshot: Dict[str, Any], response_tier: str = "") -> Dict[str, str]:
        headers = {
            "X-Tenant-Plan": str(usage_snapshot.get("plan") or "unknown"),
            "X-Usage-Month": str(usage_snapshot.get("year_month") or ""),
            "X-Usage-Events-Month": str(int(usage_snapshot.get("usage_events", 0) or 0)),
            "X-Usage-Ok-Events-Month": str(int(usage_snapshot.get("ok_events", 0) or 0)),
            "X-Usage-Error-Events-Month": str(int(usage_snapshot.get("error_events", 0) or 0)),
            "X-Usage-Events-Limit": str(int(usage_snapshot.get("max_usage_events", 0) or 0)),
            "X-Usage-Events-Remaining": str(int(usage_snapshot.get("remaining_usage_events", 0) or 0)),
        }
        if response_tier:
            headers["X-Response-Tier"] = str(response_tier)
        return headers

    def _require_any_feature(self, *features: str) -> bool:
        if not bool(self.server.tenant_gateway_enabled):
            return True
        resolution = self._tenant_resolution()
        requested = [_compact(item).lower() for item in features if _compact(item)]
        for feature in requested:
            if self.server.tenant_gateway.check_feature(resolution, feature):
                return True
        tenant_id = _tenant_id_value(resolution)
        self.server.security_events.append(
            {
                "event": "tenant_blocked",
                "service": "permit_precheck_api",
                "path": self.path.split("?", 1)[0],
                "feature": ",".join(requested),
                "ip": self._client_ip(),
                "host": _compact(self.headers.get("Host")),
                "origin": _compact(self.headers.get("Origin")),
                "tenant_id": tenant_id,
                "request_id": self._request_id(),
            }
        )
        self._write_json(403, {"ok": False, "error": "tenant_not_allowed"})
        return False

    def _require_feature(self, feature: str) -> bool:
        if not bool(self.server.tenant_gateway_enabled):
            return True
        resolution = self._tenant_resolution()
        if self.server.tenant_gateway.check_feature(resolution, feature):
            return True
        tenant_id = ""
        if resolution.tenant is not None:
            tenant_id = str(resolution.tenant.tenant_id or "")
        self.server.security_events.append(
            {
                "event": "tenant_blocked",
                "service": "permit_precheck_api",
                "path": self.path.split("?", 1)[0],
                "feature": str(feature or ""),
                "ip": self._client_ip(),
                "host": _compact(self.headers.get("Host")),
                "origin": _compact(self.headers.get("Origin")),
                "tenant_id": tenant_id,
                "request_id": self._request_id(),
            }
        )
        self._write_json(403, {"ok": False, "error": "tenant_not_allowed"})
        return False

    def _require_system(self, system: str) -> bool:
        if not bool(self.server.tenant_gateway_enabled):
            return True
        resolution = self._tenant_resolution()
        if self.server.tenant_gateway.check_system(resolution, system):
            return True
        tenant_id = ""
        if resolution.tenant is not None:
            tenant_id = str(resolution.tenant.tenant_id or "")
        self.server.security_events.append(
            {
                "event": "tenant_blocked",
                "service": "permit_precheck_api",
                "path": self.path.split("?", 1)[0],
                "required_system": str(system or ""),
                "ip": self._client_ip(),
                "host": _compact(self.headers.get("Host")),
                "origin": _compact(self.headers.get("Origin")),
                "tenant_id": tenant_id,
                "request_id": self._request_id(),
            }
        )
        self._write_json(403, {"ok": False, "error": "system_not_allowed", "required_system": str(system or "")})
        return False

    def _write_json(self, status: int, payload: Dict[str, Any], extra_headers: Dict[str, str] | None = None) -> None:
        request_id = self._request_id()
        channel_id = _channel_id_value(self._channel_resolution())
        response_tier = ""
        tenant_plan = ""
        if isinstance(extra_headers, dict):
            response_tier = _compact(extra_headers.get("X-Response-Tier"), _LIM_X_RESPONSE_TIER)
            tenant_plan = _compact(extra_headers.get("X-Tenant-Plan"), _LIM_X_TENANT_PLAN)
        response_payload = build_response_envelope(
            payload,
            service="permit_precheck_api",
            api_version="v1",
            request_id=request_id,
            channel_id=channel_id,
            tenant_plan=tenant_plan,
            response_tier=response_tier,
        )
        body = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
        allow_origin = self._allow_origin()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Api-Version", "v1")
        self.send_header("X-Service-Name", "permit_precheck_api")
        self.send_header("X-Request-Id", request_id)
        for hk, hv in self._channel_headers().items():
            self.send_header(str(hk), str(hv))
        for hk, hv in DEFAULT_SECURITY_HEADERS:
            self.send_header(hk, hv)
        if allow_origin:
            self.send_header("Access-Control-Allow-Origin", allow_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key, X-Request-Id, X-Correlation-Id, X-Channel-Id")
        if isinstance(extra_headers, dict):
            for hk, hv in extra_headers.items():
                self.send_header(str(hk), str(hv))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass

    def _request_id(self) -> str:
        cached = getattr(self, "_cached_request_id", "")
        if cached:
            return str(cached)
        incoming = _compact(self.headers.get("X-Request-Id") or self.headers.get("X-Correlation-Id"), _LIM_SERVICE_CODE)
        if not incoming:
            incoming = uuid.uuid4().hex
        setattr(self, "_cached_request_id", incoming)
        return incoming

    def _allow_request(self) -> bool:
        ok, retry_after = self.server.rate_limiter.allow(self._client_ip())
        if ok:
            return True
        self._write_json(429, {"ok": False, "error": "rate_limited"}, extra_headers={"Retry-After": str(max(1, int(retry_after)))})
        return False

    def _deny_if_blocked_token(self) -> bool:
        if not bool(self.server.tenant_gateway_enabled):
            return False
        token = header_token(self.headers, "x")
        if not token:
            return False
        resolution = self._tenant_resolution()
        if not self.server.tenant_gateway.is_token_blocked(resolution, token):
            return False
        self._write_json(401, {"ok": False, "error": "blocked_api_key"})
        return True

    def _require_api_key(self, admin: bool = False) -> bool:
        if self._deny_if_blocked_token():
            return False
        expected = self.server.admin_api_keys if admin else self.server.api_keys
        if admin and not expected:
            expected = self.server.api_keys
        if is_authorized_any(self.headers, expected):
            return True
        self._write_json(401, {"ok": False, "error": "unauthorized"})
        return False

    def _read_json_body(self) -> Dict[str, Any]:
        content_type = str(self.headers.get("Content-Type", "") or "").lower()
        if content_type and "application/json" not in content_type:
            raise ValueError("content_type_must_be_application_json")
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        if length > int(self.server.max_body_bytes):
            raise ValueError("payload_too_large")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8") or "{}")
        return payload if isinstance(payload, dict) else {}

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._allow_request():
            return
        self._write_json(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if not self._allow_request():
            return
        if not self._require_channel_ready():
            return
        path = self.path.split("?", 1)[0]
        if path in {"/health", "/v1/health"}:
            self._write_json(200, _partner_health_payload())
            return
        if path in {"/meta", "/v1/permit/meta"}:
            if self.server.admin_api_keys and not self._require_api_key(admin=True):
                return
            if not self._require_feature("meta"):
                return
            self._write_json(200, {"ok": True, "meta": self.server.engine.meta})
            return
        self._write_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if not self._allow_request():
            return
        if not self._require_channel_ready():
            return
        try:
            payload = self._read_json_body() if path in {"/precheck", "/v1/permit/precheck", "/reload", "/v1/permit/reload"} else {}
        except ValueError:
            self._write_json(400, {"ok": False, "error": "invalid_request_body"})
            return
        except (TypeError, UnicodeDecodeError, OverflowError):
            self._write_json(400, {"ok": False, "error": "invalid_json"})
            return

        if path in {"/reload", "/v1/permit/reload"}:
            if not self._require_api_key(admin=True):
                return
            if not self._require_feature("reload"):
                return
            meta = self.server.engine.refresh()
            self._write_json(200, {"ok": True, "meta": meta})
            return

        if path in {"/precheck", "/v1/permit/precheck"}:
            if self.server.api_keys and not self._require_api_key(admin=False):
                return
            if is_sandbox_request(self.headers, api_key=header_token(self.headers)):
                self._write_json(200, sandbox_permit_response())
                return
            if not self._require_channel_system("permit"):
                return
            if not self._require_system("permit"):
                return
            if not self._require_feature("permit_precheck"):
                return
            bundle = normalize_v1_request(
                payload,
                headers=self.headers,
                default_source="permit_precheck_api",
                default_page_url=_compact(self.headers.get("Origin") or self.headers.get("Referer")),
            )
            request_meta = dict(bundle.get("request_meta") or {})
            hinted_request_id = _compact(request_meta.get("request_id_hint"), _LIM_SERVICE_CODE)
            if hinted_request_id and not getattr(self, "_cached_request_id", ""):
                setattr(self, "_cached_request_id", hinted_request_id)
            if not self._require_channel_hint_match(request_meta):
                return
            resolution = self._tenant_resolution()
            tenant_plan = _tenant_plan_key(resolution)
            tenant_id = _tenant_id_value(resolution)
            usage_before = self.server.usage_store.usage_snapshot(tenant_id, tenant_plan)
            if bool(usage_before.get("blocked")):
                self._write_json(
                    429,
                    {
                        "ok": False,
                        "error": "plan_usage_limit_exceeded",
                        "tenant_plan": str(usage_before.get("plan") or "unknown"),
                        "usage_events": int(usage_before.get("usage_events", 0) or 0),
                        "max_usage_events": int(usage_before.get("max_usage_events", 0) or 0),
                    },
                    extra_headers=self._usage_headers(usage_before),
                )
                return
            engine_payload = dict(bundle.get("fields") or {})
            if bundle.get("inputs"):
                engine_payload["inputs"] = dict(bundle.get("inputs") or {})
            merged_inputs = dict(bundle.get("inputs") or {})
            for key in ("service_code", "service_name", "industry_name", "rule_id"):
                if (not _compact(engine_payload.get(key))) and _compact(merged_inputs.get(key)):
                    engine_payload[key] = merged_inputs.get(key)
            result = self.server.engine.precheck(engine_payload)
            projected = _project_precheck_result(self.server, resolution, result)
            response_tier = str(((projected.get("response_policy") or {}).get("tier")) or "")
            page_url = _compact(request_meta.get("page_url"))
            requested_at = _compact(request_meta.get("requested_at"))
            inputs = dict(bundle.get("inputs") or {})
            try:
                usage_after = self.server.usage_store.insert_precheck_usage(
                    tenant_id=tenant_id,
                    plan=tenant_plan,
                    request_id=hinted_request_id,
                    source=_compact(request_meta.get("source") or "permit_precheck_api"),
                    page_url=page_url,
                    requested_at=requested_at,
                    inputs=inputs,
                    result=result,
                    response_tier=response_tier,
                )
            except (sqlite3.Error, OSError, TypeError, KeyError, ValueError):
                logger.exception("permit usage logging failed")
                usage_after = usage_before
            self._write_json(
                200 if result.get("ok") else 422,
                projected,
                extra_headers=self._usage_headers(usage_after, response_tier=response_tier),
            )
            return

        self._write_json(404, {"ok": False, "error": "not_found"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Permit precheck API server")
    parser.add_argument("--host", default=_env_str("PERMIT_PRECHECK_API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=_env_int("PERMIT_PRECHECK_API_PORT", 8792))
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG_PATH))
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--allow-origins", default=_env_str("PERMIT_PRECHECK_ALLOW_ORIGINS", ""))
    parser.add_argument("--api-key", default=_env_str("PERMIT_PRECHECK_API_KEY", ""))
    parser.add_argument("--admin-api-key", default=_env_str("PERMIT_PRECHECK_ADMIN_API_KEY", ""))
    parser.add_argument("--max-body-bytes", type=int, default=_env_int("PERMIT_PRECHECK_MAX_BODY_BYTES", 65536))
    parser.add_argument("--rate-limit-per-min", type=int, default=_env_int("PERMIT_PRECHECK_RATE_LIMIT_PER_MIN", 90))
    parser.add_argument("--trust-x-forwarded-for", action="store_true", default=_env_bool("PERMIT_PRECHECK_TRUST_X_FORWARDED_FOR", False))
    parser.add_argument("--security-log-file", default=_env_str("PERMIT_PRECHECK_SECURITY_LOG_FILE", "logs/security_permit_precheck_events.jsonl"))
    parser.add_argument("--usage-db", default=_env_str("PERMIT_PRECHECK_USAGE_DB", "logs/permit_precheck_usage.sqlite3"))
    parser.add_argument("--plan-thresholds-config", default=_env_str("PLAN_THRESHOLDS_CONFIG", "tenant_config/plan_thresholds.json"))
    parser.add_argument("--tenant-gateway-enabled", default=_env_str("TENANT_GATEWAY_ENABLED", "true"))
    parser.add_argument("--tenant-gateway-strict", default=_env_str("TENANT_GATEWAY_STRICT", "false"))
    parser.add_argument("--tenant-gateway-config", default=_env_str("TENANT_GATEWAY_CONFIG", "tenant_config/tenant_registry.json"))
    parser.add_argument("--tenant-gateway-default-tenant", default=_env_str("TENANT_GATEWAY_DEFAULT_TENANT", ""))
    parser.add_argument("--channel-router-strict", default=_env_str("CHANNEL_ROUTER_STRICT", "false"))
    parser.add_argument("--channel-profiles-config", default=_env_str("CHANNEL_PROFILES_CONFIG", "tenant_config/channel_profiles.json"))
    args = parser.parse_args()

    engine = PermitPrecheckEngine(str(args.catalog or ""), str(args.rules or ""))
    meta = engine.refresh()
    allow_origins = parse_origin_allowlist(str(args.allow_origins or ""))
    tenant_gateway_enabled = str(args.tenant_gateway_enabled or "").strip().lower() in {"1", "true", "yes", "on", "y"}
    tenant_gateway_strict = str(args.tenant_gateway_strict or "").strip().lower() in {"1", "true", "yes", "on", "y"}
    channel_router_strict = str(args.channel_router_strict or "").strip().lower() in {"1", "true", "yes", "on", "y"}
    tenant_gateway = load_gateway(
        strict=bool(tenant_gateway_strict),
        default_tenant_id=str(args.tenant_gateway_default_tenant or "").strip(),
        config_path=str(args.tenant_gateway_config or "").strip(),
    )
    channel_router = load_channel_router(
        strict=bool(channel_router_strict),
        config_path=str(args.channel_profiles_config or "").strip(),
    )
    usage_store = PermitUsageStore(
        db_path=str(args.usage_db or "").strip(),
        thresholds_path=str(args.plan_thresholds_config or "").strip(),
    )

    srv = PermitApiServer(
        (args.host, int(args.port)),
        Handler,
        engine,
        allow_origins,
        args.api_key,
        args.admin_api_key,
        args.max_body_bytes,
        args.rate_limit_per_min,
        bool(args.trust_x_forwarded_for),
        args.security_log_file,
        bool(tenant_gateway_enabled),
        tenant_gateway,
        usage_store,
        channel_router,
        bool(channel_router_strict),
    )
    logger.info("permit precheck api start: host=%s port=%s", args.host, args.port)
    logger.info("permit precheck meta: %s", meta)
    logger.info("permit precheck allow origins: %s", ",".join(sorted(allow_origins)) if allow_origins else "(none)")
    logger.info("tenant gateway: enabled=%s strict=%s tenant_count=%s", bool(tenant_gateway_enabled), bool(tenant_gateway_strict), tenant_gateway.tenant_count)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        logger.info("permit precheck api stop requested")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
