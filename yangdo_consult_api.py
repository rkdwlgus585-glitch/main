import argparse
import json
import os
import re
import signal
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from core_engine.api_response import _compact, now_iso
from core_engine.tenant_gateway import TenantGateway
from tenant_config.loader import load_gateway

from lead_intake import LeadIntakeHub
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
from utils import load_config, setup_logger

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:  # pragma: no cover - optional runtime dependency
    gspread = None
    ServiceAccountCredentials = None


CONFIG = load_config(
    {
        "YANGDO_CONSULT_API_HOST": "0.0.0.0",
        "YANGDO_CONSULT_API_PORT": "8788",
        "YANGDO_CONSULT_DB": "logs/yangdo_consult_requests.sqlite3",
        "YANGDO_CONSULT_ALLOW_ORIGINS": "https://seoulmna.kr,https://www.seoulmna.kr,https://seoulmna.co.kr,https://www.seoulmna.co.kr",
        "YANGDO_CONSULT_ENABLE_CRM": "true",
        "YANGDO_CONSULT_RUN_MATCH": "false",
        "YANGDO_CONSULT_API_KEY": "",
        "YANGDO_CONSULT_MAX_BODY_BYTES": "131072",
        "YANGDO_CONSULT_RATE_LIMIT_PER_MIN": "120",
        "YANGDO_CONSULT_TRUST_X_FORWARDED_FOR": "false",
        "YANGDO_CONSULT_SECURITY_LOG_FILE": "logs/security_consult_events.jsonl",
        "YANGDO_USAGE_SHEET_ENABLED": "true",
        "YANGDO_USAGE_JSON_FILE": "service_account.json",
        "YANGDO_USAGE_SHEET_NAME": "26양도매물",
        "YANGDO_USAGE_SHEET_TAB": "양도가계산사용로그",
        "TENANT_GATEWAY_ENABLED": "true",
        "TENANT_GATEWAY_STRICT": "false",
        "TENANT_GATEWAY_CONFIG": "tenant_config/tenant_registry.json",
        "TENANT_GATEWAY_DEFAULT_TENANT": "",
    }
)

logger = setup_logger(name="yangdo_consult_api")

# ── Input field size limits (chars) ─────────────────────────────────
_LIM_TOKEN: int = 40        # page_mode, status, phone, short tokens
_LIM_SHORT_ID: int = 80     # customer_name, lead_id, input fields, etc.
_LIM_SOURCE: int = 100      # source field
_LIM_EMAIL: int = 120       # customer_email, estimated_range, confidence
_LIM_LICENSE: int = 200     # license_text, missing_critical
_LIM_HEADER: int = 300      # HTTP Origin / Host headers, subject
_LIM_PAGE_URL: int = 500    # page_url
_LIM_NOTE: int = 1200       # customer_note, error_text (1000)
_LIM_SUMMARY: int = 12000   # summary_text
_LIM_LABEL: int = 20        # lead_priority, lead_urgency
_LIM_COMPACT: int = 30      # debt_level, liq_level
_LIM_MEDIUM: int = 60       # estimated_center, service_track, neighbors


def _cfg_bool(key, default=False) -> bool:
    value = str(CONFIG.get(key, default)).strip().lower()
    if value in {"1", "true", "yes", "on", "y"}:
        return True
    if value in {"0", "false", "no", "off", "n"}:
        return False
    return bool(default)


def _cfg_int(key, default) -> int:
    try:
        return int(str(CONFIG.get(key, default)).strip())
    except (ValueError, TypeError):
        return int(default)


def _parse_confidence_score(raw) -> float | None:
    src = str(raw or "")
    m = re.search(r"(\d+(?:\.\d+)?)", src.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except (ValueError, OverflowError):
        return None


def _priority_info(payload: dict) -> tuple[str, str]:
    score = 50.0
    text = " ".join(
        [
            str(payload.get("summary_text", "")),
            str(payload.get("customer_note", "")),
            str(payload.get("subject", "")),
        ]
    ).lower()
    conf = _parse_confidence_score(payload.get("estimated_confidence"))
    if conf is not None:
        if conf >= 80:
            score += 10
        elif conf < 50:
            score -= 8
    if str(payload.get("customer_phone", "")).strip():
        score += 8
    if str(payload.get("customer_email", "")).strip():
        score += 4
    if any(token in text for token in ["긴급", "급함", "당장", "오늘", "내일", "마감"]):
        score += 14
    if any(token in text for token in ["분할합병", "합병", "분할"]):
        score += 5
    if any(token in text for token in ["전기", "정보통신", "소방"]):
        score += 4

    if score >= 72:
        return "우선", "긴급"
    if score >= 56:
        return "중요", "보통"
    return "일반", "일반"


def _tokenize_license(raw: Any) -> list[str]:
    tokens = []
    src = str(raw or "").replace("<br>", "\n")
    for piece in re.split(r"[\n,/\|·ㆍ\s]+", src):
        t = _compact(piece, limit=_LIM_TOKEN)
        if not t:
            continue
        tokens.append(t)
    uniq = []
    seen = set()
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(token)
    return uniq[:6]


CANONICAL_MODE_YANGDO = "yangdo_calculator"
CANONICAL_MODE_PERMIT = "permit_precheck"
CANONICAL_SOURCE_YANGDO = "seoulmna_kr_yangdo_ai"
CANONICAL_SOURCE_HOT_MATCH = "seoulmna_kr_hot_match"
CANONICAL_SOURCE_PERMIT = "seoulmna_kr_permit_precheck_newreg"


def _detect_business_mode(payload: dict) -> str:
    blob = " ".join(
        [
            str(payload.get("service_track", "")),
            str(payload.get("business_domain", "")),
            str(payload.get("page_mode", "")),
            str(payload.get("source_mode", "")),
            str(payload.get("source", "")),
            str(payload.get("subject", "")),
            str(payload.get("summary_text", "")),
            str(payload.get("license_text", "")),
        ]
    ).lower()
    if any(k in blob for k in ["permit_precheck", "permit", "newreg", "acquisition", "인허가", "신규등록"]):
        return CANONICAL_MODE_PERMIT
    if any(k in blob for k in ["yangdo", "transfer_price_estimation", "양도", "mna"]):
        return CANONICAL_MODE_YANGDO
    mode = _compact(payload.get("page_mode"), limit=_LIM_TOKEN)
    return mode or "unknown"


def _canonical_source(payload: dict, mode: str) -> str:
    src = _compact(payload.get("source"), limit=_LIM_SOURCE).lower()
    if "hot_match" in src:
        return CANONICAL_SOURCE_HOT_MATCH
    if mode == CANONICAL_MODE_PERMIT:
        return CANONICAL_SOURCE_PERMIT
    if mode == CANONICAL_MODE_YANGDO:
        return CANONICAL_SOURCE_YANGDO
    return _compact(payload.get("source"), limit=_LIM_SOURCE)


def _normalize_business_payload(raw_payload: dict) -> dict:
    payload = dict(raw_payload or {})
    mode = _detect_business_mode(payload)
    canonical_source = _canonical_source(payload, mode)
    legacy_mode = _compact(payload.get("page_mode"), limit=_LIM_TOKEN)
    legacy_source = _compact(payload.get("source"), limit=_LIM_SOURCE)
    payload["page_mode"] = mode
    payload["source"] = canonical_source
    payload["service_track"] = _compact(payload.get("service_track"), limit=_LIM_SHORT_ID) or (
        "permit_precheck_new_registration" if mode == CANONICAL_MODE_PERMIT else "transfer_price_estimation"
    )
    payload["business_domain"] = _compact(payload.get("business_domain"), limit=_LIM_SHORT_ID) or (
        "permit_precheck" if mode == CANONICAL_MODE_PERMIT else "yangdo_transfer"
    )
    if legacy_mode and legacy_mode != mode and not _compact(payload.get("legacy_page_mode"), limit=_LIM_TOKEN):
        payload["legacy_page_mode"] = legacy_mode
    if legacy_source and legacy_source != canonical_source and not _compact(payload.get("legacy_source"), limit=_LIM_SOURCE):
        payload["legacy_source"] = legacy_source
    return payload


def _build_tags(payload: dict) -> list[str]:
    tags = []
    normalized = _normalize_business_payload(payload)
    source = _compact(normalized.get("source"), limit=_LIM_SHORT_ID)
    if source:
        tags.append(source)
    mode = _compact(normalized.get("page_mode"), limit=_LIM_COMPACT)
    if mode:
        tags.append(mode)
    service_track = _compact(normalized.get("service_track"), limit=_LIM_MEDIUM)
    if service_track:
        tags.append(service_track)
    for token in _tokenize_license(normalized.get("license_text", "")):
        tags.append(token)
    if str(normalized.get("estimated_neighbors", "")).strip():
        tags.append("ai산정")
    out = []
    seen = set()
    for tag in tags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out[:8]


class ConsultStore:
    """SQLite-backed store for consultation request records.

    Creates or opens a local database at *db_path*, auto-creating parent
    directories as needed.  Thread-safe for concurrent request handling
    via per-call connections with a 30-second busy timeout.
    """

    def __init__(self, db_path) -> None:
        self.db_path = str(db_path or "").strip()
        if self.db_path:
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consult_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TEXT NOT NULL,
                    source TEXT,
                    page_mode TEXT,
                    subject TEXT,
                    summary_text TEXT,
                    customer_name TEXT,
                    customer_phone TEXT,
                    customer_email TEXT,
                    customer_note TEXT,
                    license_text TEXT,
                    estimated_center TEXT,
                    estimated_range TEXT,
                    estimated_confidence TEXT,
                    estimated_neighbors TEXT,
                    page_url TEXT,
                    requested_at TEXT,
                    lead_priority TEXT,
                    lead_urgency TEXT,
                    lead_tags TEXT,
                    crm_status TEXT,
                    crm_lead_id TEXT,
                    raw_json TEXT
                )
                """
            )
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
            conn.commit()
        finally:
            conn.close()

    def insert(self, payload: dict, tags: list[str], priority: str, urgency: str) -> int:
        """Insert a consultation request and return the row ID."""
        payload = _normalize_business_payload(payload)
        row = {
            "received_at": now_iso(),
            "source": _compact(payload.get("source"), limit=_LIM_SOURCE),
            "page_mode": _compact(payload.get("page_mode"), limit=_LIM_TOKEN),
            "subject": _compact(payload.get("subject"), limit=_LIM_HEADER),
            "summary_text": _compact(payload.get("summary_text"), limit=_LIM_SUMMARY),
            "customer_name": _compact(payload.get("customer_name"), limit=_LIM_SHORT_ID),
            "customer_phone": _compact(payload.get("customer_phone"), limit=_LIM_TOKEN),
            "customer_email": _compact(payload.get("customer_email"), limit=_LIM_EMAIL),
            "customer_note": _compact(payload.get("customer_note"), limit=_LIM_NOTE),
            "license_text": _compact(payload.get("license_text"), limit=_LIM_LICENSE),
            "estimated_center": _compact(payload.get("estimated_center"), limit=_LIM_MEDIUM),
            "estimated_range": _compact(payload.get("estimated_range"), limit=_LIM_EMAIL),
            "estimated_confidence": _compact(payload.get("estimated_confidence"), limit=_LIM_EMAIL),
            "estimated_neighbors": _compact(payload.get("estimated_neighbors"), limit=_LIM_MEDIUM),
            "page_url": _compact(payload.get("page_url"), limit=_LIM_PAGE_URL),
            "requested_at": _compact(payload.get("requested_at"), limit=_LIM_SHORT_ID),
            "lead_priority": _compact(priority, limit=_LIM_LABEL),
            "lead_urgency": _compact(urgency, limit=_LIM_LABEL),
            "lead_tags": ",".join(tags),
            "crm_status": "pending",
            "crm_lead_id": "",
            "raw_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        }
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            cur = conn.execute(
                """
                INSERT INTO consult_requests (
                    received_at, source, page_mode, subject, summary_text,
                    customer_name, customer_phone, customer_email, customer_note,
                    license_text, estimated_center, estimated_range, estimated_confidence,
                    estimated_neighbors, page_url, requested_at,
                    lead_priority, lead_urgency, lead_tags, crm_status, crm_lead_id, raw_json
                ) VALUES (
                    :received_at, :source, :page_mode, :subject, :summary_text,
                    :customer_name, :customer_phone, :customer_email, :customer_note,
                    :license_text, :estimated_center, :estimated_range, :estimated_confidence,
                    :estimated_neighbors, :page_url, :requested_at,
                    :lead_priority, :lead_urgency, :lead_tags, :crm_status, :crm_lead_id, :raw_json
                )
                """,
                row,
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def insert_usage(self, payload: dict) -> int:
        """Insert a usage log entry and return the row ID."""
        payload = _normalize_business_payload(payload)
        row = {
            "received_at": now_iso(),
            "source": _compact(payload.get("source"), limit=_LIM_SOURCE),
            "page_mode": _compact(payload.get("page_mode"), limit=_LIM_TOKEN),
            "status": _compact(payload.get("status"), limit=_LIM_TOKEN),
            "error_text": _compact(payload.get("error_text"), limit=_LIM_NOTE),
            "license_text": _compact(payload.get("license_text"), limit=_LIM_LICENSE),
            "input_specialty": _compact(payload.get("input_specialty"), limit=_LIM_SHORT_ID),
            "input_y23": _compact(payload.get("input_y23"), limit=_LIM_SHORT_ID),
            "input_y24": _compact(payload.get("input_y24"), limit=_LIM_SHORT_ID),
            "input_y25": _compact(payload.get("input_y25"), limit=_LIM_SHORT_ID),
            "input_balance": _compact(payload.get("input_balance"), limit=_LIM_SHORT_ID),
            "input_capital": _compact(payload.get("input_capital"), limit=_LIM_SHORT_ID),
            "input_surplus": _compact(payload.get("input_surplus"), limit=_LIM_SHORT_ID),
            "input_debt_level": _compact(payload.get("input_debt_level"), limit=_LIM_COMPACT),
            "input_liq_level": _compact(payload.get("input_liq_level"), limit=_LIM_COMPACT),
            "ok_capital": "1" if bool(payload.get("ok_capital")) else "0",
            "ok_engineer": "1" if bool(payload.get("ok_engineer")) else "0",
            "ok_office": "1" if bool(payload.get("ok_office")) else "0",
            "output_center": _compact(payload.get("output_center"), limit=_LIM_SHORT_ID),
            "output_range": _compact(payload.get("output_range"), limit=_LIM_EMAIL),
            "output_confidence": _compact(payload.get("output_confidence"), limit=_LIM_EMAIL),
            "output_neighbors": _compact(payload.get("output_neighbors"), limit=_LIM_SHORT_ID),
            "missing_critical": _compact(payload.get("missing_critical"), limit=_LIM_LICENSE),
            "page_url": _compact(payload.get("page_url"), limit=_LIM_PAGE_URL),
            "requested_at": _compact(payload.get("requested_at"), limit=_LIM_SHORT_ID),
            "raw_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        }
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
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def update_crm_result(self, request_id: int, status: str, lead_id: str = "") -> None:
        """Update CRM sync status for a previously inserted consultation."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            conn.execute(
                "UPDATE consult_requests SET crm_status=?, crm_lead_id=? WHERE id=?",
                (str(status or ""), str(lead_id or ""), int(request_id or 0)),
            )
            conn.commit()
        finally:
            conn.close()


class UsageSheetWriter:
    """Google Sheets writer for estimation usage telemetry.

    Appends one row per API estimation call, capturing input parameters,
    output results, and diagnostic metadata.  Silently no-ops when
    credentials are unavailable so the main API path is never blocked.
    """

    HEADERS = [
        "received_at",
        "source",
        "page_mode",
        "service_track",
        "business_domain",
        "source_mode",
        "status",
        "error_text",
        "license_text",
        "input_specialty",
        "input_y23",
        "input_y24",
        "input_y25",
        "input_balance",
        "input_capital",
        "input_surplus",
        "input_debt_level",
        "input_liq_level",
        "ok_capital",
        "ok_engineer",
        "ok_office",
        "output_center",
        "output_range",
        "output_confidence",
        "output_neighbors",
        "missing_critical",
        "page_url",
        "requested_at",
    ]

    def __init__(self, enabled: bool = True, json_file: str = "service_account.json", sheet_name: str = "26양도매물", tab_name: str = "양도가계산사용로그") -> None:
        self.enabled = bool(enabled)
        self.json_file = str(json_file or "").strip()
        self.sheet_name = str(sheet_name or "").strip()
        self.tab_name = str(tab_name or "").strip()
        self._ws = None
        self._lock = threading.Lock()

    def _connect(self) -> Any:
        if not self.enabled:
            return None
        if gspread is None or ServiceAccountCredentials is None:
            raise RuntimeError("gspread_not_available")
        if not self.json_file:
            raise RuntimeError("json_file_missing")
        if not os.path.exists(self.json_file):
            raise RuntimeError(f"json_file_not_found:{self.json_file}")

        with self._lock:
            if self._ws is not None:
                return self._ws
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.json_file, scope)
            gc = gspread.authorize(creds)
            book = gc.open(self.sheet_name)
            try:
                ws = book.worksheet(self.tab_name)
            except gspread.exceptions.WorksheetNotFound:
                ws = book.add_worksheet(title=self.tab_name, rows=2000, cols=max(30, len(self.HEADERS) + 4))
            first = ws.row_values(1)
            if not first:
                ws.append_row(self.HEADERS, value_input_option="RAW")
            self._ws = ws
            return self._ws

    def append_usage(self, payload: dict) -> dict:
        """Append a usage row to the Google Sheet, returning status."""
        if not self.enabled:
            return {"ok": False, "reason": "disabled"}
        try:
            payload = _normalize_business_payload(payload)
            ws = self._connect()
            if ws is None:
                return {"ok": False, "reason": "worksheet_unavailable"}
            row = [
                now_iso(),
                _compact(payload.get("source"), 100),
                _compact(payload.get("page_mode"), 40),
                _compact(payload.get("service_track"), 80),
                _compact(payload.get("business_domain"), 80),
                _compact(payload.get("source_mode"), 40),
                _compact(payload.get("status"), 40),
                _compact(payload.get("error_text"), 1000),
                _compact(payload.get("license_text"), 200),
                _compact(payload.get("input_specialty"), 80),
                _compact(payload.get("input_y23"), 80),
                _compact(payload.get("input_y24"), 80),
                _compact(payload.get("input_y25"), 80),
                _compact(payload.get("input_balance"), 80),
                _compact(payload.get("input_capital"), 80),
                _compact(payload.get("input_surplus"), 80),
                _compact(payload.get("input_debt_level"), 30),
                _compact(payload.get("input_liq_level"), 30),
                "1" if bool(payload.get("ok_capital")) else "0",
                "1" if bool(payload.get("ok_engineer")) else "0",
                "1" if bool(payload.get("ok_office")) else "0",
                _compact(payload.get("output_center"), 80),
                _compact(payload.get("output_range"), 120),
                _compact(payload.get("output_confidence"), 120),
                _compact(payload.get("output_neighbors"), 80),
                _compact(payload.get("missing_critical"), 200),
                _compact(payload.get("page_url"), 500),
                _compact(payload.get("requested_at"), 80),
            ]
            ws.append_row(row, value_input_option="USER_ENTERED")
            return {"ok": True}
        except Exception:  # pragma: no cover - external dependency
            logger.exception("usage sheet append failed")
            return {"ok": False, "reason": "sheet_append_failed"}


class CrmBridge:
    """Thread-safe bridge to the CRM lead intake system.

    Lazily connects to :class:`LeadIntakeHub` on first use and caches
    the connection behind a lock.  Normalises business payloads before
    submission and maps CRM outcomes to a simple status dict.
    """

    def __init__(self, enabled: bool = True, run_match: bool = False) -> None:
        self.enabled = bool(enabled)
        self.run_match = bool(run_match)
        self._hub = None
        self._hub_lock = threading.Lock()

    def _connect(self) -> Any:
        if not self.enabled:
            return None
        with self._hub_lock:
            if self._hub is not None:
                return self._hub
            hub = LeadIntakeHub()
            hub.connect()
            self._hub = hub
            return hub

    def submit(self, payload: dict, tags: list[str], urgency: str) -> dict:
        """Submit a lead to CRM, returning status and lead_id."""
        if not self.enabled:
            return {"status": "disabled", "lead_id": ""}
        normalized = _normalize_business_payload(payload)
        try:
            hub = self._connect()
        except Exception:
            logger.exception("crm connect failed")
            return {"status": "crm_connect_error", "lead_id": ""}

        contact = _compact(normalized.get("customer_phone")) or _compact(normalized.get("customer_email"))
        title = _compact(normalized.get("subject")) or "서울건설정보 AI 산정 상담 요청"
        summary = _compact(normalized.get("summary_text"), limit=_LIM_SUMMARY)
        if tags:
            summary += f"\n\n[자동 태그] {', '.join(tags)}"
        mode = _compact(normalized.get("page_mode"), limit=_LIM_TOKEN)
        intent = "인허가(신규등록)" if mode == CANONICAL_MODE_PERMIT else "양도양수"
        channel = "permit_precheck_web" if mode == CANONICAL_MODE_PERMIT else "yangdo_ai_web"

        out = {}
        try:
            out = hub.intake_one(
                {
                    "title": title,
                    "content": summary,
                    "channel": channel,
                    "customer_name": _compact(normalized.get("customer_name"), limit=_LIM_SHORT_ID),
                    "contact": contact,
                    "source": _compact(normalized.get("page_url"), limit=_LIM_PAGE_URL),
                    "urgency": urgency,
                    "intent": intent,
                },
                dry_run=False,
            )
        except Exception:
            logger.exception("crm intake failed")
            return {"status": "crm_insert_error", "lead_id": ""}

        status = _compact(out.get("status"), limit=_LIM_TOKEN) or "unknown"
        lead_id = _compact(out.get("lead_id"), limit=_LIM_SHORT_ID)
        return {"status": status, "lead_id": lead_id}


class YangdoConsultApiHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the yangdo consultation API.

    Routes GET (health, status) and POST (submit, consult, usage)
    requests with per-request tenant resolution, feature gating,
    rate limiting, and CORS enforcement.
    """

    server_version = "YangdoConsultAPI/1.1"

    def _request_id(self) -> str:
        cached = getattr(self, "_cached_request_id", "")
        if cached:
            return str(cached)
        incoming = _compact(
            self.headers.get("X-Request-Id") or self.headers.get("X-Correlation-Id"),
            limit=_LIM_HEADER,
        )
        if not incoming:
            incoming = uuid.uuid4().hex
        setattr(self, "_cached_request_id", incoming)
        return incoming

    def _allow_origin(self) -> str:
        req_origin = _compact(self.headers.get("Origin"), limit=_LIM_HEADER)
        return resolve_allow_origin(req_origin, self.server.allowed_origins)

    def _client_ip(self) -> str:
        return safe_client_ip(self, trust_x_forwarded_for=bool(self.server.trust_x_forwarded_for))

    def _tenant_resolution(self) -> Any:
        return self.server.tenant_gateway.resolve(
            host=_compact(self.headers.get("Host"), limit=_LIM_HEADER),
            origin=_compact(self.headers.get("Origin"), limit=_LIM_HEADER),
        )

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
                "service": "yangdo_consult_api",
                "path": self.path.split("?", 1)[0],
                "feature": str(feature or ""),
                "ip": self._client_ip(),
                "host": _compact(self.headers.get("Host"), limit=_LIM_HEADER),
                "origin": _compact(self.headers.get("Origin"), limit=_LIM_HEADER),
                "tenant_id": tenant_id,
            }
        )
        self._write_json(403, {"ok": False, "error": "tenant_not_allowed"})
        return False

    def _require_auth(self) -> bool:
        token = header_token(self.headers, "x")
        if token and bool(self.server.tenant_gateway_enabled):
            resolution = self._tenant_resolution()
            if self.server.tenant_gateway.is_token_blocked(resolution, token):
                tenant_id = ""
                if resolution.tenant is not None:
                    tenant_id = str(resolution.tenant.tenant_id or "")
                self.server.security_events.append(
                    {
                        "event": "auth_blocked_key",
                        "service": "yangdo_consult_api",
                        "path": self.path.split("?", 1)[0],
                        "ip": self._client_ip(),
                        "origin": _compact(self.headers.get("Origin"), limit=_LIM_HEADER),
                        "host": _compact(self.headers.get("Host"), limit=_LIM_HEADER),
                        "tenant_id": tenant_id,
                    }
                )
                self._write_json(401, {"ok": False, "error": "blocked_api_key"})
                return False
        if is_authorized_any(self.headers, self.server.api_keys):
            return True
        self.server.security_events.append(
            {
                "event": "auth_failed",
                "service": "yangdo_consult_api",
                "path": self.path.split("?", 1)[0],
                "ip": self._client_ip(),
                "origin": _compact(self.headers.get("Origin"), limit=_LIM_HEADER),
            }
        )
        self._write_json(401, {"ok": False, "error": "unauthorized"})
        return False

    def _allow_request(self) -> bool:
        ok, retry_after = self.server.rate_limiter.allow(self._client_ip())
        if ok:
            return True
        self.server.security_events.append(
            {
                "event": "rate_limited",
                "service": "yangdo_consult_api",
                "path": self.path.split("?", 1)[0],
                "ip": self._client_ip(),
                "retry_after": int(max(1, int(retry_after))),
            }
        )
        self._write_json(
            429,
            {"ok": False, "error": "rate_limited"},
            extra_headers={"Retry-After": str(max(1, int(retry_after)))},
        )
        return False

    def _write_json(self, status: int, data: dict, extra_headers: dict[str, str] | None = None) -> None:
        request_id = self._request_id()
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        allow_origin = self._allow_origin()
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-Id", request_id)
        for hk, hv in DEFAULT_SECURITY_HEADERS:
            self.send_header(hk, hv)
        if allow_origin:
            self.send_header("Access-Control-Allow-Origin", allow_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key, X-Request-Id, X-Correlation-Id")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        if isinstance(extra_headers, dict):
            for hk, hv in extra_headers.items():
                if hk and hv is not None:
                    self.send_header(str(hk), str(hv))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # Client disconnected before reading response.
            pass

    def _read_json(self) -> dict:
        content_type = str(self.headers.get("Content-Type", "") or "").lower()
        if content_type and "application/json" not in content_type:
            raise ValueError("content_type_must_be_application_json")
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        if length > int(self.server.max_body_bytes):
            raise ValueError("payload_too_large")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        if not self._allow_request():
            return
        self._write_json(200, {"ok": True})

    def do_GET(self) -> None:
        """Route GET requests to /health endpoint."""
        path = self.path.split("?", 1)[0].rstrip("/")
        if not self._allow_request():
            return
        if path == "/health":
            self._write_json(
                200,
                {
                    "ok": True,
                    "service": "yangdo_consult_api",
                    "time": now_iso(),
                    "crm_enabled": bool(self.server.crm_bridge.enabled),
                    "usage_sheet_enabled": bool(self.server.usage_sheet.enabled),
                },
            )
            return
        self._write_json(404, {"ok": False, "error": "not_found"})

    def _handle_consult(self, payload: dict) -> None:
        payload = _normalize_business_payload(payload)
        name = _compact(payload.get("customer_name"), limit=_LIM_SHORT_ID)
        phone = _compact(payload.get("customer_phone"), limit=_LIM_TOKEN)
        email = _compact(payload.get("customer_email"), limit=_LIM_EMAIL)
        if not name:
            self._write_json(400, {"ok": False, "error": "customer_name_required"})
            return
        if not phone and not email:
            self._write_json(400, {"ok": False, "error": "phone_or_email_required"})
            return

        priority, urgency = _priority_info(payload)
        tags = _build_tags(payload)

        try:
            request_id = self.server.store.insert(payload, tags, priority, urgency)
        except (sqlite3.Error, OSError):
            logger.exception("db insert failed")
            self._write_json(500, {"ok": False, "error": "db_insert_failed"})
            return

        crm = self.server.crm_bridge.submit(payload, tags, urgency)
        crm_status = _compact(crm.get("status"), limit=_LIM_EMAIL)
        crm_lead_id = _compact(crm.get("lead_id"), limit=_LIM_SHORT_ID)
        try:
            self.server.store.update_crm_result(request_id, crm_status, crm_lead_id)
        except (sqlite3.Error, OSError):
            logger.exception("db update crm result failed")

        self._write_json(
            200,
            {
                "ok": True,
                "request_id": int(request_id),
                "lead_priority": priority,
                "lead_urgency": urgency,
                "lead_tags": tags,
                "crm_status": crm_status,
                "crm_lead_id": crm_lead_id,
                "received_at": now_iso(),
            },
        )
        self.server.security_events.append(
            {
                "event": "consult_accepted",
                "service": "yangdo_consult_api",
                "path": "/consult",
                "ip": self._client_ip(),
                "db_request_id": int(request_id),
                "correlation_id": self._request_id(),
            }
        )

    def _handle_usage(self, payload: dict) -> None:
        payload = _normalize_business_payload(payload)
        try:
            usage_id = self.server.store.insert_usage(payload)
        except (sqlite3.Error, OSError):
            logger.exception("usage db insert failed")
            self._write_json(500, {"ok": False, "error": "usage_db_insert_failed"})
            return

        sheet_result = self.server.usage_sheet.append_usage(payload)
        self._write_json(
            200,
            {
                "ok": True,
                "usage_id": int(usage_id),
                "sheet_logged": bool(sheet_result.get("ok")),
                "sheet_reason": _compact(sheet_result.get("reason"), limit=_LIM_HEADER),
                "received_at": now_iso(),
            },
        )
        self.server.security_events.append(
            {
                "event": "usage_logged",
                "service": "yangdo_consult_api",
                "path": "/usage",
                "ip": self._client_ip(),
                "usage_id": int(usage_id),
                "correlation_id": self._request_id(),
            }
        )

    def do_POST(self) -> None:
        """Route POST requests to /consult or /usage endpoints."""
        path = self.path.rstrip("/")
        if path not in {"/consult", "/usage"}:
            self._write_json(404, {"ok": False, "error": "not_found"})
            return
        if not self._allow_request():
            return
        if not self._require_auth():
            return
        try:
            payload = self._read_json()
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            self._write_json(400, {"ok": False, "error": "invalid_json"})
            return
        except ValueError:
            self._write_json(400, {"ok": False, "error": "invalid_request_body"})
            return

        if path == "/consult":
            if not self._require_feature("consult"):
                return
            self._handle_consult(payload)
            return
        if not self._require_feature("usage"):
            return
        self._handle_usage(payload)


class YangdoConsultApiServer(ThreadingHTTPServer):
    """Multi-tenant threading HTTP server for yangdo consultation.

    Wires together :class:`ConsultStore`, :class:`UsageSheetWriter`,
    :class:`CrmBridge`, and security primitives (rate limiter, tenant
    gateway, CORS origins) into a single server instance.
    """

    def __init__(
        self,
        addr: tuple[str, int],
        handler_cls: type,
        store: "ConsultStore",
        crm_bridge: "CrmBridge",
        allowed_origins: set[str] | list[str] | None,
        usage_sheet: "UsageSheetWriter",
        api_key: str,
        max_body_bytes: int,
        rate_limit_per_min: int,
        trust_x_forwarded_for: bool,
        security_log_file: str,
        tenant_gateway_enabled: bool,
        tenant_gateway: Any,
    ) -> None:
        super().__init__(addr, handler_cls)
        self.store = store
        self.crm_bridge = crm_bridge
        self.allowed_origins = set(allowed_origins or [])
        self.usage_sheet = usage_sheet
        self.api_keys = parse_key_values(str(api_key or ""))
        self.max_body_bytes = max(1024, int(max_body_bytes or 131072))
        self.rate_limiter = SlidingWindowRateLimiter(limit=max(1, min(10000, int(rate_limit_per_min or 120))), window_seconds=60)
        self.trust_x_forwarded_for = bool(trust_x_forwarded_for)
        self.security_events = SecurityEventLogger(str(security_log_file or ""))
        self.tenant_gateway_enabled = bool(tenant_gateway_enabled)
        self.tenant_gateway = tenant_gateway if isinstance(tenant_gateway, TenantGateway) else TenantGateway([], strict=False, default_tenant_id="")


def _parse_origins(raw: str) -> list[str]:
    return sorted(parse_origin_allowlist(str(raw or "")))


def main() -> None:
    """Parse CLI arguments and start the yangdo consultation HTTP server."""
    parser = argparse.ArgumentParser(description="서울건설정보 양도가 계산기 상담/사용 로그 API 서버")
    parser.add_argument("--host", default=str(CONFIG.get("YANGDO_CONSULT_API_HOST", "0.0.0.0")).strip())
    parser.add_argument("--port", type=int, default=_cfg_int("YANGDO_CONSULT_API_PORT", 8788))
    parser.add_argument("--db-path", default=str(CONFIG.get("YANGDO_CONSULT_DB", "logs/yangdo_consult_requests.sqlite3")).strip())
    parser.add_argument("--allow-origins", default=str(CONFIG.get("YANGDO_CONSULT_ALLOW_ORIGINS", "")).strip())
    parser.add_argument("--api-key", default=str(CONFIG.get("YANGDO_CONSULT_API_KEY", "")).strip())
    parser.add_argument("--max-body-bytes", type=int, default=_cfg_int("YANGDO_CONSULT_MAX_BODY_BYTES", 131072))
    parser.add_argument("--rate-limit-per-min", type=int, default=_cfg_int("YANGDO_CONSULT_RATE_LIMIT_PER_MIN", 120))
    parser.add_argument("--trust-x-forwarded-for", action="store_true", default=_cfg_bool("YANGDO_CONSULT_TRUST_X_FORWARDED_FOR", False))
    parser.add_argument("--security-log-file", default=str(CONFIG.get("YANGDO_CONSULT_SECURITY_LOG_FILE", "logs/security_consult_events.jsonl")).strip())
    parser.add_argument("--disable-crm", action="store_true")
    parser.add_argument("--run-match", action="store_true", default=_cfg_bool("YANGDO_CONSULT_RUN_MATCH", False))
    parser.add_argument("--disable-usage-sheet", action="store_true")
    parser.add_argument("--tenant-gateway-enabled", default=str(CONFIG.get("TENANT_GATEWAY_ENABLED", "true")).strip())
    parser.add_argument("--tenant-gateway-strict", default=str(CONFIG.get("TENANT_GATEWAY_STRICT", "false")).strip())
    parser.add_argument("--tenant-gateway-config", default=str(CONFIG.get("TENANT_GATEWAY_CONFIG", "tenant_config/tenant_registry.json")).strip())
    parser.add_argument("--tenant-gateway-default-tenant", default=str(CONFIG.get("TENANT_GATEWAY_DEFAULT_TENANT", "")).strip())
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error(f"port must be 1-65535, got {args.port}")

    db_path = os.path.abspath(args.db_path)

    # ── fail-fast: verify database directory is writable ──
    db_dir = os.path.dirname(db_path) or "."
    if not os.path.isdir(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            parser.error(f"cannot create database directory: {db_dir}")
    if not os.access(db_dir, os.W_OK):
        parser.error(f"database directory not writable: {db_dir}")

    allow_origins = _parse_origins(args.allow_origins)
    api_key = str(args.api_key or "").strip()
    api_keys = parse_key_values(api_key)
    enable_crm = _cfg_bool("YANGDO_CONSULT_ENABLE_CRM", True) and (not args.disable_crm)
    enable_usage_sheet = _cfg_bool("YANGDO_USAGE_SHEET_ENABLED", True) and (not args.disable_usage_sheet)

    usage_sheet = UsageSheetWriter(
        enabled=enable_usage_sheet,
        json_file=str(CONFIG.get("YANGDO_USAGE_JSON_FILE", "service_account.json")).strip(),
        sheet_name=str(CONFIG.get("YANGDO_USAGE_SHEET_NAME", "26양도매물")).strip(),
        tab_name=str(CONFIG.get("YANGDO_USAGE_SHEET_TAB", "양도가계산사용로그")).strip(),
    )

    store = ConsultStore(db_path)
    crm = CrmBridge(enabled=enable_crm, run_match=bool(args.run_match))
    tenant_gateway_enabled = str(args.tenant_gateway_enabled or "").strip().lower() in {"1", "true", "yes", "on", "y"}
    tenant_gateway_strict = str(args.tenant_gateway_strict or "").strip().lower() in {"1", "true", "yes", "on", "y"}
    tenant_gateway = load_gateway(
        strict=bool(tenant_gateway_strict),
        default_tenant_id=str(args.tenant_gateway_default_tenant or "").strip(),
        config_path=str(args.tenant_gateway_config or "").strip(),
    )

    srv = YangdoConsultApiServer(
        (args.host, int(args.port)),
        YangdoConsultApiHandler,
        store,
        crm,
        allow_origins,
        usage_sheet,
        api_key,
        args.max_body_bytes,
        args.rate_limit_per_min,
        bool(args.trust_x_forwarded_for),
        args.security_log_file,
        bool(tenant_gateway_enabled),
        tenant_gateway,
    )

    logger.info("consult api start: host=%s port=%s db=%s crm_enabled=%s usage_sheet=%s", args.host, args.port, db_path, enable_crm, enable_usage_sheet)
    logger.info("consult api allow origins: %s", ",".join(allow_origins) if allow_origins else "(none)")
    logger.info("consult api auth enabled: %s", bool(api_keys))
    logger.info("consult api auth key count: %s", len(api_keys))
    logger.info("consult api request caps: max_body_bytes=%s rate_limit_per_min=%s trust_xff=%s", args.max_body_bytes, args.rate_limit_per_min, bool(args.trust_x_forwarded_for))
    logger.info("consult api security log file: %s", args.security_log_file)
    logger.info("tenant gateway: enabled=%s strict=%s tenant_count=%s default_tenant=%s config=%s", bool(tenant_gateway_enabled), bool(tenant_gateway_strict), tenant_gateway.tenant_count, str(args.tenant_gateway_default_tenant or ""), str(args.tenant_gateway_config or ""))
    logger.info("consult endpoint: http://%s:%s/consult", args.host, args.port)
    logger.info("usage endpoint: http://%s:%s/usage", args.host, args.port)
    def _graceful_shutdown(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        logger.info("consult api received %s, shutting down", sig_name)
        srv.shutdown()

    signal.signal(signal.SIGTERM, _graceful_shutdown)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        logger.info("consult api stop requested")
    finally:
        try:
            srv.server_close()
        except OSError:
            pass


if __name__ == "__main__":
    main()


