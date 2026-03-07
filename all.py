import argparse
import atexit
import csv
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timedelta
from html import escape
from urllib.parse import urljoin, urlparse

import gspread
import requests
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import yangdo_calculator as _yangdo_calculator
from utils import load_config

# ======================================================
# [설정]
# ======================================================
CONFIG = load_config(
    {
        "TARGET_URL": "http://www.nowmna.com/yangdo_list1.php",
        "JSON_FILE": "service_account.json",
        "SHEET_NAME": "26양도매물",
        "TAB_PRICE_REVIEW": "가격검수큐",
        "TAB_YANGDO_ESTIMATE": "양도가산정",
        "YANGDO_CALCULATOR_OUTPUT": "output/yangdo_price_calculator.html",
        "YANGDO_CALCULATOR_SUBJECT": "AI 양도가 산정 계산기 | 서울건설정보",
        "YANGDO_CALCULATOR_MODE": "customer",
        "YANGDO_CALCULATOR_BOARD_SLUG": "",
        "YANGDO_CONSULT_ENDPOINT": "",
        "YANGDO_USAGE_ENDPOINT": "",
        "YANGDO_ESTIMATE_ENDPOINT": "",
        "YANGDO_WIDGET_API_KEY": "",
        "YANGDO_ENABLE_CONSULT_WIDGET": "false",
        "YANGDO_ENABLE_USAGE_LOG": "false",
        "YANGDO_ENABLE_HOT_MATCH": "false",
        "KAKAO_OPENCHAT_URL": "",
        "CALCULATOR_CONTACT_PHONE": "",
        "SCAN_PAGES": "3",
        "MY_COMPANY_NAME": "서울건설정보",
        "PHONE": "",
        "MY_PHONE": "",
        "STOP_IF_DUPLICATE_COUNT": "5",
        "SITE_URL": "https://seoulmna.co.kr",
        "MNA_BOARD_SLUG": "mna",
        "UPLOAD_ENABLED": "true",
        "UPLOAD_STATE_FILE": "all_upload_state.json",
        "UPLOAD_MAX_PER_RUN": "50",
        "UPLOAD_DELAY_SEC": "0.8",
        "UPLOAD_AUTO_CONTINUE": "true",
        "KOREAN_QUALITY_FIX": "true",
        "SCHEMA_GUARD_ENABLED": "true",
        "SCHEMA_ALERT_LOG": "logs/schema_alerts.log",
        "RECONCILE_AUDIT_DIR": "logs/reconcile_audit",
        "RECONCILE_DASHBOARD_DIR": "logs/dashboard",
        "RECONCILE_LOCK_FILE": "logs/reconcile.lock",
        "RECONCILE_RUN_STATE_FILE": "logs/reconcile_run_state.json",
        "RECONCILE_MIN_INTERVAL_SEC": "300",
        "RECONCILE_LOCK_STALE_SEC": "7200",
        "SCHEDULER_STATE_FILE": "scheduler_catchup_state.json",
        "SCHEDULE_TARGET_HOUR": "21",
        "SCHEDULE_LOOKBACK_DAYS": "7",
        "RECONCILE_NOWMNA_MAX_PAGES": "300",
        "RECONCILE_SEOUL_MAX_PAGES": "0",
        "RECONCILE_MAX_UPDATES": "0",
        "RECONCILE_DELAY_SEC": "0.25",
        "SEOUL_DAILY_LIMIT_STATE_FILE": "logs/seoul_daily_limit_state.json",
        "SEOUL_DAILY_REQUEST_CAP": "500",
        "SEOUL_DAILY_WRITE_CAP": "80",
        "SEOUL_TRAFFIC_GUARD_ENABLED": "true",
        "SEOUL_TRAFFIC_GUARD_REQUEST_BUFFER": "24",
        "SEOUL_TRAFFIC_GUARD_WRITE_BUFFER": "6",
        "SEOUL_TRAFFIC_GUARD_MIN_INTERVAL_SEC": "0.35",
        "SEOUL_TRAFFIC_GUARD_REPORT_FILE": "logs/seoul_co_traffic_guard_latest.json",
        "SEOUL_TRAFFIC_GUARD_SESSION_DIR": "logs/seoul_co_traffic_guard",
        "SEOUL_TRAFFIC_GUARD_LOCK_FILE": "logs/seoul_co_traffic_guard.lock",
        "SEOUL_TRAFFIC_GUARD_LOCK_STALE_SEC": "10800",
        "STRICT_DOMAIN_GUARD": "true",
        "ADMIN_MEMO_REQUIRE_BR": "true",
        "SHEET_ROW_JUMP_WATCHDOG_FILE": "logs/sheet_row_jump_watchdog_latest.json",
        "SHEET_ROW_JUMP_ABORT_ON_RISK": "true",
        "DEFER_QUEUE_FILE": "logs/deferred_requeue_queue.json",
        "DEFER_REQUEST_PATTERNS": "리퀘스트,request,삭제후,삭제 후,나중,재등록,보류요청,추가요청",
        "LISTING_QUALITY_GATE_STRICT": "true",
        "LISTING_QUALITY_MIN_SCORE": "35",
        "LOW_QUALITY_QUEUE_FILE": "logs/low_quality_listing_queue.json",
        "MEMO_TYPO_CHECK": "true",
        "MEMO_TYPO_FIX": "false",
        "MEMO_TYPO_APPROVE_ALL": "false",
        "MEMO_TYPO_APPROVED_UIDS": "",
    }
)

TARGET_URL = str(CONFIG.get("TARGET_URL", "")).strip()
JSON_FILE = str(CONFIG.get("JSON_FILE", "service_account.json")).strip()
SHEET_NAME = str(CONFIG.get("SHEET_NAME", "26양도매물")).strip()
TAB_PRICE_REVIEW = str(CONFIG.get("TAB_PRICE_REVIEW", "가격검수큐")).strip() or "가격검수큐"
TAB_YANGDO_ESTIMATE = str(CONFIG.get("TAB_YANGDO_ESTIMATE", "양도가산정")).strip() or "양도가산정"
YANGDO_CALCULATOR_OUTPUT = (
    str(CONFIG.get("YANGDO_CALCULATOR_OUTPUT", "output/yangdo_price_calculator.html")).strip()
    or "output/yangdo_price_calculator.html"
)
YANGDO_CALCULATOR_SUBJECT = (
    str(CONFIG.get("YANGDO_CALCULATOR_SUBJECT", "서울건설정보 | 양도가 산정 시스템")).strip()
    or "서울건설정보 | 양도가 산정 시스템"
)
YANGDO_CALCULATOR_MODE = (
    str(CONFIG.get("YANGDO_CALCULATOR_MODE", "customer")).strip().lower()
    or "customer"
)
if YANGDO_CALCULATOR_MODE not in {"customer", "owner"}:
    YANGDO_CALCULATOR_MODE = "customer"
YANGDO_CALCULATOR_BOARD_SLUG = str(CONFIG.get("YANGDO_CALCULATOR_BOARD_SLUG", "")).strip()
YANGDO_CONSULT_ENDPOINT_RAW = str(CONFIG.get("YANGDO_CONSULT_ENDPOINT", "")).strip()
YANGDO_USAGE_ENDPOINT_RAW = str(CONFIG.get("YANGDO_USAGE_ENDPOINT", "")).strip()
YANGDO_ESTIMATE_ENDPOINT_RAW = str(CONFIG.get("YANGDO_ESTIMATE_ENDPOINT", "")).strip()
YANGDO_WIDGET_API_KEY = str(CONFIG.get("YANGDO_WIDGET_API_KEY", "")).strip()
KAKAO_OPENCHAT_URL = str(CONFIG.get("KAKAO_OPENCHAT_URL", "")).strip()
CALCULATOR_CONTACT_PHONE = (
    str(CONFIG.get("CALCULATOR_CONTACT_PHONE", "")).strip()
    or str(CONFIG.get("PHONE", "") or CONFIG.get("MY_PHONE", "")).strip()
    or "010-9926-8661"
)
if "1668" in str(CALCULATOR_CONTACT_PHONE):
    CALCULATOR_CONTACT_PHONE = "010-9926-8661"
MY_COMPANY_NAME = str(CONFIG.get("MY_COMPANY_NAME", "서울건설정보")).strip()
MY_PHONE = str(CONFIG.get("PHONE", "") or CONFIG.get("MY_PHONE", "")).strip()
SITE_URL = str(CONFIG.get("SITE_URL", "https://seoulmna.co.kr")).rstrip("/")
MNA_BOARD_SLUG = str(CONFIG.get("MNA_BOARD_SLUG", "mna")).strip() or "mna"
UPLOAD_STATE_FILE = str(CONFIG.get("UPLOAD_STATE_FILE", "all_upload_state.json")).strip()


def _cfg_int(key, default):
    try:
        return int(str(CONFIG.get(key, default)).strip())
    except Exception:
        return default


def _cfg_float(key, default):
    try:
        return float(str(CONFIG.get(key, default)).strip())
    except Exception:
        return default


def _cfg_bool(key, default=False):
    val = str(CONFIG.get(key, default)).strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _host_of(url):
    src = str(url or "").strip()
    if not src:
        return ""
    if "://" not in src:
        src = f"https://{src}"
    host = urlparse(src).netloc.lower()
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def _sanitize_public_endpoint(url):
    src = str(url or "").strip()
    if not src:
        return ""
    host = _host_of(src)
    if host in {"127.0.0.1", "localhost", "::1"}:
        return ""
    return src


YANGDO_CONSULT_ENDPOINT = _sanitize_public_endpoint(YANGDO_CONSULT_ENDPOINT_RAW)
YANGDO_USAGE_ENDPOINT = _sanitize_public_endpoint(YANGDO_USAGE_ENDPOINT_RAW)
YANGDO_ESTIMATE_ENDPOINT = _sanitize_public_endpoint(YANGDO_ESTIMATE_ENDPOINT_RAW)
YANGDO_ENABLE_CONSULT_WIDGET = _cfg_bool("YANGDO_ENABLE_CONSULT_WIDGET", False)
YANGDO_ENABLE_USAGE_LOG = _cfg_bool("YANGDO_ENABLE_USAGE_LOG", False)
YANGDO_ENABLE_HOT_MATCH = _cfg_bool("YANGDO_ENABLE_HOT_MATCH", False)


STRICT_DOMAIN_GUARD = _cfg_bool("STRICT_DOMAIN_GUARD", True)
LISTING_ALLOWED_HOSTS = {"seoulmna.co.kr", "www.seoulmna.co.kr"}
BLOG_HOSTS = {"seoulmna.kr", "www.seoulmna.kr"}
NOWMNA_ALLOWED_HOSTS = {"nowmna.com", "www.nowmna.com"}


def _parse_uid_set(raw):
    out = set()
    for token in re.split(r"[,\s]+", str(raw or "").strip()):
        uid = token.strip()
        if uid and uid.isdigit():
            out.add(uid)
    return out


SCAN_PAGES = max(1, _cfg_int("SCAN_PAGES", 3))
STOP_IF_DUPLICATE_COUNT = max(1, _cfg_int("STOP_IF_DUPLICATE_COUNT", 5))
UPLOAD_ENABLED = _cfg_bool("UPLOAD_ENABLED", True)
UPLOAD_MAX_PER_RUN = max(1, _cfg_int("UPLOAD_MAX_PER_RUN", 50))
UPLOAD_DELAY_SEC = max(0.0, _cfg_float("UPLOAD_DELAY_SEC", 0.8))
UPLOAD_AUTO_CONTINUE = _cfg_bool("UPLOAD_AUTO_CONTINUE", True)
KOREAN_QUALITY_FIX = _cfg_bool("KOREAN_QUALITY_FIX", True)
SCHEMA_GUARD_ENABLED = _cfg_bool("SCHEMA_GUARD_ENABLED", True)
SCHEMA_ALERT_LOG = str(CONFIG.get("SCHEMA_ALERT_LOG", "logs/schema_alerts.log")).strip() or "logs/schema_alerts.log"
RECONCILE_AUDIT_DIR = str(CONFIG.get("RECONCILE_AUDIT_DIR", "logs/reconcile_audit")).strip() or "logs/reconcile_audit"
RECONCILE_DASHBOARD_DIR = str(CONFIG.get("RECONCILE_DASHBOARD_DIR", "logs/dashboard")).strip() or "logs/dashboard"
RECONCILE_LOCK_FILE = str(CONFIG.get("RECONCILE_LOCK_FILE", "logs/reconcile.lock")).strip() or "logs/reconcile.lock"
RECONCILE_RUN_STATE_FILE = (
    str(CONFIG.get("RECONCILE_RUN_STATE_FILE", "logs/reconcile_run_state.json")).strip()
    or "logs/reconcile_run_state.json"
)
RECONCILE_MIN_INTERVAL_SEC = max(0, _cfg_int("RECONCILE_MIN_INTERVAL_SEC", 300))
RECONCILE_LOCK_STALE_SEC = max(60, _cfg_int("RECONCILE_LOCK_STALE_SEC", 7200))
SCHEDULER_STATE_FILE = str(CONFIG.get("SCHEDULER_STATE_FILE", "scheduler_catchup_state.json")).strip() or "scheduler_catchup_state.json"
SCHEDULE_TARGET_HOUR = min(23, max(0, _cfg_int("SCHEDULE_TARGET_HOUR", 21)))
SCHEDULE_LOOKBACK_DAYS = max(1, _cfg_int("SCHEDULE_LOOKBACK_DAYS", 7))
RECONCILE_NOWMNA_MAX_PAGES = max(1, _cfg_int("RECONCILE_NOWMNA_MAX_PAGES", 300))
RECONCILE_SEOUL_MAX_PAGES = max(0, _cfg_int("RECONCILE_SEOUL_MAX_PAGES", 0))
RECONCILE_MAX_UPDATES = max(0, _cfg_int("RECONCILE_MAX_UPDATES", 0))
RECONCILE_DELAY_SEC = max(0.0, _cfg_float("RECONCILE_DELAY_SEC", 0.25))
SEOUL_DAILY_LIMIT_STATE_FILE = (
    str(CONFIG.get("SEOUL_DAILY_LIMIT_STATE_FILE", "logs/seoul_daily_limit_state.json")).strip()
    or "logs/seoul_daily_limit_state.json"
)
SEOUL_DAILY_REQUEST_CAP = max(0, _cfg_int("SEOUL_DAILY_REQUEST_CAP", 500))
SEOUL_DAILY_WRITE_CAP = max(0, _cfg_int("SEOUL_DAILY_WRITE_CAP", 80))
SEOUL_TRAFFIC_GUARD_ENABLED = _cfg_bool("SEOUL_TRAFFIC_GUARD_ENABLED", True)
SEOUL_TRAFFIC_GUARD_REQUEST_BUFFER = max(0, _cfg_int("SEOUL_TRAFFIC_GUARD_REQUEST_BUFFER", 24))
SEOUL_TRAFFIC_GUARD_WRITE_BUFFER = max(0, _cfg_int("SEOUL_TRAFFIC_GUARD_WRITE_BUFFER", 6))
SEOUL_TRAFFIC_GUARD_MIN_INTERVAL_SEC = max(0.0, _cfg_float("SEOUL_TRAFFIC_GUARD_MIN_INTERVAL_SEC", 0.35))
SEOUL_TRAFFIC_GUARD_REPORT_FILE = (
    str(CONFIG.get("SEOUL_TRAFFIC_GUARD_REPORT_FILE", "logs/seoul_co_traffic_guard_latest.json")).strip()
    or "logs/seoul_co_traffic_guard_latest.json"
)
SEOUL_TRAFFIC_GUARD_SESSION_DIR = (
    str(CONFIG.get("SEOUL_TRAFFIC_GUARD_SESSION_DIR", "logs/seoul_co_traffic_guard")).strip()
    or "logs/seoul_co_traffic_guard"
)
SEOUL_TRAFFIC_GUARD_LOCK_FILE = (
    str(CONFIG.get("SEOUL_TRAFFIC_GUARD_LOCK_FILE", "logs/seoul_co_traffic_guard.lock")).strip()
    or "logs/seoul_co_traffic_guard.lock"
)
SEOUL_TRAFFIC_GUARD_LOCK_STALE_SEC = max(300, _cfg_int("SEOUL_TRAFFIC_GUARD_LOCK_STALE_SEC", 10800))
ADMIN_MEMO_REQUIRE_BR = _cfg_bool("ADMIN_MEMO_REQUIRE_BR", True)
SHEET_ROW_JUMP_WATCHDOG_FILE = (
    str(CONFIG.get("SHEET_ROW_JUMP_WATCHDOG_FILE", "logs/sheet_row_jump_watchdog_latest.json")).strip()
    or "logs/sheet_row_jump_watchdog_latest.json"
)
SHEET_ROW_JUMP_ABORT_ON_RISK = _cfg_bool("SHEET_ROW_JUMP_ABORT_ON_RISK", True)
DEFER_QUEUE_FILE = str(CONFIG.get("DEFER_QUEUE_FILE", "logs/deferred_requeue_queue.json")).strip() or "logs/deferred_requeue_queue.json"
DEFER_REQUEST_PATTERNS = tuple(
    re.sub(r"\s+", " ", str(x or "")).strip().lower()
    for x in str(CONFIG.get("DEFER_REQUEST_PATTERNS", "")).split(",")
    if re.sub(r"\s+", " ", str(x or "")).strip()
)
LISTING_QUALITY_GATE_STRICT = _cfg_bool("LISTING_QUALITY_GATE_STRICT", True)
LISTING_QUALITY_MIN_SCORE = max(0, min(100, _cfg_int("LISTING_QUALITY_MIN_SCORE", 35)))
LOW_QUALITY_QUEUE_FILE = str(CONFIG.get("LOW_QUALITY_QUEUE_FILE", "logs/low_quality_listing_queue.json")).strip() or "logs/low_quality_listing_queue.json"
MEMO_TYPO_CHECK = _cfg_bool("MEMO_TYPO_CHECK", True)
MEMO_TYPO_FIX = _cfg_bool("MEMO_TYPO_FIX", False)
MEMO_TYPO_APPROVE_ALL = _cfg_bool("MEMO_TYPO_APPROVE_ALL", False)
MEMO_TYPO_APPROVED_UIDS = _parse_uid_set(CONFIG.get("MEMO_TYPO_APPROVED_UIDS", ""))


def _validate_domain_separation():
    site_host = _host_of(SITE_URL)
    target_host = _host_of(TARGET_URL)

    if not site_host:
        raise ValueError("[domain-guard] SITE_URL host is empty.")
    if site_host in BLOG_HOSTS:
        raise ValueError(
            "[domain-guard] SITE_URL points to seoulmna.kr(blog). "
            "all.py listing automation must target seoulmna.co.kr only."
        )
    if STRICT_DOMAIN_GUARD and site_host not in LISTING_ALLOWED_HOSTS:
        raise ValueError(
            f"[domain-guard] SITE_URL host '{site_host}' is not allowed. "
            "Use seoulmna.co.kr for listing uploads."
        )
    if site_host in NOWMNA_ALLOWED_HOSTS:
        raise ValueError(
            f"[domain-guard] SITE_URL host '{site_host}' is nowmna source domain; "
            "listing publish domain must be seoulmna.co.kr."
        )

    if target_host and target_host in LISTING_ALLOWED_HOSTS:
        raise ValueError(
            f"[domain-guard] TARGET_URL host '{target_host}' points to seoulmna.co.kr; "
            "source crawler target must be nowmna.com."
        )


def _is_allowed_nowmna_url(url):
    src = str(url or "").strip()
    if not src:
        return False
    return _host_of(src) in NOWMNA_ALLOWED_HOSTS


_validate_domain_separation()


# 윈도우 콘솔 인코딩
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ★ [핵심] 차이가 있는 이름만 골라서 변환 (웹사이트 -> 시트 기준) ★
LICENSE_MAP = {
    "가스": "가스1종",
    "실내건축": "실내",
    "상하수도": "상하",
    "철근콘크리트": "철콘",
    "철콘": "철콘",
    "금속구조": "금속",
    "금속창호": "금속",
    "지붕판금": "지붕",
    "미장방수": "습식",
    "습식방수": "습식",
    "보링그라우팅": "보링",
    "강구조": "철강구조물",
    "철도궤도": "철도",
    "구조물해체": "비계",
    "비계구조물": "비계",
    # 토공, 포장, 전기, 기계설비 등 이름이 같은 건 자동 통과
}


def normalize_license(text):
    """면허 이름을 시트 기준으로 통일"""
    clean_name = (text or "").strip()
    return LICENSE_MAP.get(clean_name, clean_name)


def clean_text_save(text):
    if not text:
        return ""
    if "양도리스트" in text:
        return ""
    return str(text).strip().replace("\t", "").replace("\r", "")


def _safe_quit(driver):
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        pass


def get_value_by_label(driver, label_list):
    for label in label_list:
        try:
            xpath = f"//td[contains(text(), '{label}')]/following-sibling::td"
            elem = driver.find_element(By.XPATH, xpath)
            return clean_text_save(elem.text)
        except Exception:
            continue
    return ""


def _normalize_nowmna_header_key(text):
    src = _compact_text(text)
    if not src:
        return ""
    key = src.replace(" ", "")
    key = key.replace("년도", "년")
    key = key.replace("시공능력평가액", "시공능력")
    key = key.replace("시평액", "시평")
    key = key.replace("시공평가", "시평")
    return key


def _build_nowmna_sales_col_map(header_cells):
    mapping = {
        "license": 0,
        "year": 1,
        "specialty": 2,
        "y20": 3,
        "y21": 4,
        "y22": 5,
        "y23": 6,
        "y24": 7,
        "y25": 8,
    }
    for idx, raw in enumerate(list(header_cells or [])):
        key = _normalize_nowmna_header_key(raw)
        if not key:
            continue
        if "업종" in key:
            mapping["license"] = idx
            continue
        if "면허년" in key:
            mapping["year"] = idx
            continue
        if any(token in key for token in ("시공능력", "시평")):
            mapping["specialty"] = idx
            continue
        m = re.search(r"(20\d{2}|\b2[0-5]\b)", key)
        if m:
            token = m.group(1)
            if token.startswith("20") and len(token) == 4:
                yy = int(token[-2:])
            else:
                yy = int(token)
            if 20 <= yy <= 25:
                mapping[f"y{yy}"] = idx
    return mapping


def _extract_nowmna_sales_rows_from_body_text(body_text):
    rows = []
    lines = [str(x or "").strip() for x in str(body_text or "").splitlines() if str(x or "").strip()]
    if not lines:
        return rows

    start_idx = -1
    for idx, line in enumerate(lines):
        if ("업종" in line and "2020" in line) or ("면허년도" in line and "2020" in line):
            start_idx = idx + 1
            break
    if start_idx < 0:
        return rows

    stop_tokens = ("재무제표", "주요체크사항", "비고", "회사개요")
    for line in lines[start_idx:]:
        if any(token in line for token in stop_tokens):
            break
        if not re.search(r"\d", line):
            continue
        if "업종" in line and "2020" in line:
            continue
        tokens = re.split(r"\s+", line)
        if len(tokens) < 2:
            continue
        split_idx = -1
        for i, tok in enumerate(tokens):
            if re.fullmatch(r"(19|20)\d{2}", tok) or re.search(r"\d", tok):
                split_idx = i
                break
        if split_idx <= 0:
            continue
        license_name = _canonical_license_name("".join(tokens[:split_idx]))
        if not license_name:
            continue
        row_year = ""
        metrics = list(tokens[split_idx:])
        if metrics and re.fullmatch(r"(19|20)\d{2}", metrics[0]):
            row_year = metrics.pop(0)
        metrics = [_compact_text(tok) for tok in metrics if _compact_text(tok)]

        y20 = y21 = y22 = y23 = y24 = y25 = specialty = ""
        if len(metrics) >= 7:
            y20 = metrics[0] if len(metrics) > 0 else ""
            y21 = metrics[1] if len(metrics) > 1 else ""
            y22 = metrics[2] if len(metrics) > 2 else ""
            y23 = metrics[3] if len(metrics) > 3 else ""
            y24 = metrics[4] if len(metrics) > 4 else ""
            y25 = metrics[-2] if len(metrics) >= 8 else (metrics[5] if len(metrics) > 5 else "")
            specialty = metrics[-1]
        elif metrics:
            # Sparse rows still carry a valid license row even when many year cells are omitted.
            if re.search(r"\d", metrics[-1]):
                specialty = metrics[-1]
        rows.append(
            {
                "license": license_name,
                "year": row_year,
                "specialty": specialty,
                "y20": y20,
                "y21": y21,
                "y22": y22,
                "y23": y23,
                "y24": y24,
                "y25": y25,
            }
        )
    return rows


def _extract_price_fragment(text):
    src = str(text or "").strip()
    if not src:
        return ""
    src = re.sub(r"<br\s*/?>", "\n", src, flags=re.I)
    src = re.sub(r"<[^>]+>", " ", src)
    src = re.sub(r"^(최종|청구|양도가|매매가|입금가)\s*[:：]?\s*", "", src)

    m = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?\s*억(?:\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*만)?", src)
    if m:
        return re.sub(r"\s+", "", m.group(0))

    m = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?\s*만", src)
    if m:
        return re.sub(r"\s+", "", m.group(0))

    m = re.search(r"[0-9][0-9,]*(?:\.[0-9]+)?", src)
    if m:
        plain = m.group(0).replace(",", "")
        if "억" in src:
            return f"{plain}억"
        compact = re.sub(r"\s+", "", src)
        if re.fullmatch(r"[0-9][0-9,]*(?:\.[0-9]+)?", compact):
            return plain
        return ""
    return ""


def extract_final_yangdo_price(raw_value):
    raw = str(raw_value or "").strip()
    if not raw or raw.lower() == "none":
        return "협의"

    parts = re.split(r"\s*(?:~|〜|∼|–|—|-|→|->|to|TO)\s*", raw)
    candidates = [x.strip() for x in parts if x.strip()] or [raw]
    for candidate in reversed(candidates):
        parsed = _extract_price_fragment(candidate)
        if parsed:
            return parsed
    return raw


def _is_numeric_price(value):
    parsed = _extract_price_fragment(extract_final_yangdo_price(value))
    return bool(parsed and re.search(r"\d", parsed))


def _is_consult_text(value):
    src = str(value or "").strip()
    if not src:
        return False
    return "협의" in src and not re.search(r"\d", src)


def _price_evidence_summary(source="", evidence=""):
    src = str(source or "").strip() or "unknown"
    txt = str(evidence or "").strip()
    if not txt:
        return "source=empty|kind=empty|present=N"
    if _is_numeric_price(txt):
        kind = "numeric"
    elif _is_consult_text(txt):
        kind = "consult"
    elif re.search(r"\d", txt):
        kind = "mixed"
    else:
        kind = "text"
    return _truncate(f"source={src}|kind={kind}|present=Y", 160)


def _trace_payload(price, source, confidence, fallback_used, evidence):
    return {
        "price": str(price or "").strip() or "협의",
        "source": str(source or "").strip() or "unknown",
        "confidence": str(confidence or "").strip() or "low",
        "fallback_used": "Y" if str(fallback_used).upper() in {"Y", "TRUE", "1"} else "N",
        "evidence": _price_evidence_summary(source, evidence),
    }


def resolve_yangdo_price_trace(primary_price="", claim_price="", memo_text=""):
    primary = str(primary_price or "").strip()
    claim = str(claim_price or "").strip()
    memo = str(memo_text or "").strip()

    if _is_numeric_price(primary):
        return _trace_payload(
            price=extract_final_yangdo_price(primary),
            source="primary",
            confidence="high",
            fallback_used="N",
            evidence=primary,
        )

    if _is_numeric_price(claim):
        return _trace_payload(
            price=extract_final_yangdo_price(claim),
            source="claim",
            confidence="high",
            fallback_used="Y",
            evidence=claim,
        )

    if any(token in memo for token in ("청구", "범위", "양도가", "매매가", "최종")) and _is_numeric_price(memo):
        return _trace_payload(
            price=extract_final_yangdo_price(memo),
            source="memo",
            confidence="medium",
            fallback_used="Y",
            evidence=memo,
        )

    if _is_consult_text(primary) or _is_consult_text(claim):
        source = "primary_consult" if _is_consult_text(primary) else "claim_consult"
        evidence = primary if _is_consult_text(primary) else claim
        return _trace_payload(
            price="협의",
            source=source,
            confidence="low",
            fallback_used="Y" if source == "claim_consult" else "N",
            evidence=evidence,
        )

    if primary:
        return _trace_payload(
            price=primary,
            source="primary_text",
            confidence="low",
            fallback_used="N",
            evidence=primary,
        )

    if claim:
        return _trace_payload(
            price=claim,
            source="claim_text",
            confidence="low",
            fallback_used="Y",
            evidence=claim,
        )

    return _trace_payload(
        price="협의",
        source="empty",
        confidence="low",
        fallback_used="Y",
        evidence="",
    )


def resolve_yangdo_price(primary_price="", claim_price="", memo_text=""):
    return resolve_yangdo_price_trace(primary_price, claim_price, memo_text)["price"]


def _build_price_trace_summary(price_trace, primary_price="", claim_price=""):
    trace = dict(price_trace or {})
    normalized = str(trace.get("price") or "").strip() or "협의"
    source = str(trace.get("source") or "unknown").strip() or "unknown"
    confidence = str(trace.get("confidence") or "low").strip() or "low"
    fallback = "Y" if str(trace.get("fallback_used") or "").strip().upper() in {"Y", "TRUE", "1"} else "N"
    primary_present = "Y" if _compact_text(primary_price) else "N"
    claim_present = "Y" if _compact_text(claim_price) else "N"
    summary = (
        f"정규가={normalized} | source={source} | confidence={confidence} "
        f"| fallback={fallback} | primary={primary_present} | claim={claim_present}"
    )
    return _truncate(summary, 160)


PRICE_TRACE_HEADERS = [
    "가격비식별요약",
    "가격추출소스",
    "가격추출근거요약",
    "가격신뢰도",
    "가격fallback",
]

# Core listing columns
# - AJ(index 35): 신용 별표 표시
# - AK(index 36): 신용 주체(별도 관리)
# - AL~AP(index 37~41): 가격 추적 컬럼
CREDIT_DISPLAY_COL_IDX = 35
CREDIT_SUBJECT_COL_IDX = 36
TRACE_START_COL_IDX = 37
TRACE_COL_COUNT = 5

# 특정 UID는 신용 주체명을 고정한다. (수기 운영 정책 반영)
CREDIT_SUBJECT_UID_OVERRIDES = {
    "11537": "서울건설정보",
    "11538": "서울건설정보",
}


def _col_to_a1(col_1based):
    n = int(col_1based)
    if n <= 0:
        raise ValueError("column index must be positive")
    out = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out.append(chr(ord("A") + rem))
    return "".join(reversed(out))


def _row_text(row, idx):
    if idx < 0 or idx >= len(row):
        return ""
    return str(row[idx]).strip()


def _sheet_no_to_int(value):
    src = str(value or "").strip().replace(",", "")
    if not src:
        return 0
    if re.fullmatch(r"\d+", src):
        return int(src)
    if re.fullmatch(r"\d+\.0+", src):
        try:
            return int(float(src))
        except Exception:
            return 0
    return 0


def _normalize_sheet_row_no_override(value):
    if value is None:
        return None
    if str(value or "").strip().upper() == "__CLEAR__":
        return "__CLEAR__"
    num = _sheet_no_to_int(value)
    if num > 0:
        return num
    return ""


def _resolve_sheet_row_no(old_no="", row_no_override=None, fallback_no=0, allocate_if_missing=False):
    override = _normalize_sheet_row_no_override(row_no_override)
    old_num = _sheet_no_to_int(old_no)
    old_txt = str(old_no or "").strip()
    if override == "__CLEAR__":
        return ""
    if override is None:
        if old_num > 0:
            return old_num
        if old_txt:
            return old_txt
        if allocate_if_missing and int(fallback_no or 0) > 0:
            return int(fallback_no)
        return ""
    if override != "":
        return override
    if old_num > 0:
        return old_num
    if old_txt:
        return old_txt
    return ""


def _extract_sheet_uid_from_row(row):
    for idx in (34, 33, 32):
        cand = extract_id_strict(_row_text(row, idx))
        if cand:
            return cand
    return ""


def _is_listing_anchor_row(row):
    # A sparse row with only trace columns(AL~AP) should not move append anchor.
    if _sheet_no_to_int(_row_text(row, 0)) > 0:
        return True
    if _extract_sheet_uid_from_row(row):
        return True
    for idx in (2, 3, 4, 13, 14, 15, 16, 20, 31):
        if _row_text(row, idx):
            return True
    return False


def _has_listing_core_cells(row):
    # Legacy trace-only rows may still populate AK(index 36)=신용주체.
    # Treat core listing columns as A~AJ and exclude AK/AL~AP trace metadata.
    max_idx = min(len(row), CREDIT_SUBJECT_COL_IDX)
    for idx in range(max_idx):
        if _row_text(row, idx):
            return True
    return False


def _ensure_price_trace_headers(worksheet, all_values):
    row1 = all_values[0] if all_values else []
    subject_col = CREDIT_SUBJECT_COL_IDX + 1  # AK
    start_col = TRACE_START_COL_IDX + 1  # AL
    expected = list(PRICE_TRACE_HEADERS)

    current_subject = str(row1[subject_col - 1]).strip() if (subject_col - 1) < len(row1) else ""
    need_subject_update = current_subject != "신용주체"
    need_trace_update = False
    for offset, header in enumerate(expected):
        idx = (start_col - 1) + offset
        current = str(row1[idx]).strip() if idx < len(row1) else ""
        if current != header:
            need_trace_update = True
            break

    if not need_subject_update and not need_trace_update:
        return

    if need_subject_update:
        subject_a1 = _col_to_a1(subject_col) + "1"
        try:
            worksheet.update(range_name=subject_a1, values=[["신용주체"]])
        except TypeError:
            worksheet.update(subject_a1, [["신용주체"]])
        print(f"   🧭 신용 주체 헤더 설정: {subject_a1}")

    if need_trace_update:
        start_a1 = _col_to_a1(start_col)
        end_a1 = _col_to_a1(start_col + len(expected) - 1)
        range_name = f"{start_a1}1:{end_a1}1"
        try:
            worksheet.update(range_name=range_name, values=[expected])
        except TypeError:
            worksheet.update(range_name, [expected])
        print(f"   🧭 가격 추적 헤더 설정: {range_name}")


def _build_price_trace_updates(all_values):
    if len(all_values) <= 1:
        return {
            "price_values": [],
            "trace_values": [],
            "total_rows": 0,
            "changed_rows": 0,
            "recovered_rows": 0,
            "changed_examples": [],
        }

    price_values = []
    trace_values = []
    changed_rows = 0
    recovered_rows = 0
    changed_examples = []

    def _looks_like_trace_source(text):
        src = str(text or "").strip().lower()
        if not src:
            return False
        keywords = ("primary", "claim", "memo", "consult", "empty", "fallback")
        return any(k in src for k in keywords)

    def _looks_like_trace_confidence(text):
        src = str(text or "").strip().lower()
        return src in {"high", "medium", "low"}

    def _looks_like_trace_fallback(text):
        src = str(text or "").strip().upper()
        return src in {"Y", "N"}

    def _looks_like_trace_raw(text):
        src = str(text or "").strip()
        if not src:
            return False
        if "협의" in src:
            return True
        return bool(re.search(r"\d", src))

    def _trace_layout_score(trace_values):
        vals = list(trace_values or [])
        while len(vals) < TRACE_COL_COUNT:
            vals.append("")
        score = 0
        if _looks_like_trace_raw(vals[0]):
            score += 1
        if _looks_like_trace_source(vals[1]):
            score += 2
        if _compact_text(vals[2]):
            score += 1
        if _looks_like_trace_confidence(vals[3]):
            score += 2
        if _looks_like_trace_fallback(vals[4]):
            score += 1
        return score

    def _read_existing_trace_cols(row):
        new_vals = [
            _row_text(row, TRACE_START_COL_IDX + 0),
            _row_text(row, TRACE_START_COL_IDX + 1),
            _row_text(row, TRACE_START_COL_IDX + 2),
            _row_text(row, TRACE_START_COL_IDX + 3),
            _row_text(row, TRACE_START_COL_IDX + 4),
        ]
        legacy_vals = [
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 0),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 1),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 2),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 3),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 4),
        ]
        new_score = _trace_layout_score(new_vals)
        legacy_score = _trace_layout_score(legacy_vals)
        if legacy_score > new_score:
            return legacy_vals
        return new_vals

    def _trace_first_col_is_summary(text):
        src = str(text or "").strip()
        return src.startswith("정규가=") and "source=" in src and "confidence=" in src

    def _trace_semantically_matches(old_trace, new_price, new_trace):
        vals = list(old_trace or [])
        while len(vals) < TRACE_COL_COUNT:
            vals.append("")
        if vals[1] != new_trace[1] or vals[3] != new_trace[3] or vals[4] != new_trace[4]:
            return False
        if _compact_text(extract_final_yangdo_price(vals[0])) != _compact_text(extract_final_yangdo_price(new_price)):
            return False
        if _trace_first_col_is_summary(vals[0]):
            return vals == new_trace
        # Legacy raw trace layout is acceptable if semantic fields already match.
        return True

    for row_idx, row in enumerate(all_values[1:], start=2):
        if not _has_listing_core_cells(row):
            primary = _row_text(row, 18)
            old_trace = _read_existing_trace_cols(row)
            price_values.append([primary])
            trace_values.append(old_trace)
            continue

        primary = _row_text(row, 18)   # C19
        claim = _row_text(row, 33)     # C34
        memo = _row_text(row, 31)      # C32

        trace = resolve_yangdo_price_trace(primary, claim, memo)
        new_price = trace["price"]
        new_trace = [
            _build_price_trace_summary(trace, primary, claim),
            trace["source"],
            trace["evidence"],
            trace["confidence"],
            trace["fallback_used"],
        ]

        old_trace = _read_existing_trace_cols(row)
        effective_trace = old_trace if _trace_semantically_matches(old_trace, new_price, new_trace) else new_trace

        if primary != new_price or old_trace != effective_trace:
            changed_rows += 1
            if len(changed_examples) < 20:
                changed_examples.append(
                    {
                        "row": row_idx,
                        "old_price": primary,
                        "new_price": new_price,
                        "source": trace["source"],
                        "confidence": trace["confidence"],
                        "fallback": trace["fallback_used"],
                    }
                )

        if (not primary or primary == "협의") and _is_numeric_price(new_price):
            recovered_rows += 1

        price_values.append([new_price])
        trace_values.append(effective_trace)

    return {
        "price_values": price_values,
        "trace_values": trace_values,
        "total_rows": len(all_values) - 1,
        "changed_rows": changed_rows,
        "recovered_rows": recovered_rows,
        "changed_examples": changed_examples,
    }


def _to_int_safe(value):
    try:
        return int(str(value).strip())
    except Exception:
        return 0


def _to_float_safe(value):
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def _price_gap_score(primary, claim):
    p = _to_float_safe(_to_eok_text(primary))
    c = _to_float_safe(_to_eok_text(claim))
    if p <= 0 or c <= 0:
        return 0
    gap = abs(p - c)
    if gap >= 1.0:
        return 25
    if gap >= 0.5:
        return 15
    if gap >= 0.2:
        return 8
    return 0


def _low_conf_risk_bundle(source, fallback, primary="", claim="", memo=""):
    src = str(source or "").strip().lower()
    fb = str(fallback or "").strip().upper()
    score = 0
    reasons = []

    if src == "primary_consult":
        score += 55
        reasons.append("양도가 협의표기")
    if src in {"claim_consult", "empty", "primary_text", "claim_text"}:
        score += 30
        reasons.append(f"추출소스:{src}")
    if fb == "Y":
        score += 18
        reasons.append("fallback사용")

    gap_score = _price_gap_score(primary, claim)
    if gap_score > 0:
        score += gap_score
        reasons.append("양도가/청구가 차이")

    memo_txt = str(memo or "")
    if "협의" in memo_txt and claim and re.search(r"\d", claim):
        score += 12
        reasons.append("비고협의+청구숫자혼재")

    if score >= 55:
        priority = "P1"
    elif score >= 30:
        priority = "P2"
    else:
        priority = "P3"
    return priority, score, ", ".join(reasons[:4])


def _priority_from_low_row(source, fallback, primary="", claim="", memo=""):
    return _low_conf_risk_bundle(source, fallback, primary, claim, memo)[0]


LOW_CONF_PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3}
LOW_CONF_MANUAL_HEADERS = ["검수완료", "검수메모", "검수수정양도가", "검수시각"]


def _low_conf_priority_rank(priority):
    return LOW_CONF_PRIORITY_ORDER.get(str(priority or "").strip().upper(), 99)


def _low_conf_sort_key(row):
    return (
        _low_conf_priority_rank(row.get("검수우선순위", "")),
        -_to_int_safe(row.get("리스크점수", 0)),
        -_to_int_safe(row.get("번호", "")),
        -_to_int_safe(row.get("row", "")),
    )


def _sort_low_confidence_rows(rows):
    return sorted(rows, key=_low_conf_sort_key)


def _is_low_conf_review_done(value):
    v = str(value or "").strip().lower()
    return v in {"y", "yes", "1", "true", "done", "ok", "완료", "검수완료"}


def _exclude_reviewed_low_confidence_rows(rows):
    kept = []
    skipped = 0
    for row in rows:
        if _is_low_conf_review_done(row.get("검수완료", "")):
            skipped += 1
            continue
        kept.append(row)
    return kept, skipped


def _autofill_reviewed_timestamp(rows, now_text=None):
    ts = str(now_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    filled = 0
    for row in rows:
        if not _is_low_conf_review_done(row.get("검수완료", "")):
            continue
        if str(row.get("검수시각", "")).strip():
            continue
        row["검수시각"] = ts
        filled += 1
    return rows, filled


def _merge_manual_cell_value(col, old_value, new_value, old_review_done, new_review_done):
    ov = str(old_value or "").strip()
    nv = str(new_value or "").strip()

    if col == "검수시각":
        if ov and nv:
            return max(ov, nv)
        return old_value if ov else new_value

    if col == "검수완료":
        if old_review_done and not new_review_done:
            return old_value
        if new_review_done and not old_review_done:
            return new_value
        return old_value if ov else new_value

    if old_review_done and not new_review_done:
        return old_value if ov else new_value
    if new_review_done and not old_review_done:
        return new_value if nv else old_value
    return old_value if ov else new_value


def _merge_manual_data(old_data, new_data, available_manual_cols):
    old_done = _is_low_conf_review_done(old_data.get("검수완료", ""))
    new_done = _is_low_conf_review_done(new_data.get("검수완료", ""))
    merged = {}
    for col in available_manual_cols:
        merged[col] = _merge_manual_cell_value(
            col,
            old_data.get(col, ""),
            new_data.get(col, ""),
            old_done,
            new_done,
        )
    return merged


def _low_conf_row_keys(row):
    keys = []
    seq = str(row.get("번호", "")).strip()
    if seq:
        keys.append(f"번호:{seq}")
    row_no = str(row.get("row", "")).strip()
    if row_no:
        keys.append(f"row:{row_no}")
    return keys


def _merge_low_confidence_manual_fields(rows, existing_values):
    merged_rows = [dict(row) for row in rows]
    for row in merged_rows:
        for col in LOW_CONF_MANUAL_HEADERS:
            row.setdefault(col, "")

    if not merged_rows or not existing_values:
        return merged_rows

    header = [str(x).strip() for x in (existing_values[0] if existing_values else [])]
    if not header:
        return merged_rows

    idx_map = {name: idx for idx, name in enumerate(header)}
    available_manual_cols = [col for col in LOW_CONF_MANUAL_HEADERS if col in idx_map]
    if not available_manual_cols:
        return merged_rows

    preserved_by_key = {}
    for raw in existing_values[1:]:
        row_dict = {}
        for name, idx in idx_map.items():
            row_dict[name] = _row_text(raw, idx)

        manual_data = {col: row_dict.get(col, "") for col in available_manual_cols}
        if not any(str(v).strip() for v in manual_data.values()):
            continue

        for key in _low_conf_row_keys(row_dict):
            if key in preserved_by_key:
                preserved_by_key[key] = _merge_manual_data(
                    preserved_by_key[key], manual_data, available_manual_cols
                )
            else:
                preserved_by_key[key] = manual_data

    for row in merged_rows:
        matched = None
        for key in _low_conf_row_keys(row):
            if key in preserved_by_key:
                matched = preserved_by_key[key]
                break
        if not matched:
            continue

        for col in available_manual_cols:
            if not str(row.get(col, "")).strip():
                row[col] = matched.get(col, "")

    return merged_rows


def _finalize_low_confidence_rows(rows, existing_values=None, limit=0, skip_reviewed=False):
    finalized = _sort_low_confidence_rows(rows)
    finalized = _merge_low_confidence_manual_fields(finalized, existing_values or [])

    skipped_reviewed = 0
    if skip_reviewed:
        finalized, skipped_reviewed = _exclude_reviewed_low_confidence_rows(finalized)

    limited_out = 0
    limit = max(0, _to_int_safe(limit))
    if limit > 0 and len(finalized) > limit:
        limited_out = len(finalized) - limit
        finalized = finalized[:limit]

    preserved_count = sum(
        1
        for row in finalized
        if any(str(row.get(col, "")).strip() for col in LOW_CONF_MANUAL_HEADERS)
    )

    return finalized, {
        "skipped_reviewed": skipped_reviewed,
        "limited_out": limited_out,
        "preserved_count": preserved_count,
    }


def _collect_low_confidence_rows(all_values, limit=0, recent_rows=0, recent_numbers=0):
    rows = []
    if len(all_values) <= 1:
        return rows

    def _looks_like_trace_source(text):
        src = str(text or "").strip().lower()
        if not src:
            return False
        keywords = ("primary", "claim", "memo", "consult", "empty", "fallback")
        return any(k in src for k in keywords)

    def _looks_like_trace_confidence(text):
        return str(text or "").strip().lower() in {"high", "medium", "low"}

    def _looks_like_trace_fallback(text):
        return str(text or "").strip().upper() in {"Y", "N"}

    def _looks_like_trace_raw(text):
        src = str(text or "").strip()
        if not src:
            return False
        if "협의" in src:
            return True
        return bool(re.search(r"\d", src))

    def _trace_layout_score(trace_values):
        vals = list(trace_values or [])
        while len(vals) < TRACE_COL_COUNT:
            vals.append("")
        score = 0
        if _looks_like_trace_raw(vals[0]):
            score += 1
        if _looks_like_trace_source(vals[1]):
            score += 2
        if _compact_text(vals[2]):
            score += 1
        if _looks_like_trace_confidence(vals[3]):
            score += 2
        if _looks_like_trace_fallback(vals[4]):
            score += 1
        return score

    min_row_idx = 2
    recent_rows = max(0, _to_int_safe(recent_rows))
    if recent_rows > 0:
        min_row_idx = max(2, len(all_values) - recent_rows + 1)

    top_seq_set = set()
    recent_numbers = max(0, _to_int_safe(recent_numbers))
    if recent_numbers > 0:
        seq_nums = []
        for row in all_values[1:]:
            seq = _row_text(row, 0)
            if not seq or not str(seq).strip().isdigit():
                continue
            seq_nums.append(int(seq))
        seq_nums = sorted(set(seq_nums), reverse=True)
        top_seq_set = set(seq_nums[:recent_numbers])

    for row_idx, row in enumerate(all_values[1:], start=2):
        if row_idx < min_row_idx:
            continue

        primary = _row_text(row, 18)   # C19
        claim = _row_text(row, 33)     # C34
        memo = _row_text(row, 31)      # C32
        seq = _row_text(row, 0)        # C1

        if top_seq_set:
            if not seq.isdigit() or int(seq) not in top_seq_set:
                continue

        new_trace = [
            _row_text(row, TRACE_START_COL_IDX + 0),
            _row_text(row, TRACE_START_COL_IDX + 1),
            _row_text(row, TRACE_START_COL_IDX + 2),
            _row_text(row, TRACE_START_COL_IDX + 3),
            _row_text(row, TRACE_START_COL_IDX + 4),
        ]
        legacy_trace = [
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 0),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 1),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 2),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 3),
            _row_text(row, CREDIT_SUBJECT_COL_IDX + 4),
        ]

        if _trace_layout_score(legacy_trace) > _trace_layout_score(new_trace):
            raw, source, evidence, confidence, fallback = legacy_trace
        else:
            raw, source, evidence, confidence, fallback = new_trace

        if not _looks_like_trace_confidence(confidence):
            trace = resolve_yangdo_price_trace(raw or primary, claim, memo)
            raw = raw or primary
            if not _looks_like_trace_source(source):
                source = trace["source"]
            evidence = evidence or trace["evidence"]
            confidence = trace["confidence"]
            if not _looks_like_trace_fallback(fallback):
                fallback = trace["fallback_used"]

        if str(confidence).strip().lower() != "low":
            continue

        priority, risk_score, risk_reason = _low_conf_risk_bundle(
            source=source,
            fallback=fallback,
            primary=primary,
            claim=claim,
            memo=memo,
        )

        rows.append(
            {
                "row": row_idx,
                "검수우선순위": priority,
                "리스크점수": risk_score,
                "리스크사유": risk_reason,
                "번호": seq,
                "양도가": primary,
                "가격비식별요약": _build_price_trace_summary(
                    resolve_yangdo_price_trace(raw or primary, claim, memo),
                    raw or primary,
                    claim,
                ),
                "가격추출소스": source,
                "가격추출근거요약": evidence,
                "가격신뢰도": confidence,
                "가격fallback": fallback,
                "청구양도가": claim,
                "비고": _truncate(memo, 200),
            }
        )

    if limit > 0:
        rows = _sort_low_confidence_rows(rows)[: max(0, _to_int_safe(limit))]

    return rows


LOW_CONF_SHEET_HEADERS = [
    "생성시각",
    "검수우선순위",
    "row",
    "번호",
    "양도가",
    "가격비식별요약",
    "가격추출소스",
    "가격추출근거요약",
    "가격신뢰도",
    "가격fallback",
    "청구양도가",
    "비고",
    *LOW_CONF_MANUAL_HEADERS,
    "리스크점수",
    "리스크사유",
]


def _build_low_confidence_sheet_values(rows, generated_at=None):
    ts = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values = [list(LOW_CONF_SHEET_HEADERS)]
    for row in rows:
        values.append(
            [
                ts,
                row.get("검수우선순위", ""),
                row.get("row", ""),
                row.get("번호", ""),
                row.get("양도가", ""),
                row.get("가격비식별요약", ""),
                row.get("가격추출소스", ""),
                row.get("가격추출근거요약", ""),
                row.get("가격신뢰도", ""),
                row.get("가격fallback", ""),
                row.get("청구양도가", ""),
                row.get("비고", ""),
                row.get("검수완료", ""),
                row.get("검수메모", ""),
                row.get("검수수정양도가", ""),
                row.get("검수시각", ""),
                row.get("리스크점수", ""),
                row.get("리스크사유", ""),
            ]
        )
    return values


YANGDO_ESTIMATE_SHEET_HEADERS = [
    "생성시각",
    "row",
    "번호",
    "UID",
    "업종",
    "현재양도가",
    "청구양도가",
    "추정중앙값(억)",
    "추정하한(억)",
    "추정상한(억)",
    "권장범위",
    "신뢰도",
    "신뢰점수",
    "근거건수",
    "평균유사도",
    "근거UID(상위5)",
    "판정",
    "청구-추정차(억)",
    "현재-추정차(억)",
]


def _sheet_num_or_none(raw):
    src = str(raw or "").strip().replace(",", "")
    if not src or src in {"-", "--", "협의", "미대출", "미가입", "신규"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", src)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _sheet_balance_to_eok(raw):
    src = _compact_text(raw)
    if not src:
        return None
    if "억" in src or "만" in src:
        return _sheet_num_or_none(_to_eok_text(src))
    num = _sheet_num_or_none(src)
    if num is None:
        return None
    return _round4(float(num) / 10000.0)


def _price_to_eok_float(raw):
    src = str(raw or "").strip()
    if not src or "협의" in src and not re.search(r"\d", src):
        return None
    has_unit = bool(re.search(r"[억만]", src))
    parsed = extract_final_yangdo_price(src)
    eok_text = _to_eok_text(parsed)
    val = _to_float_safe(eok_text)
    if val <= 0:
        return None
    # Guard against row/UID-like raw integers accidentally parsed as price.
    if not has_unit and float(val) >= 200:
        return None
    return float(val)


def _fmt_eok_value(value):
    if value is None:
        return ""
    try:
        num = float(value)
    except Exception:
        return ""
    if abs(num - round(num)) < 1e-9:
        return f"{int(round(num))}억"
    return f"{num:.2f}".rstrip("0").rstrip(".") + "억"


def _license_token_set_for_estimate(raw):
    out = set()
    for line in str(raw or "").replace("<br>", "\n").replace("<br/>", "\n").splitlines():
        for token in re.split(r"[/,|·ㆍ+&\s]+", str(line or "").strip()):
            clean = str(token or "").strip()
            if not clean:
                continue
            canonical = _canonical_license_name(clean) or normalize_license(clean)
            key = _normalize_license_key(canonical)
            if key and len(key) >= 2 and key not in _GENERIC_LICENSE_KEYS:
                out.add(key)
    return out


def _safe_sales_sums(rec):
    y = rec.get("years", {})
    latest3 = [y.get("y23"), y.get("y24"), y.get("y25")]
    latest5 = [y.get("y21"), y.get("y22"), y.get("y23"), y.get("y24"), y.get("y25")]
    sum3 = sum(v for v in latest3 if isinstance(v, (int, float)))
    sum5 = sum(v for v in latest5 if isinstance(v, (int, float)))
    has3 = any(isinstance(v, (int, float)) for v in latest3)
    has5 = any(isinstance(v, (int, float)) for v in latest5)
    return (sum3 if has3 else None), (sum5 if has5 else None)


def _sheet_row_to_estimate_record(row, row_idx):
    src = list(row or [])
    uid = _extract_sheet_uid_from_row(src) or ""
    number = _sheet_no_to_int(_row_text(src, 0))
    license_text = _row_text(src, 2)
    years = {
        "y20": _sheet_num_or_none(_row_text(src, 5)),
        "y21": _sheet_num_or_none(_row_text(src, 6)),
        "y22": _sheet_num_or_none(_row_text(src, 7)),
        "y23": _sheet_num_or_none(_row_text(src, 8)),
        "y24": _sheet_num_or_none(_row_text(src, 9)),
        "y25": _sheet_num_or_none(_row_text(src, 12)),
    }
    rec = {
        "row": int(row_idx),
        "number": int(number) if number > 0 else 0,
        "uid": str(uid),
        "license_text": license_text,
        "license_tokens": _license_token_set_for_estimate(license_text),
        "license_year": _sheet_num_or_none(_row_text(src, 3)),
        "specialty": _sheet_num_or_none(_row_text(src, 4)),
        "years": years,
        "location": _compact_text(_row_text(src, 16)),
        "company_type": _compact_text(_row_text(src, 15)),
        "association": _compact_text(_row_text(src, 20)),
        "shares": _sheet_num_or_none(_row_text(src, 14)),
        "balance_eok": _sheet_balance_to_eok(_row_text(src, 17)),
        "debt_ratio": _sheet_num_or_none(_row_text(src, 21)),
        "liq_ratio": _sheet_num_or_none(_row_text(src, 23)),
        "surplus_eok": _sheet_num_or_none(_to_eok_text(_row_text(src, 30))),
        "capital_eok": _sheet_num_or_none(_to_eok_text(_row_text(src, 19))),
        "current_price_text": _row_text(src, 18),
        "claim_price_text": _row_text(src, 33),
        "current_price_eok": _price_to_eok_float(_row_text(src, 18)),
        "claim_price_eok": _price_to_eok_float(_row_text(src, 33)),
    }
    if not (isinstance(rec.get("license_year"), (int, float)) and 1900 <= float(rec.get("license_year")) <= 2099):
        rec["license_year"] = None
    if rec.get("current_price_eok") is not None and rec.get("uid"):
        uid_num = _to_float_safe(rec.get("uid"))
        if uid_num > 0 and abs(float(rec["current_price_eok"]) - float(uid_num)) < 1e-9:
            rec["current_price_eok"] = None
    if rec.get("claim_price_eok") is not None and rec.get("uid"):
        uid_num = _to_float_safe(rec.get("uid"))
        if uid_num > 0 and abs(float(rec["claim_price_eok"]) - float(uid_num)) < 1e-9:
            rec["claim_price_eok"] = None
    sum3, sum5 = _safe_sales_sums(rec)
    rec["sales3_eok"] = sum3
    rec["sales5_eok"] = sum5
    return rec


def _build_estimate_records(all_values):
    records = []
    for row_idx, row in enumerate(list(all_values or [])[1:], start=2):
        if not _has_listing_core_cells(row):
            continue
        rec = _sheet_row_to_estimate_record(row, row_idx)
        if not rec.get("uid") and rec.get("number", 0) <= 0:
            continue
        records.append(rec)
    return records


def _jaccard_similarity(left, right):
    a = set(left or set())
    b = set(right or set())
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union <= 0:
        return 0.0
    return inter / union


def _relative_closeness(left, right):
    if left is None or right is None:
        return 0.35
    denom = max(abs(float(left)), abs(float(right)), 1.0)
    rel = abs(float(left) - float(right)) / denom
    return max(0.0, 1.0 - min(rel, 1.0))


def _safe_ratio(num_value, den_value):
    num = _to_float_safe(num_value)
    den = _to_float_safe(den_value)
    if num <= 0 or den <= 0:
        return None
    val = num / den
    if val <= 0:
        return None
    return float(val)


_CORE_LICENSE_TOKENS = {
    "전기", "정보통신", "소방", "기계설비", "가스",
    "토건", "토목", "건축", "조경", "실내",
    "토공", "포장", "철콘", "상하", "석공", "비계", "석면", "습식", "도장",
    "조경식재", "조경시설", "산림토목", "도시정비", "보링", "수중", "금속",
}
_CORE_LICENSE_TOKENS_SORTED = sorted(_CORE_LICENSE_TOKENS, key=len, reverse=True)
_CORE_TEXT_ALIAS_MAP = {
    "실내건축": "실내",
    "철근콘크리트": "철콘",
    "상하수도설비": "상하",
    "토목건축": "토건",
    "정보통신공사업": "정보통신",
    "통신공사업": "정보통신",
    "통신": "정보통신",
    "기계설비공사업": "기계설비",
    "기계가스설비공사업": "기계설비",
    "기계가스": "기계설비",
    "기계": "기계설비",
    "금속구조물창호온실": "금속",
    "비계구조물해체": "비계",
    "석면해체제거": "석면",
    "습식방수석공": "습식",
    "소방시설": "소방",
    "전기공사업": "전기",
    "소방공사업": "소방",
}


def _core_tokens_from_text(raw):
    key = _normalize_license_key(raw)
    if not key:
        return set()
    alias = _CORE_TEXT_ALIAS_MAP.get(key)
    if alias:
        return {alias}
    hits = set()
    for token in _CORE_LICENSE_TOKENS_SORTED:
        if token and token in key:
            hits.add(token)
    return hits


def _core_license_tokens(tokens):
    out = set()
    for raw in set(tokens or set()):
        token = str(raw or "").strip()
        if not token:
            continue
        if token in _CORE_LICENSE_TOKENS:
            out.add(token)
        out.update(_core_tokens_from_text(token))
    return out


def _is_single_token_cross_combo(target_tokens, candidate_tokens, candidate_license_text=""):
    tset = set(target_tokens or set())
    cset = set(candidate_tokens or set())
    target = _single_token_target_core(tset)
    if not target:
        return False
    cand_core = _core_license_tokens(cset) | _core_tokens_from_text(candidate_license_text)
    if target not in cset and target not in cand_core:
        return False
    if len(cand_core) <= 1:
        return False
    return any(tok != target for tok in cand_core)


def _single_token_target_core(target_tokens):
    tset = set(target_tokens or set())
    core = _core_license_tokens(tset)
    if len(core) == 1:
        return next(iter(sorted(core)))
    if len(tset) == 1:
        return next(iter(tset))
    return ""


def _is_single_token_same_core(target_tokens, candidate_tokens, candidate_license_text=""):
    target = _single_token_target_core(target_tokens)
    if not target:
        return False
    cset = set(candidate_tokens or set())
    cand_core = _core_license_tokens(cset) | _core_tokens_from_text(candidate_license_text)
    if len(cand_core) >= 2:
        return False
    if len(cand_core) == 1:
        return target in cand_core
    if len(cset) == 1:
        tok = next(iter(cset))
        return (target in tok) or (tok in target)
    return False


def _is_single_token_profile_outlier(target, candidate):
    tset = set(target.get("license_tokens", set()) or set())
    if not _single_token_target_core(tset):
        return False
    spec_ratio = _safe_ratio(target.get("specialty"), candidate.get("specialty"))
    sales_ratio = _safe_ratio(target.get("sales3_eok"), candidate.get("sales3_eok"))
    if spec_ratio is not None and (spec_ratio < 0.30 or spec_ratio > 3.30):
        return True
    if sales_ratio is not None and (sales_ratio < 0.30 or sales_ratio > 3.30):
        return True
    return False


def _neighbor_similarity_score(target, candidate):
    tokens_t = set(target.get("license_tokens", set()) or set())
    tokens_c = set(candidate.get("license_tokens", set()) or set())
    inter = tokens_t & tokens_c
    token_precision = (len(inter) / float(max(1, len(tokens_c)))) if tokens_c else 0.0
    single_core_target = bool(_single_token_target_core(tokens_t))
    score = 0.0

    lic_j = _jaccard_similarity(tokens_t, tokens_c)
    score += lic_j * 55.0
    score += min(15.0, 4.0 * len(inter))

    score += _relative_closeness(target.get("specialty"), candidate.get("specialty")) * 10.0
    score += _relative_closeness(target.get("sales3_eok"), candidate.get("sales3_eok")) * 8.0
    score += _relative_closeness(target.get("sales5_eok"), candidate.get("sales5_eok")) * 6.0
    score += _relative_closeness(target.get("license_year"), candidate.get("license_year")) * 3.0
    score += _relative_closeness(target.get("debt_ratio"), candidate.get("debt_ratio")) * 3.0
    score += _relative_closeness(target.get("liq_ratio"), candidate.get("liq_ratio")) * 3.0

    if _compact_text(target.get("location")) and _compact_text(target.get("location")) == _compact_text(candidate.get("location")):
        score += 2.0
    if _compact_text(target.get("association")) and _compact_text(target.get("association")) == _compact_text(candidate.get("association")):
        score += 2.0

    # 업종이 완전히 다르면 과도한 매칭 방지
    if tokens_t and tokens_c and not inter:
        score *= 0.55
    if _is_single_token_cross_combo(tokens_t, tokens_c, candidate.get("license_text")):
        # 단일 업종 입력 시 타 핵심업종이 섞인 복합면허를 하드 감점
        score *= 0.10
    if tokens_t and tokens_c and single_core_target and len(tokens_c) >= 2 and (tokens_t & tokens_c):
        # 단일 업종 검색에서 복합면허 과대매칭 억제
        score *= 0.62
        if token_precision < 0.60:
            score *= 0.72
        spec_ratio = None
        sales_ratio = None
        try:
            a = target.get("specialty")
            b = candidate.get("specialty")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and float(b) != 0:
                spec_ratio = float(a) / float(b)
        except Exception:
            spec_ratio = None
        try:
            a = target.get("sales3_eok")
            b = candidate.get("sales3_eok")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and float(b) != 0:
                sales_ratio = float(a) / float(b)
        except Exception:
            sales_ratio = None
        if (
            (spec_ratio is not None and (spec_ratio < 0.35 or spec_ratio > 2.85))
            or (sales_ratio is not None and (sales_ratio < 0.35 or sales_ratio > 2.85))
        ):
            score *= 0.72

    return max(0.0, min(100.0, score))


def _weighted_quantile(values, weights, q):
    pairs = []
    for v, w in zip(values or [], weights or []):
        try:
            vv = float(v)
            ww = float(w)
        except Exception:
            continue
        if ww <= 0:
            continue
        pairs.append((vv, ww))
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[0])
    total = sum(w for _, w in pairs)
    if total <= 0:
        return None
    threshold = max(0.0, min(1.0, float(q))) * total
    run = 0.0
    for val, weight in pairs:
        run += weight
        if run >= threshold:
            return val
    return pairs[-1][0]


def _round4(value):
    if value is None:
        return None
    return round(float(value), 4)


def _build_neighbor_index(train_records):
    index = {}
    for rec in train_records:
        for token in rec.get("license_tokens", set()):
            index.setdefault(token, []).append(rec)
    return index


def _estimate_row_price(target, train_records, token_index=None, top_k=12, min_score=26.0):
    token_index = token_index or {}
    if not train_records:
        return None

    target_uid = str(target.get("uid", "")).strip()
    target_row = int(target.get("row", 0) or 0)
    token_pool = set(target.get("license_tokens", set()) or set())

    candidates = []
    if token_pool:
        seen_ids = set()
        for token in token_pool:
            for rec in token_index.get(token, []):
                marker = (rec.get("uid", ""), rec.get("row", 0))
                if marker in seen_ids:
                    continue
                seen_ids.add(marker)
                candidates.append(rec)
    if len(candidates) < max(40, int(top_k) * 4) and not token_pool:
        candidates = list(train_records)
    elif token_pool and not candidates:
        candidates = list(train_records)

    target_core_set = _core_license_tokens(token_pool)
    target_core_count = len(target_core_set)

    def _score_candidates(pool, strict_same_core, threshold):
        out = []
        for cand in pool:
            price_eok = cand.get("current_price_eok")
            if price_eok is None:
                continue
            if target_uid and str(cand.get("uid", "")).strip() == target_uid:
                continue
            if target_row > 0 and int(cand.get("row", 0) or 0) == target_row:
                continue
            cand_tokens = set(cand.get("license_tokens", set()) or set())
            cand_core = _core_license_tokens(cand_tokens) | _core_tokens_from_text(cand.get("license_text"))
            if target_core_count >= 2 and target_core_set and not (target_core_set & cand_core):
                continue
            if strict_same_core and not _is_single_token_same_core(token_pool, cand_tokens, cand.get("license_text")):
                continue
            if _is_single_token_cross_combo(token_pool, cand_tokens, cand.get("license_text")):
                continue
            if _is_single_token_profile_outlier(target, cand):
                continue
            sim = _neighbor_similarity_score(target, cand)
            if sim < float(threshold):
                continue
            out.append((sim, cand))
        return out

    strict_same_core = bool(_single_token_target_core(token_pool))
    threshold = float(min_score)
    scored = _score_candidates(candidates, strict_same_core, threshold)
    if strict_same_core and not scored:
        scored = _score_candidates(candidates, True, max(12.0, threshold - 8.0))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return None

    display_neighbors = scored[: max(1, int(top_k))]
    token_count = target_core_count if target_core_count > 0 else len(token_pool)
    sim_window = 18.0 if token_count >= 2 else (14.0 if token_count == 1 else 10.0)
    best_sim = float(scored[0][0])
    stat_floor = max(float(min_score), best_sim - sim_window)
    stat_neighbors = [(sim, rec) for sim, rec in scored if float(sim) >= stat_floor]
    min_stat_size = max(10, int(top_k))
    if len(stat_neighbors) < min_stat_size:
        stat_neighbors = scored[: max(min_stat_size, int(top_k) * 4)]

    prices = [float(rec.get("current_price_eok")) for _, rec in stat_neighbors]
    sims = [float(sim) for sim, _ in stat_neighbors]
    center = _weighted_quantile(prices, sims, 0.5)
    p25 = _weighted_quantile(prices, sims, 0.25)
    p75 = _weighted_quantile(prices, sims, 0.75)
    p10 = _weighted_quantile(prices, sims, 0.10)
    p90 = _weighted_quantile(prices, sims, 0.90)
    p95 = _weighted_quantile(prices, sims, 0.95)
    if center is None:
        return None
    if p25 is None:
        p25 = min(prices)
    if p75 is None:
        p75 = max(prices)
    if p10 is None:
        p10 = min(prices)
    if p90 is None:
        p90 = max(prices)
    if p95 is None:
        p95 = max(prices)

    abs_dev = [abs(x - center) for x in prices]
    mad = _weighted_quantile(abs_dev, sims, 0.5)
    mad = float(mad if mad is not None else 0.0)

    spread = max(float(p75) - float(p25), mad * 1.8, float(center) * 0.08, 0.08)
    low = max(0.05, float(center) - spread * 0.55)
    high = max(low, float(center) + spread * 0.55)
    avg_sim = sum(sims) / max(1.0, len(sims))
    token_count = len(set(target.get("license_tokens", set()) or set()))

    claim_eok = target.get("claim_price_eok")
    if isinstance(claim_eok, (int, float)) and claim_eok > 0:
        base_center = float(center)
        gap_ratio = abs(float(claim_eok) - base_center) / max(base_center, 0.1)
        claim_weight = min(0.35, 0.18 + max(0.0, gap_ratio - 0.15) * 0.20)
        p90_safe = max(float(p90), 0.1)
        p10_safe = max(float(p10), 0.1)
        if float(claim_eok) > (p90_safe * 1.25) and avg_sim >= 52:
            uplift = min(0.40, max(0.0, ((float(claim_eok) / p90_safe) - 1.25) * 0.28))
            if len(stat_neighbors) <= 6:
                uplift *= 1.15
            if token_count >= 2:
                uplift *= 1.10
            claim_weight = min(0.72, claim_weight + uplift)
        elif float(claim_eok) < (p10_safe * 0.80) and avg_sim >= 52:
            down = min(0.20, max(0.0, (0.80 - (float(claim_eok) / p10_safe)) * 0.18))
            claim_weight = max(0.10, claim_weight - down)
        center = (base_center * (1.0 - claim_weight)) + (float(claim_eok) * claim_weight)
        low = min(low, center)
        high = max(high, center)
        # 고가 희소구간(20억+) 과소추정 완화: 신뢰 가능한 청구가와 추가 합성
        if float(claim_eok) >= 20 and avg_sim >= 55:
            high_gap = (float(claim_eok) / max(float(center), 0.1)) - 1.0
            if high_gap > 0.22:
                sparse_pull = min(0.34, max(0.10, ((high_gap - 0.22) * 0.28) + 0.10))
                center = (float(center) * (1.0 - sparse_pull)) + (float(claim_eok) * sparse_pull)
                low = min(low, center)
                high = max(high, center)
        if float(claim_eok) > high * 1.18:
            extra = min(float(claim_eok) - high, max(float(center) * 0.45, (high - low) * 0.80))
            extra_w = 0.55
            if float(claim_eok) >= 20 and avg_sim >= 55:
                extra_w = 0.86
            high = high + max(0.0, extra * extra_w)
        if float(claim_eok) >= 20 and avg_sim >= 55 and float(claim_eok) > max(float(p90) * 1.20, float(center) * 1.18):
            high = max(high, float(claim_eok))

    # 저가 구간 과대추정 억제: 유사군 상단 분위보다 지나치게 높으면 상단 캡으로 안정화
    upper_cap = max(float(p95) * 1.35, float(p90) * 1.45, float(p75) * 1.60, 0.15)
    claim_allows_high = isinstance(claim_eok, (int, float)) and float(claim_eok) > (upper_cap * 1.05)
    if float(center) > upper_cap and not claim_allows_high:
        ratio = (float(center) / max(upper_cap, 0.1)) - 1.0
        pull = min(0.65, max(0.18, ratio * 0.55 + 0.18))
        next_center = (float(center) * (1.0 - pull)) + (upper_cap * pull)
        scale = next_center / max(float(center), 0.1)
        center = next_center
        low = max(0.05, float(low) * scale)
        high = max(low, float(high) * scale)
    if float(center) < float(low):
        low = float(center)
    if float(center) > float(high):
        high = float(center)
    if float(high) < float(low):
        high = float(low)

    coverage = min(1.0, len(stat_neighbors) / 8.0)
    dispersion = mad / max(float(center), 0.1)
    confidence_score = (avg_sim * 0.62) + (coverage * 25.0) + max(0.0, 20.0 - dispersion * 60.0)
    confidence_score = max(0.0, min(100.0, confidence_score))
    if confidence_score >= 75:
        confidence = "high"
    elif confidence_score >= 55:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "estimate_center_eok": _round4(center),
        "estimate_low_eok": _round4(low),
        "estimate_high_eok": _round4(high),
        "confidence": confidence,
        "confidence_score": _round4(confidence_score),
        "neighbor_count": len(stat_neighbors),
        "display_neighbor_count": len(display_neighbors),
        "avg_similarity": _round4(avg_sim),
        "neighbor_uids": [str(rec.get("uid", "")).strip() for _, rec in display_neighbors if str(rec.get("uid", "")).strip()],
    }


def _estimate_price_judgement(current_eok, claim_eok, center, low, high):
    if center is None:
        return "근거부족"
    if isinstance(claim_eok, (int, float)) and claim_eok > 0:
        if claim_eok > float(high) * 1.07:
            return "청구가 상단 초과"
        if claim_eok < float(low) * 0.93:
            return "청구가 하단 미만"
        return "청구가 적정권"
    if isinstance(current_eok, (int, float)) and current_eok > 0:
        if current_eok > float(high) * 1.07:
            return "현재가 상단 초과"
        if current_eok < float(low) * 0.93:
            return "현재가 하단 미만"
        return "현재가 적정권"
    return "신규추정"


def _build_yangdo_estimate_rows(all_values, uid_filter="", limit=0, only_missing=False, top_k=12, min_score=26.0):
    uid_filter = str(uid_filter or "").strip()
    records = _build_estimate_records(all_values)
    train_records = [r for r in records if isinstance(r.get("current_price_eok"), (int, float)) and r.get("current_price_eok", 0) > 0]
    token_index = _build_neighbor_index(train_records)

    output = []
    for rec in records:
        if uid_filter and str(rec.get("uid", "")).strip() != uid_filter:
            continue
        if only_missing and isinstance(rec.get("current_price_eok"), (int, float)) and rec.get("current_price_eok", 0) > 0:
            continue

        est = _estimate_row_price(
            rec,
            train_records=train_records,
            token_index=token_index,
            top_k=max(3, int(top_k or 12)),
            min_score=float(min_score),
        )
        if not est:
            continue

        current_eok = rec.get("current_price_eok")
        claim_eok = rec.get("claim_price_eok")
        center = est.get("estimate_center_eok")
        low = est.get("estimate_low_eok")
        high = est.get("estimate_high_eok")
        claim_gap = None
        current_gap = None
        if isinstance(claim_eok, (int, float)) and claim_eok > 0 and center is not None:
            claim_gap = _round4(float(claim_eok) - float(center))
        if isinstance(current_eok, (int, float)) and current_eok > 0 and center is not None:
            current_gap = _round4(float(current_eok) - float(center))

        row = {
            "row": rec.get("row", 0),
            "number": rec.get("number", 0),
            "uid": str(rec.get("uid", "")).strip(),
            "license": rec.get("license_text", ""),
            "current_price": rec.get("current_price_text", ""),
            "claim_price": rec.get("claim_price_text", ""),
            "estimate_center_eok": center,
            "estimate_low_eok": low,
            "estimate_high_eok": high,
            "recommend_range_text": f"{_fmt_eok_value(low)} ~ {_fmt_eok_value(high)}",
            "confidence": est.get("confidence", "low"),
            "confidence_score": est.get("confidence_score", 0),
            "neighbor_count": est.get("neighbor_count", 0),
            "avg_similarity": est.get("avg_similarity", 0),
            "neighbor_uids": est.get("neighbor_uids", []),
            "judgement": _estimate_price_judgement(current_eok, claim_eok, center, low, high),
            "claim_minus_estimate_eok": claim_gap,
            "current_minus_estimate_eok": current_gap,
        }
        output.append(row)

    output.sort(
        key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}.get(str(x.get("confidence", "")).lower(), 9),
            -_to_int_safe(x.get("number", 0)),
            -_to_int_safe(x.get("row", 0)),
        )
    )
    if int(limit or 0) > 0:
        output = output[: int(limit)]
    return output, {"train_count": len(train_records), "record_count": len(records)}


def _build_yangdo_estimate_sheet_values(rows, generated_at=None):
    ts = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values = [list(YANGDO_ESTIMATE_SHEET_HEADERS)]
    for row in rows:
        neighbor_uids = ",".join([x for x in row.get("neighbor_uids", []) if x][:5])
        values.append(
            [
                ts,
                row.get("row", ""),
                row.get("number", ""),
                row.get("uid", ""),
                row.get("license", ""),
                row.get("current_price", ""),
                row.get("claim_price", ""),
                row.get("estimate_center_eok", ""),
                row.get("estimate_low_eok", ""),
                row.get("estimate_high_eok", ""),
                row.get("recommend_range_text", ""),
                row.get("confidence", ""),
                row.get("confidence_score", ""),
                row.get("neighbor_count", ""),
                row.get("avg_similarity", ""),
                neighbor_uids,
                row.get("judgement", ""),
                row.get("claim_minus_estimate_eok", ""),
                row.get("current_minus_estimate_eok", ""),
            ]
        )
    return values


def _safe_json_for_script(data):
    return _yangdo_calculator.safe_json_for_script(data)


def _listing_detail_url(seoul_no=0, uid=""):
    return _yangdo_calculator.listing_detail_url(SITE_URL, seoul_no=seoul_no, now_uid=uid)


def _build_yangdo_calculator_training_dataset(records):
    return _yangdo_calculator.build_training_dataset(records, site_url=SITE_URL)


def _calc_quantile(values, q):
    return _yangdo_calculator.calc_quantile(values, q)


def _mean_or_none(values):
    return _yangdo_calculator.mean_or_none(values)


def _build_yangdo_calculator_meta(all_records, train_dataset):
    return _yangdo_calculator.build_meta(all_records, train_dataset)


def _build_yangdo_calculator_page_html(train_dataset, meta, view_mode="customer"):
    return _yangdo_calculator.build_page_html(
        train_dataset,
        meta,
        site_url=SITE_URL,
        license_canonical_by_key=LICENSE_CANONICAL_BY_KEY,
        generic_license_keys=sorted(list(_GENERIC_LICENSE_KEYS)),
        view_mode=view_mode,
        consult_endpoint=YANGDO_CONSULT_ENDPOINT,
        usage_endpoint=YANGDO_USAGE_ENDPOINT,
        estimate_endpoint=YANGDO_ESTIMATE_ENDPOINT,
        api_key=YANGDO_WIDGET_API_KEY,
        contact_phone=CALCULATOR_CONTACT_PHONE,
        openchat_url=KAKAO_OPENCHAT_URL,
        enable_consult_widget=YANGDO_ENABLE_CONSULT_WIDGET,
        enable_usage_log=YANGDO_ENABLE_USAGE_LOG,
        enable_hot_match=YANGDO_ENABLE_HOT_MATCH,
    )


def _compact_yangdo_training_dataset(train_dataset, max_rows=0):
    rows = list(train_dataset or [])
    try:
        limit = int(max_rows or 0)
    except Exception:
        limit = 0
    if limit <= 0 or len(rows) <= limit:
        return rows

    rows_sorted = sorted(
        rows,
        key=lambda r: (
            _to_int_safe(r.get("seoul_no", 0)),
            _to_int_safe(r.get("now_uid", 0)),
        ),
        reverse=True,
    )
    selected = []
    selected_idx = set()
    row_tokens = []
    token_freq = {}

    for row in rows_sorted:
        toks = sorted(
            {
                str(tok or "").strip()
                for tok in list(row.get("tokens", []) or [])
                if str(tok or "").strip()
            }
        )
        row_tokens.append(toks)
        for tok in toks:
            token_freq[tok] = token_freq.get(tok, 0) + 1

    def _pick(idx):
        if idx in selected_idx:
            return False
        if idx < 0 or idx >= len(rows_sorted):
            return False
        selected_idx.add(idx)
        selected.append(rows_sorted[idx])
        return True

    def _signal_score(row):
        # 축약본에서도 "비교 기준이 되는 매물"이 남도록 핵심 지표 기반으로 점수화
        specialty = max(0.0, _to_float_safe(row.get("specialty", None)))
        sales3 = max(0.0, _to_float_safe(row.get("sales3_eok", None)))
        sales5 = max(0.0, _to_float_safe(row.get("sales5_eok", None)))
        balance = max(0.0, _to_float_safe(row.get("balance_eok", None)))
        capital = max(0.0, _to_float_safe(row.get("capital_eok", None)))
        price = max(0.0, _to_float_safe(row.get("price_eok", None)))
        return (
            (math.log1p(specialty) * 0.28)
            + (math.log1p(sales3) * 0.28)
            + (math.log1p(sales5) * 0.10)
            + (math.log1p(balance) * 0.16)
            + (math.log1p(capital) * 0.08)
            + (math.log1p(price) * 0.10)
        )

    def _row_signal_tuple(idx):
        row = rows_sorted[idx]
        return (
            -_signal_score(row),
            -_to_int_safe(row.get("seoul_no", 0)),
            -_to_int_safe(row.get("now_uid", 0)),
        )

    # 1) 가격 극단/중앙 앵커 일부 포함 (범위 왜곡 방지)
    priced = [
        (idx, _to_float_safe(row.get("price_eok", None)))
        for idx, row in enumerate(rows_sorted)
        if _to_float_safe(row.get("price_eok", None)) > 0
    ]
    priced.sort(key=lambda x: x[1])
    if priced:
        edge_take = max(1, min(2, max(1, limit // 10)))
        for idx, _ in priced[:edge_take]:
            _pick(idx)
        for idx, _ in priced[-edge_take:]:
            _pick(idx)
        for q in (0.25, 0.5, 0.75):
            pos = int(round((len(priced) - 1) * q))
            _pick(priced[pos][0])
    if len(selected) >= limit:
        return selected[:limit]

    # 2) 전체 고신호(시평/실적/공제/자본) 매물 우선 확보
    ranked_global = sorted(range(len(rows_sorted)), key=_row_signal_tuple)
    signal_take = max(2, min(len(ranked_global), max(6, limit // 2)))
    for idx in ranked_global[:signal_take]:
        _pick(idx)
        if len(selected) >= limit:
            return selected[:limit]

    # 3) 토큰 조합별(예: 토건+토목+건축) 레퍼런스 앵커를 보강
    group_map = {}
    for idx, toks in enumerate(row_tokens):
        if not toks:
            continue
        key = tuple(toks)
        group_map.setdefault(key, []).append(idx)

    group_items = sorted(
        list(group_map.items()),
        key=lambda kv: (
            -len(kv[1]),
            -max(_to_int_safe(rows_sorted[i].get("seoul_no", 0)) for i in kv[1]),
        ),
    )
    for _group_key, idxs in group_items:
        ranked_group = sorted(idxs, key=_row_signal_tuple)
        for idx in ranked_group[:2]:
            _pick(idx)
            if len(selected) >= limit:
                return selected[:limit]
        newest_idx = max(
            idxs,
            key=lambda i: (
                _to_int_safe(rows_sorted[i].get("seoul_no", 0)),
                _to_int_safe(rows_sorted[i].get("now_uid", 0)),
            ),
        )
        _pick(newest_idx)
        if len(selected) >= limit:
            return selected[:limit]
        if len(selected) >= int(limit * 0.85):
            break

    # 4) 주요 토큰 커버리지 보강 (상위 빈도 토큰 기준)
    top_tokens = [tok for tok, _cnt in sorted(token_freq.items(), key=lambda x: (-x[1], x[0]))[: max(6, limit // 2)]]
    for tok in top_tokens:
        cand = [i for i, toks in enumerate(row_tokens) if tok in toks]
        if not cand:
            continue
        best_idx = min(cand, key=_row_signal_tuple)
        _pick(best_idx)
        newest_idx = max(
            cand,
            key=lambda i: (
                _to_int_safe(rows_sorted[i].get("seoul_no", 0)),
                _to_int_safe(rows_sorted[i].get("now_uid", 0)),
            ),
        )
        _pick(newest_idx)
        if len(selected) >= limit:
            return selected[:limit]

    # 5) 남은 슬롯은 최신순으로 채움
    for idx, _row in enumerate(rows_sorted):
        _pick(idx)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _resolve_yangdo_page_board_slug(override_slug=""):
    slug = str(override_slug or "").strip()
    if slug:
        return slug
    slug = str(YANGDO_CALCULATOR_BOARD_SLUG or "").strip()
    if slug:
        return slug
    return str(MNA_BOARD_SLUG or "mna").strip() or "mna"


def run_build_yangdo_calculator_page(
    output_path="",
    publish=False,
    wr_id=0,
    subject="",
    view_mode="customer",
    board_slug="",
    max_train_rows=0,
):
    print("🧮 [Calculator] 양도가 산정 페이지 생성 시작...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        book = client.open(SHEET_NAME)
        source_ws = book.sheet1
        all_values = source_ws.get_all_values()
    except Exception as e:
        print(f"❌ 산정 페이지용 시트 연결 실패: {e}")
        return

    records = _build_estimate_records(all_values)
    full_train_dataset = _build_yangdo_calculator_training_dataset(records)
    train_dataset = _compact_yangdo_training_dataset(full_train_dataset, max_rows=max_train_rows)
    meta = _build_yangdo_calculator_meta(records, full_train_dataset)
    meta["runtime_train_count"] = len(train_dataset)
    meta["runtime_compact"] = bool(len(train_dataset) < len(full_train_dataset))
    print(
        "   데이터 요약: "
        f"전체 {meta.get('all_record_count', 0)}건 / "
        f"학습(원본) {meta.get('train_count', 0)}건 / "
        f"학습(실행) {meta.get('runtime_train_count', 0)}건 "
        f"(가격보유율 {meta.get('priced_ratio', 0)}%)"
    )
    if not train_dataset:
        print("❌ 양도가 숫자 학습 데이터가 없어 페이지를 생성할 수 없습니다.")
        return

    mode = str(view_mode or YANGDO_CALCULATOR_MODE).strip().lower()
    if mode not in {"customer", "owner"}:
        mode = "customer"
    html_content = _build_yangdo_calculator_page_html(train_dataset, meta, view_mode=mode)
    out_path = str(output_path or YANGDO_CALCULATOR_OUTPUT).strip() or YANGDO_CALCULATOR_OUTPUT
    if str(out_path).strip().lower().endswith(".md"):
        print("⚠️ 출력 경로가 .md 입니다. 산정기 본문은 HTML/JS이므로 .html 경로 사용을 권장합니다.")
    _ensure_parent_dir(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ 산정 페이지 HTML 저장: {out_path} (mode={mode})")

    if not publish:
        return

    admin_id = str(CONFIG.get("ADMIN_ID", "") or os.getenv("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "") or os.getenv("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        print("❌ ADMIN_ID/ADMIN_PW 미설정: 사이트 게시 단계 중단")
        return

    default_subject = YANGDO_CALCULATOR_SUBJECT
    if mode == "owner":
        default_subject = "AI 양도가 산정 계산기 | 서울건설정보 (내부검수)"
    publish_subject = str(subject or default_subject).strip() or default_subject
    target_board_slug = _resolve_yangdo_page_board_slug(board_slug)
    try:
        publisher = MnaBoardPublisher(SITE_URL, target_board_slug, admin_id, admin_pw)
        publisher.login()
        result = publisher.publish_custom_html(
            subject=publish_subject,
            html_content=html_content,
            wr_id=int(wr_id or 0),
            link1=f"{SITE_URL}/{target_board_slug}",
        )
        print(
            "✅ 산정 페이지 게시 완료: "
            f"board={target_board_slug} "
            f"mode={result.get('mode', '')} "
            f"url={result.get('url', '')}"
        )
    except Exception as e:
        print(f"❌ 산정 페이지 게시 실패: {e}")


def extract_id_strict(text):
    if not text:
        return None
    match = re.match(r"^(\d{4,5})", str(text).strip())
    if match:
        return match.group(1)
    return None


def _as_lines(text):
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _as_aligned_lines(text):
    raw = str(text or "")
    if not raw:
        return []
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    rows = [line.strip() for line in normalized.split("\n")]
    while rows and rows[-1] == "":
        rows.pop()
    return rows


def _join_lines_preserve_alignment(values):
    rows = [str(v or "").strip() for v in (values or [])]
    while rows and rows[-1] == "":
        rows.pop()
    return "\n".join(rows)


def _compact_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


MEMO_TYPO_RULES = (
    ("이채", "이체"),
    ("나움", "나옴"),
    ("완류", "완료"),
)

MEMO_TYPO_RUNTIME = {
    "check": bool(MEMO_TYPO_CHECK),
    "fix": bool(MEMO_TYPO_FIX),
    "approve_all": bool(MEMO_TYPO_APPROVE_ALL),
    "approved_uids": set(MEMO_TYPO_APPROVED_UIDS),
    "decision_cache": {},
}


def _configure_memo_typo_runtime(check=None, fix=None, approve_all=None, approved_uids=None):
    if check is not None:
        MEMO_TYPO_RUNTIME["check"] = bool(check)
    if fix is not None:
        MEMO_TYPO_RUNTIME["fix"] = bool(fix)
    if approve_all is not None:
        MEMO_TYPO_RUNTIME["approve_all"] = bool(approve_all)
    if approved_uids is not None:
        MEMO_TYPO_RUNTIME["approved_uids"] = _parse_uid_set(approved_uids)
    MEMO_TYPO_RUNTIME["decision_cache"] = {}


def _detect_memo_typo_candidates(text):
    src = str(text or "")
    if not src:
        return src, []

    revised = src
    notices = []
    for wrong, right in MEMO_TYPO_RULES:
        if wrong not in revised:
            continue
        count = revised.count(wrong)
        revised = revised.replace(wrong, right)
        notices.append({"from": wrong, "to": right, "count": count})
    return revised, notices


def _memo_typo_decision(uid, notices):
    opts = dict(MEMO_TYPO_RUNTIME or {})
    if not notices:
        return False, "no_candidate"
    if not opts.get("fix", False):
        return False, "fix_disabled"
    if opts.get("approve_all", False):
        return True, "approve_all"

    uid_key = str(uid or "").strip()
    approved_uids = set(opts.get("approved_uids", set()) or set())
    if uid_key and uid_key in approved_uids:
        return True, "approved_uid_list"

    cache = dict(opts.get("decision_cache", {}) or {})
    if uid_key and uid_key in cache:
        return bool(cache[uid_key]), "cached"

    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        return False, "non_interactive_no_consent"

    pairs = ", ".join(f"{n['from']}->{n['to']}" for n in notices)
    ans = input(
        f"[동의요청] UID {uid_key or '-'} 비고 오타 의심({pairs}) "
        "시트 반영 시 수정할까요? [y/N]: "
    ).strip().lower()
    approved = ans in {"y", "yes"}
    if uid_key:
        MEMO_TYPO_RUNTIME["decision_cache"][uid_key] = approved
    return approved, "prompt"


def _review_memo_typo_for_sheet(uid, memo_text):
    raw = str(memo_text or "")
    if not MEMO_TYPO_RUNTIME.get("check", True):
        return raw

    revised, notices = _detect_memo_typo_candidates(raw)
    if not notices:
        return raw

    uid_key = str(uid or "").strip() or "-"
    pairs = ", ".join(f"{n['from']}->{n['to']}({n['count']})" for n in notices)
    apply_fix, reason = _memo_typo_decision(uid_key, notices)
    if apply_fix:
        print(f"⚠️ [비고 오타의심] UID {uid_key}: {pairs} -> 수정 적용({reason})")
        return revised

    print(f"⚠️ [비고 오타의심] UID {uid_key}: {pairs} -> 원문 유지({reason})")
    return raw


def _has_credit_grade_hint(text):
    src = _compact_text(text)
    if not src:
        return False
    if "신용" in src:
        return True
    upper = src.upper()
    return bool(re.search(r"\b(AAA|AA[\+\-]?|A[\+\-]?|BBB[\+\-]?)\b", upper))


def _extract_credit_note_lines(text):
    out = []
    for line in _split_text_lines(text):
        norm = _compact_text(line)
        if not norm:
            continue
        if _has_credit_grade_hint(norm):
            out.append(norm)
    return out


def _merge_sheet_memo_preserve_credit(old_memo, new_memo):
    new_lines = [_compact_text(x) for x in _split_text_lines(new_memo) if _compact_text(x)]
    if any(_has_credit_grade_hint(x) for x in new_lines):
        return "\n".join(new_lines)

    old_credit_lines = _extract_credit_note_lines(old_memo)
    if not old_credit_lines:
        return "\n".join(new_lines)

    seen = {_normalize_compare_text(x) for x in new_lines}
    merged = list(new_lines)
    for line in old_credit_lines:
        key = _normalize_compare_text(line)
        if key and key not in seen:
            merged.append(line)
            seen.add(key)
    return "\n".join(merged)


def _normalize_shares_balance(shares_raw, balance_raw):
    shares = _compact_text(shares_raw)
    balance = _compact_text(balance_raw)

    parts = []
    if shares and "/" in shares:
        parts.extend([_compact_text(p) for p in shares.split("/") if _compact_text(p)])
    if balance and "/" in balance:
        parts.extend([_compact_text(p) for p in balance.split("/") if _compact_text(p)])

    if parts:
        share_candidate = ""
        balance_candidate = balance
        for part in parts:
            if ("만" in part or "억" in part) and not balance_candidate:
                balance_candidate = part
                continue
            if ("좌" in part or re.search(r"\d", part)) and not share_candidate:
                share_candidate = part

        if share_candidate:
            shares = share_candidate
        if balance_candidate:
            balance = balance_candidate

    share_num = _number_token(shares)
    shares = f"{share_num}좌" if share_num else ""
    balance = balance.replace(" ", "")
    return shares, balance


def _truncate(text, limit):
    t = _compact_text(text)
    if len(t) <= limit:
        return t
    return t[: max(0, limit - 3)].rstrip() + "..."


def _to_num_key(uid):
    try:
        return int(str(uid))
    except Exception:
        return 0


def _safe_alert_text(html):
    if not html:
        return ""
    m = re.search(r"alert\((['\"])(.*?)\1\)", html, flags=re.S)
    if not m:
        return ""
    msg = m.group(2)
    msg = msg.replace(r"\n", " ").replace(r"\r", " ").strip()
    return _compact_text(msg)


def _ensure_parent_dir(path):
    parent = os.path.dirname(str(path or "").strip())
    if parent:
        os.makedirs(parent, exist_ok=True)


def _append_log_line(path, line):
    if not path:
        return
    _ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(str(line or "").rstrip() + "\n")


def _schema_guard(source, ok, reason, sample=""):
    if ok:
        return
    msg = (
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t"
        f"{source}\t{_compact_text(reason)}"
    )
    if sample:
        msg += f"\t샘플={_truncate(sample, 200)}"
    _append_log_line(SCHEMA_ALERT_LOG, msg)
    raise RuntimeError(f"[구조 변경 감지:{source}] {_compact_text(reason)}")


def _is_soft_empty_nowmna_list_page(ok, reason, page_no=0, html=""):
    if ok:
        return False
    try:
        page_no = int(page_no or 0)
    except Exception:
        page_no = 0
    reason_text = str(reason or "").strip().lower()
    if page_no < 5:
        return False
    if not reason_text.startswith("uid_row=0"):
        return False
    if _safe_alert_text(html):
        return False
    return True


def _validate_nowmna_list_schema(html, page_no=1):
    src = str(html or "")
    uid_count = 0
    for tr in BeautifulSoup(src, "html.parser").select("tr"):
        tds = tr.select("td")
        if len(tds) < 2:
            continue
        uid = _compact_text(tds[0].get_text(" ", strip=True))
        if uid.isdigit():
            uid_count += 1

    if page_no <= 2:
        ok = uid_count >= 5 and ("yangdo_view1.php?uid=" in src or "A.gif" in src or "B.gif" in src or "C.gif" in src)
    else:
        ok = uid_count >= 1 or ("yangdo_view1.php?uid=" in src)
    return ok, f"uid_row={uid_count}, page={page_no}"


def _validate_nowmna_detail_schema(page_html, uid=""):
    src = str(page_html or "")
    checks = [
        "면허년도",
        "양도가",
        "회사형태",
        "법인설립",
        "소재지",
    ]
    hit = sum(1 for token in checks if token in src)
    ok = hit >= 2
    return ok, f"detail_uid={uid}, token_hit={hit}"


def _validate_seoul_write_form_schema(form_html, context="write"):
    src = str(form_html or "")
    required_tokens = [
        "name=\"wr_subject\"",
        "name=\"wr_content\"",
        "name=\"wr_17\"",
        "name=\"wr_20\"",
    ]
    missing = [tok for tok in required_tokens if tok not in src]
    return len(missing) == 0, f"context={context}, missing={','.join(missing) if missing else '-'}"


def _load_upload_state(path):
    if not path or not os.path.exists(path):
        return {"uploaded_uids": {}, "last_uploaded_uid": 0}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"uploaded_uids": {}, "last_uploaded_uid": 0}
        if "uploaded_uids" not in data or not isinstance(data["uploaded_uids"], dict):
            data["uploaded_uids"] = {}
        if not str(data.get("last_uploaded_uid", "")).strip().isdigit():
            data["last_uploaded_uid"] = 0
        return data
    except Exception:
        return {"uploaded_uids": {}, "last_uploaded_uid": 0}


def _extract_last_uploaded_uid(state):
    payload = dict(state or {})
    explicit = payload.get("last_uploaded_uid", 0)
    try:
        explicit_num = int(explicit or 0)
    except Exception:
        explicit_num = 0
    uploaded = payload.get("uploaded_uids", {})
    max_uid = 0
    if isinstance(uploaded, dict):
        for raw_uid in uploaded.keys():
            txt = str(raw_uid or "").strip()
            if txt.isdigit():
                max_uid = max(max_uid, int(txt))
    return max(explicit_num, max_uid)


def _save_upload_state(path, state):
    state = dict(state or {})
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _field_or(item, *keys):
    for key in keys:
        val = str(item.get(key, "")).strip()
        if val:
            return val
    return ""


def _split_text_lines(value):
    text = str(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    out = []
    for line in text.splitlines():
        clean = _compact_text(line)
        if clean:
            out.append(clean)
    return out


def _korean_text_quality_fix(text):
    src = str(text or "")
    if not src or not KOREAN_QUALITY_FIX:
        return src

    out = src.replace("\r\n", "\n").replace("\r", "\n")

    # 자주 보이는 조사/문장 부자연 교정
    replacements = {
        "절차은": "절차는",
        "내용은을": "내용을",
        "요건은을": "요건을",
        "일정은을": "일정을",
        "비용은을": "비용을",
        "리스크은": "리스크는",
        "진행을 하세요": "진행하세요",
        "확인해 보세요": "확인하세요",
    }
    for old, new in replacements.items():
        out = out.replace(old, new)

    # 반복 명령문 축약
    out = re.sub(r"(하세요\.)\s*(?:하세요\.\s*)+", r"\1 ", out)
    out = re.sub(r"([가-힣A-Za-z0-9 ]+하세요\.)\s*\1+", r"\1 ", out)
    out = re.sub(r"(확인하세요\.)\s*(?:\1\s*)+", r"\1 ", out)

    # 문장부호/공백 정리
    out = re.sub(r"\s+([,.!?])", r"\1", out)
    out = re.sub(r"[ ]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _number_token(text):
    src = str(text or "").replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", src)
    return m.group(0) if m else ""


def _trim_decimal(value):
    try:
        num = float(value)
    except Exception:
        return str(value or "").strip()
    if abs(num - round(num)) < 1e-9:
        return str(int(round(num)))
    return f"{num:.4f}".rstrip("0").rstrip(".")


def _to_eok_text(raw):
    src = _compact_text(raw)
    if not src:
        return ""
    src = src.replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*억(?:\s*(\d+(?:\.\d+)?)\s*만)?", src)
    if m:
        eok = float(m.group(1))
        man = float(m.group(2) or 0.0)
        return _trim_decimal(eok + (man / 10000.0))
    m = re.search(r"(\d+(?:\.\d+)?)\s*만", src)
    if m:
        return _trim_decimal(float(m.group(1)) / 10000.0)
    token = _number_token(src)
    return _trim_decimal(token) if token else ""


def _to_man_text(raw):
    src = _compact_text(raw)
    if not src:
        return ""
    src = src.replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*억(?:\s*(\d+(?:\.\d+)?)\s*만)?", src)
    if m:
        eok = float(m.group(1))
        man = float(m.group(2) or 0.0)
        return _trim_decimal((eok * 10000.0) + man)
    m = re.search(r"(\d+(?:\.\d+)?)\s*만", src)
    if m:
        return _trim_decimal(m.group(1))
    token = _number_token(src)
    return _trim_decimal(token) if token else ""


def _to_year_text(raw):
    m = re.search(r"(19|20)\d{2}", str(raw or ""))
    return m.group(0) if m else ""


def _to_plain_number(raw):
    token = _number_token(raw)
    return _trim_decimal(token) if token else ""


def _repair_price_unit_markers(raw):
    src = str(raw or "")
    if not src:
        return ""
    src = (
        src.replace("ì–µ", "억")
        .replace("Ã¬â€“Âµ", "억")
        .replace("ï¿½", "억")
    )
    src = re.sub(r"(?<=\d)\s*[?？]{1,4}(?=\s*(?:[~∼〜-]\s*\d|\s*/|\s*$))", "억", src)
    return src


def _price_for_subject(raw):
    src = _compact_text(_repair_price_unit_markers(raw))
    if not src:
        return "협의"
    if "협의" in src and not re.search(r"\d", src):
        return "협의"
    parsed = _to_eok_text(src)
    if parsed:
        return parsed
    return src if len(src) <= 30 else src[:30]


def _normalize_metric(raw):
    src = _compact_text(raw)
    if not src or src in {"-", "--"}:
        return ""
    token = _number_token(src)
    return _trim_decimal(token) if token else src


def _guess_location_bucket(location):
    src = _compact_text(location)
    if not src:
        return ""
    if any(token in src for token in ("서울", "경기", "인천", "수도권")):
        return "수도권"
    if any(token in src for token in ("지방", "충", "강원", "전", "경", "제주", "세종", "부산", "대구", "광주", "대전", "울산")):
        return "지방"
    return ""


def _select_label_value_map(form, name):
    out = {}
    if form is None:
        return out
    sel = form.select_one(f"select[name='{name}']")
    if not sel:
        return out
    for opt in sel.select("option"):
        label = _compact_text(opt.get_text(" ", strip=True))
        value = str(opt.get("value", "")).strip()
        if not label or "선택" in label:
            continue
        if label not in out:
            out[label] = value
    return out


def _select_value_from_text(label_value_map, text):
    target = _compact_text(text)
    if not target:
        return ""
    if target in label_value_map:
        return label_value_map[target]
    target_key = re.sub(r"\s+", "", target).lower()
    best_val = ""
    best_score = -1
    for label, value in label_value_map.items():
        label_key = re.sub(r"\s+", "", _compact_text(label)).lower()
        if not label_key:
            continue
        if target_key == label_key:
            return value
        if target_key in label_key or label_key in target_key:
            score = min(len(target_key), len(label_key))
            if score > best_score:
                best_score = score
                best_val = value
    return best_val


def _extract_mna_cate_maps(form_html):
    cate1 = {}
    cate2 = {}
    html = str(form_html or "")
    m1 = re.search(r"var\s+mna_cate1\s*=\s*(\{.*?\});", html, flags=re.S)
    m2 = re.search(r"var\s+mna_cate2\s*=\s*(\{.*?\});", html, flags=re.S)
    if m1:
        try:
            cate1 = json.loads(m1.group(1))
        except Exception:
            cate1 = {}
    if m2:
        try:
            cate2 = json.loads(m2.group(1))
        except Exception:
            cate2 = {}
    return cate1, cate2


MNA_LICENSE_ALIASES = {
    "상하수도": "상하",
    "철근콘크리트": "철콘",
    "비계구조물": "비계",
    "구조물해체": "비계",
    "금속구조물": "금속",
    "금속구조물창호온실": "금속",
    "지붕판금": "지붕",
    "지붕판금건축물조립": "지붕",
    "습식방수": "습식",
    "미장방수": "습식",
    "정보통신공사업": "정보통신",
    "소방시설공사업": "소방",
    "전문소방공사업": "소방",
    "산림토목공사업": "산림토목",
    "숲길조성공사업": "숲길조성",
    "조경식재시설물": "조경식재시설물",
    "산업환경설비": "산업설비",
}


def _normalize_license_key(raw):
    text = _compact_text(raw).replace(" ", "")
    text = text.replace("(주)", "").replace("주식회사", "")
    text = re.sub(r"(업종|면허)$", "", text)
    text = re.sub(r"(공사업|건설업|공사|사업)$", "", text)
    return text


EXTRA_LICENSE_TERMS = (
    "건축",
    "토목",
    "토건",
    "조경",
    "산업설비",
    "토공",
    "포장",
    "보링",
    "실내",
    "금속",
    "지붕",
    "도장",
    "습식",
    "석공",
    "조경식재",
    "조경시설",
    "철콘",
    "상하",
    "철도",
    "철강구조물",
    "수중",
    "준설",
    "승강기",
    "삭도",
    "기계설비",
    "가스1종",
    "시설물",
    "지반조성",
    "전기",
    "정보통신",
    "소방",
    "주택",
    "대지",
    "공동사업",
    "문화재",
    "정비사업",
    "지하수",
    "폐수",
    "에너지절약",
    "산림",
    "산림경영",
    "숲가꾸기",
    "산림토목",
    "자연휴양림",
    "도시림",
    "숲길조성",
    "나무병원",
    "부동산개발",
    "석면",
)

_GENERIC_LICENSE_KEYS = {"", "기타", "일반", "전문", "사업", "공사", "건설", "면허", "업종"}


def _item_has_claim_price(item):
    return bool(_compact_text((item or {}).get("claim_price", "")))


def _validate_item_for_sheet(item, existing_claim_price=""):
    issues = []
    if not _item_has_claim_price(item) and not _compact_text(existing_claim_price):
        issues.append("claim_price_missing")
    return len(issues) == 0, issues


def _derive_sheet_status_for_new_item(item, issues=None):
    issue_list = [str(x).strip() for x in (issues or []) if str(x).strip()]
    if issue_list:
        return "완료"
    claim_status = _claim_to_status_label((item or {}).get("claim_price", ""))
    if claim_status in {"가능", "보류", "완료"}:
        return claim_status
    return _normalize_sync_status_label((item or {}).get("price", ""))


def _should_skip_site_publish_for_item(item, status_label, issues=None):
    if list(issues or []):
        return True
    return _normalize_sync_status_label(status_label) == "완료"


def _canonical_license_name(raw):
    src = _compact_text(raw)
    if not src:
        return ""
    key = _normalize_license_key(src)
    alias = MNA_LICENSE_ALIASES.get(key, src)
    out = normalize_license(alias)
    return _compact_text(out)


def _is_generic_license_name(raw):
    key = _normalize_license_key(_canonical_license_name(raw))
    return (not key) or (key in _GENERIC_LICENSE_KEYS)


def _display_license_lines(raw_lines, include_generic=True):
    out = []
    seen = set()
    for raw in _as_lines(raw_lines):
        canonical = _canonical_license_name(raw)
        key = _normalize_license_key(canonical)
        if not key:
            continue
        if (not include_generic) and key in _GENERIC_LICENSE_KEYS:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(canonical)
    return out


def _filtered_display_licenses(raw_lines):
    return _display_license_lines(raw_lines, include_generic=False)


def _build_license_term_index():
    canonical_by_key = {}

    def _register(term, canonical_hint=""):
        src = _compact_text(term)
        if not src:
            return
        key = _normalize_license_key(src)
        if key in _GENERIC_LICENSE_KEYS or len(key) < 2:
            return
        canonical = _canonical_license_name(canonical_hint or src)
        canonical_key = _normalize_license_key(canonical)
        if canonical_key in _GENERIC_LICENSE_KEYS or len(canonical_key) < 2:
            return
        canonical_by_key[key] = canonical
        canonical_by_key.setdefault(canonical_key, canonical)

    for src, dst in LICENSE_MAP.items():
        _register(src, dst)
        _register(dst, dst)
    for src, dst in MNA_LICENSE_ALIASES.items():
        _register(src, dst)
        _register(dst, dst)
    for term in EXTRA_LICENSE_TERMS:
        _register(term, term)

    keys = sorted(canonical_by_key.keys(), key=len, reverse=True)
    return canonical_by_key, keys


LICENSE_CANONICAL_BY_KEY, LICENSE_SEARCH_KEYS = _build_license_term_index()


_MEMO_LICENSE_EXCLUDE_TOKENS = ("전환", "제외", "반납", "말소", "포기", "선택")


def _extract_license_lines_from_text(text):
    out = []
    seen = set()
    for raw_line in _split_text_lines(text):
        if any(token in str(raw_line or "") for token in _MEMO_LICENSE_EXCLUDE_TOKENS):
            continue
        line_key = _normalize_license_key(raw_line)
        if not line_key:
            continue
        matches = []
        for key in LICENSE_SEARCH_KEYS:
            start = line_key.find(key)
            while start >= 0:
                end = start + len(key)
                matches.append((start, end, key))
                start = line_key.find(key, start + 1)
        if not matches:
            continue
        taken_ranges = []
        for start, end, key in sorted(matches, key=lambda x: (x[0], -(x[1] - x[0]))):
            overlap = False
            for t_start, t_end in taken_ranges:
                if not (end <= t_start or start >= t_end):
                    overlap = True
                    break
            if overlap:
                continue
            taken_ranges.append((start, end))
            canonical = _compact_text(LICENSE_CANONICAL_BY_KEY.get(key, key))
            canonical_key = _normalize_license_key(canonical)
            if not canonical_key or canonical_key in seen:
                continue
            seen.add(canonical_key)
            out.append(canonical)
    return out


def _merge_license_lines(primary_lines, secondary_lines):
    merged = []
    seen = set()
    for bucket in (list(primary_lines or []), list(secondary_lines or [])):
        for raw in bucket:
            canonical = _canonical_license_name(raw)
            key = _normalize_license_key(canonical)
            if key in _GENERIC_LICENSE_KEYS or len(key) < 2 or key in seen:
                continue
            seen.add(key)
            merged.append(canonical)
    return merged


def _license_candidates(raw):
    src = _compact_text(raw)
    if not src:
        return []
    tokens = [src, normalize_license(src)]
    for part in re.split(r"[,/|·ㆍ]", src):
        clean = _compact_text(part)
        if clean:
            tokens.append(clean)
            tokens.append(normalize_license(clean))
    out = []
    seen = set()
    for token in tokens:
        key = _normalize_license_key(token)
        if not key:
            continue
        alias = _normalize_license_key(MNA_LICENSE_ALIASES.get(key, key))
        for val in (key, alias):
            if val and val not in seen:
                seen.add(val)
                out.append(val)
    return out


def _build_cate2_lookup(cate2_map):
    lookup = {}
    for cate1, row_list in (cate2_map or {}).items():
        cate1_key = str(cate1)
        for row in row_list:
            if not isinstance(row, dict):
                continue
            for cate2, label in row.items():
                key = _normalize_license_key(label)
                if key:
                    lookup[key] = (cate1_key, str(cate2))
    return lookup


def _match_license_category(license_name, cate2_lookup):
    candidates = _license_candidates(license_name)
    for candidate in candidates:
        if candidate in cate2_lookup:
            return cate2_lookup[candidate]

    best = ("2", "")
    best_score = -1
    for candidate in candidates:
        for key, pair in cate2_lookup.items():
            if candidate in key or key in candidate:
                score = min(len(candidate), len(key))
                if score > best_score:
                    best_score = score
                    best = pair
    return best


def _build_sales_rows(item, cate2_lookup):
    lines = {
        "license": _as_aligned_lines(item.get("license", "")),
        "license_year": _as_aligned_lines(item.get("license_year", "")),
        "specialty": _as_aligned_lines(item.get("specialty", "")),
        "y20": _as_aligned_lines(item.get("y20", "")),
        "y21": _as_aligned_lines(item.get("y21", "")),
        "y22": _as_aligned_lines(item.get("y22", "")),
        "y23": _as_aligned_lines(item.get("y23", "")),
        "y24": _as_aligned_lines(item.get("y24", "")),
        "y25": _as_aligned_lines(item.get("y25", "")),
    }
    row_count = max([len(v) for v in lines.values()] + [0])
    if row_count == 0:
        return []

    def _aligned_metric_column(values):
        src = list(values or [])
        last_non_empty = -1
        for i, raw in enumerate(src):
            txt = _compact_text(raw)
            if txt and txt not in {"-", "--"}:
                last_non_empty = i
        out = []
        for i, raw in enumerate(src):
            normalized = _normalize_metric(raw)
            if normalized:
                out.append(normalized)
            elif last_non_empty >= 0 and i <= last_non_empty:
                # Preserve explicit interior blanks for row alignment.
                out.append("")
            else:
                out.append("")
        return out

    metric_cols = {
        "specialty": _aligned_metric_column(lines.get("specialty", [])),
        "y20": _aligned_metric_column(lines.get("y20", [])),
        "y21": _aligned_metric_column(lines.get("y21", [])),
        "y22": _aligned_metric_column(lines.get("y22", [])),
        "y23": _aligned_metric_column(lines.get("y23", [])),
        "y24": _aligned_metric_column(lines.get("y24", [])),
        "y25": _aligned_metric_column(lines.get("y25", [])),
    }

    rows = []
    for idx in range(row_count):
        lic = lines["license"][idx] if idx < len(lines["license"]) else ""
        if _is_generic_license_name(lic):
            continue
        source_values = (
            lic,
            lines["license_year"][idx] if idx < len(lines["license_year"]) else "",
            metric_cols["specialty"][idx] if idx < len(metric_cols["specialty"]) else "",
            metric_cols["y20"][idx] if idx < len(metric_cols["y20"]) else "",
            metric_cols["y21"][idx] if idx < len(metric_cols["y21"]) else "",
            metric_cols["y22"][idx] if idx < len(metric_cols["y22"]) else "",
            metric_cols["y23"][idx] if idx < len(metric_cols["y23"]) else "",
            metric_cols["y24"][idx] if idx < len(metric_cols["y24"]) else "",
            metric_cols["y25"][idx] if idx < len(metric_cols["y25"]) else "",
        )
        if not any(_compact_text(v) for v in source_values):
            continue
        cate1, cate2 = _match_license_category(lic, cate2_lookup)
        row = {
            "mp_cate1[]": cate1,
            "mp_cate2[]": cate2,
            "mp_year[]": _to_year_text(lines["license_year"][idx] if idx < len(lines["license_year"]) else ""),
            "mp_money[]": metric_cols["specialty"][idx] if idx < len(metric_cols["specialty"]) else "",
            "mp_2020[]": metric_cols["y20"][idx] if idx < len(metric_cols["y20"]) else "",
            "mp_2021[]": metric_cols["y21"][idx] if idx < len(metric_cols["y21"]) else "",
            "mp_2022[]": metric_cols["y22"][idx] if idx < len(metric_cols["y22"]) else "",
            "mp_2023[]": metric_cols["y23"][idx] if idx < len(metric_cols["y23"]) else "",
            "mp_2024[]": metric_cols["y24"][idx] if idx < len(metric_cols["y24"]) else "",
            "mp_2025[]": metric_cols["y25"][idx] if idx < len(metric_cols["y25"]) else "",
        }
        if any(_compact_text(v) for v in row.values()):
            rows.append(row)
    return rows


def _build_mna_subject(item):
    claim_raw = item.get("claim_price", "")
    claim_line = ""
    for line in reversed(_split_text_lines(claim_raw)):
        clean = _compact_text(_repair_price_unit_markers(line))
        if clean and re.search(r"\d", clean):
            claim_line = clean
            break
    if claim_line and ("~" in claim_line or "∼" in claim_line):
        return claim_line if len(claim_line) <= 30 else claim_line[:30]
    claim_first = _price_for_subject(claim_line or claim_raw)
    if claim_first and claim_first != "협의":
        return claim_first
    return _price_for_subject(item.get("price", ""))


def _build_mna_content(item):
    lines = []
    for raw_line in _split_text_lines(item.get("memo", "")):
        line = _korean_text_quality_fix(raw_line)
        if not re.match(r"^[\*\-\u2022\u00b7\u25b6\u2713]", line):
            line = f"* {line}"
        lines.append(line)
    if not lines:
        source = _compact_text(item.get("source_url", ""))
        if source:
            lines.append(f"* 원본 출처: {source}")
    return _korean_text_quality_fix("<br>\r\n".join(escape(line) for line in lines))


def _build_mna_admin_memo(item):
    uid = _compact_text(item.get("uid", ""))
    licenses = ", ".join(_display_license_lines(item.get("license", ""))[:4])
    sheet_price = _compact_text(item.get("sheet_price", "")) or _compact_text(item.get("price", ""))
    sheet_claim_price_raw = item.get("sheet_claim_price", "")
    if not _compact_text(sheet_claim_price_raw):
        sheet_claim_price_raw = item.get("claim_price", "")
    sheet_claim_price = _format_claim_price_for_admin_memo(
        sheet_claim_price_raw,
        uid=uid,
        licenses=licenses,
    )
    source = _compact_text(item.get("source_url", ""))
    lines = []
    if sheet_claim_price:
        lines.extend(_split_multiline_rows_keep_blank(sheet_claim_price))
    else:
        header = " ".join(x for x in (uid, licenses) if x).strip()
        price_line = _format_admin_price_for_memo(sheet_price)
        if header:
            lines.append(header)
        if price_line:
            lines.append(price_line)
        elif sheet_price and not header:
            lines.append(sheet_price)
    if source:
        if lines:
            lines.append("")
        lines.append(source)
    return _join_admin_memo_html_lines(lines)


def _split_multiline_rows_keep_blank(text):
    normalized = _normalize_multiline_text(text)
    if not normalized:
        return []
    return normalized.split("\n")


def _join_admin_memo_html_lines(lines):
    normalized = []
    prev_blank = False
    for raw in list(lines or []):
        txt = str(raw or "")
        clean = _compact_text(txt)
        if not clean:
            if normalized and not prev_blank:
                normalized.append("")
            prev_blank = True
            continue
        normalized.append(clean)
        prev_blank = False
    while normalized and normalized[-1] == "":
        normalized.pop()
    return "<br>".join(normalized)


def _validate_admin_memo_format(memo_text, require_br=True):
    src = str(memo_text or "")
    lines = _split_text_lines(src)
    errors = []

    if require_br and lines and "<br" not in src.lower():
        errors.append("br_missing")
    if not lines:
        errors.append("empty")
        return False, {"errors": errors, "uid": "", "url": "", "lines": []}

    uid = ""
    first = lines[0]
    m_uid = re.match(r"^\s*(\d{4,6})(?:\s+.+)?$", first)
    if m_uid:
        uid = m_uid.group(1)
    else:
        errors.append("uid_header_missing")

    price_lines = [ln for ln in lines[1:] if not ln.lower().startswith("http")]
    if not price_lines:
        errors.append("price_line_missing")

    url_candidates = [ln for ln in lines if ln.lower().startswith("http")]
    target_url = url_candidates[-1] if url_candidates else ""
    if not target_url:
        errors.append("source_url_missing")
    else:
        if not _is_allowed_nowmna_url(target_url):
            errors.append("source_url_host_invalid")
        url_uid = extract_id_strict(target_url)
        if uid and url_uid and uid != url_uid:
            errors.append("uid_url_mismatch")

    legacy_tokens = ("시트기준", "원문양도가")
    if any(tok in src for tok in legacy_tokens):
        errors.append("legacy_token_detected")

    return len(errors) == 0, {
        "errors": errors,
        "uid": uid,
        "url": target_url,
        "lines": lines,
    }


def _recommend_image_count_for_listing(item):
    src = dict(item or {})
    license_count = len([x for x in _as_lines(src.get("license", "")) if _compact_text(x)])
    memo_lines = len([x for x in _split_text_lines(src.get("memo", "")) if _compact_text(x)])
    memo_chars = len("".join(_split_text_lines(src.get("memo", ""))))
    if license_count >= 2 or memo_lines >= 8 or memo_chars >= 180:
        return 2
    if license_count >= 1 and (memo_lines >= 4 or memo_chars >= 80):
        return 1
    return 0


def _evaluate_listing_quality(item):
    src = dict(item or {})
    memo_lines = [x for x in _split_text_lines(src.get("memo", "")) if _compact_text(x)]
    memo_chars = len("".join(memo_lines))
    license_lines = [x for x in _as_lines(src.get("license", "")) if _compact_text(x)]

    score = 0
    reasons = []

    if license_lines:
        score += min(25, 10 + (len(license_lines) * 7))
    else:
        reasons.append("license_missing")

    if memo_chars >= 120:
        score += 35
    elif memo_chars >= 60:
        score += 24
    elif memo_chars >= 30:
        score += 12
    else:
        reasons.append("memo_too_short")

    if len(memo_lines) >= 5:
        score += 20
    elif len(memo_lines) >= 3:
        score += 12
    elif len(memo_lines) >= 1:
        score += 6
    else:
        reasons.append("memo_lines_missing")

    if _compact_text(src.get("price", "")) or _compact_text(src.get("sheet_price", "")):
        score += 10
    else:
        reasons.append("price_missing")

    if _compact_text(src.get("source_url", "")):
        score += 10
    else:
        reasons.append("source_url_missing")

    recommended_images = _recommend_image_count_for_listing(src)
    if recommended_images > 0:
        score += min(5, recommended_images * 2)

    final_score = max(0, min(100, int(score)))
    return {
        "score": final_score,
        "ok": final_score >= int(LISTING_QUALITY_MIN_SCORE),
        "reasons": reasons,
        "recommended_images": recommended_images,
        "memo_chars": memo_chars,
        "memo_lines": len(memo_lines),
        "license_count": len(license_lines),
    }


def _append_low_quality_queue(item, quality):
    path = str(LOW_QUALITY_QUEUE_FILE or "").strip()
    if not path:
        return
    payload = _load_json_file(path, default={}) or {}
    rows = list(payload.get("items", []) or [])
    uid = _compact_text(dict(item or {}).get("uid", ""))
    row = {
        "uid": uid,
        "score": int((quality or {}).get("score", 0) or 0),
        "reasons": list((quality or {}).get("reasons", []) or []),
        "recommended_images": int((quality or {}).get("recommended_images", 0) or 0),
        "source_url": _compact_text(dict(item or {}).get("source_url", "")),
        "queued_at": datetime.now().isoformat(timespec="seconds"),
    }
    if uid:
        rows = [x for x in rows if _compact_text((x or {}).get("uid", "")) != uid]
    rows.append(row)
    payload["items"] = rows
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_json_file(path, payload)


def _normalize_multiline_text(text):
    src = str(text or "")
    if not src:
        return ""
    src = re.sub(r"<br\s*/?>", "\n", src, flags=re.I)
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    rows = [_compact_text(row) for row in src.split("\n")]
    while rows and not rows[-1]:
        rows.pop()
    return "\n".join(rows).strip()


def _format_admin_price_for_memo(raw_value):
    src = _compact_text(_repair_price_unit_markers(raw_value))
    if not src:
        return ""
    src = (
        src.replace("－", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("∼", "~")
        .replace("〜", "~")
        .replace("／", "/")
    )
    src = re.sub(r"\s+", "", src)

    # Keep 입금가/양도가 간극 표기(예: 2.1억~2.6억 / 2.6억)를 그대로 유지한다.
    if "/" in src:
        parts = [p for p in (x.strip() for x in src.split("/")) if p]
        if len(parts) >= 2:
            return f"{parts[0]} / {parts[1]}"
        return src
    return src


def _looks_like_claim_price_line(text):
    src = _compact_text(text)
    if not src:
        return False
    if any(token in src for token in ("협의", "보류", "완료", "삭제", "가능")):
        return True
    if re.search(r"\d", src) and any(mark in src for mark in ("억", "만", "~", "-", "∼", "〜", "–", "—")):
        return True
    if re.search(r"\d", src) and ("/" in src) and any(mark in src for mark in ("억", "만")):
        return True
    return False


def _normalize_admin_memo_header_line(text):
    src = _compact_text(text)
    if not src:
        return ""
    src = re.sub(r"^\s*UID\s*[:#]?\s*", "", src, flags=re.I)
    src = re.sub(r"\s+", " ", src).strip()
    return src


def _split_header_price_inline(text):
    src = _compact_text(text)
    if not src:
        return "", ""
    src = (
        src.replace("－", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("∼", "~")
        .replace("〜", "~")
    )
    m = re.search(
        r"(\d+(?:\.\d+)?\s*(?:[억만에\?])?\s*[~-]\s*\d+(?:\.\d+)?\s*(?:[억만에\?])?|\d+(?:\.\d+)?\s*(?:[억만에\?]))",
        src,
    )
    if not m:
        return _normalize_admin_memo_header_line(src), ""
    header = _normalize_admin_memo_header_line(src[: m.start()])
    price = _format_admin_price_for_memo(m.group(1))
    return header, price


def _format_claim_price_for_admin_memo(raw_value, uid="", licenses=""):
    normalized = _normalize_multiline_text(raw_value)
    if not normalized:
        return ""

    fallback_header = " ".join(x for x in (_compact_text(uid), _compact_text(licenses)) if x).strip()
    rows = normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    sections = []
    bucket = []
    for raw in rows:
        row = _compact_text(raw)
        if not row:
            if bucket:
                sections.append(bucket)
                bucket = []
            continue
        bucket.append(row)
    if bucket:
        sections.append(bucket)

    rendered_sections = []
    for sec in sections:
        sec_lines = []
        idx = 0
        while idx < len(sec):
            line = sec[idx]
            header_inline, price_inline = _split_header_price_inline(line)

            if price_inline and header_inline:
                sec_lines.append(header_inline)
                sec_lines.append(price_inline)
                idx += 1
                continue

            if _looks_like_claim_price_line(line):
                price_line = _format_admin_price_for_memo(line)
                if sec_lines:
                    sec_lines.append(price_line)
                else:
                    if fallback_header:
                        sec_lines.append(fallback_header)
                    sec_lines.append(price_line)
                idx += 1
                continue

            header = _normalize_admin_memo_header_line(line)
            price = ""
            if idx + 1 < len(sec) and _looks_like_claim_price_line(sec[idx + 1]):
                price = _format_admin_price_for_memo(sec[idx + 1])
                idx += 1
            if header:
                sec_lines.append(header)
            elif fallback_header:
                sec_lines.append(fallback_header)
            if price:
                sec_lines.append(price)
            idx += 1

        sec_lines = [x for x in (_compact_text(x) for x in sec_lines) if x]
        if sec_lines:
            rendered_sections.append(sec_lines)

    if not rendered_sections:
        return ""
    out = []
    for sec_idx, sec_lines in enumerate(rendered_sections):
        if sec_idx > 0:
            out.append("")
        out.extend(sec_lines)
    return "\n".join(out).strip()


def _normalize_claim_price_for_sheet(raw_value, uid="", licenses=""):
    formatted = _format_claim_price_for_admin_memo(raw_value, uid=uid, licenses=licenses)
    if not formatted:
        return ""
    lines = [x for x in _split_multiline_rows_keep_blank(formatted) if _compact_text(x)]
    if not lines:
        return ""
    header = " ".join(x for x in (_compact_text(uid), _compact_text(licenses)) if x).strip()
    price_lines = [x for x in lines if _looks_like_claim_price_line(x)]
    out = []
    if header:
        out.append(header)
    if price_lines:
        out.extend(price_lines)
    elif not header:
        out.extend(lines)
    return "\n".join(out).strip()


def _build_mna_payload_updates(item, form, form_html, defaults, status_label="가능"):
    updates = {}

    # 기본 상단 필드
    updates["wr_sang"] = MY_COMPANY_NAME
    updates["wr_subject"] = _build_mna_subject(item)
    updates["wr_content"] = _build_mna_content(item)
    updates["wr_1"] = _to_plain_number(item.get("shares", ""))
    updates["wr_4"] = _to_eok_text(item.get("capital", ""))
    updates["wr_5"] = _to_man_text(item.get("balance", ""))
    updates["wr_7"] = _compact_text(item.get("location", ""))
    updates["wr_8"] = _normalize_metric(item.get("debt_ratio", ""))
    updates["wr_10"] = _normalize_metric(item.get("liquidity_ratio", ""))
    updates["wr_19"] = _to_eok_text(item.get("surplus", ""))
    updates["wr_20"] = _build_mna_admin_memo(item)

    phone = _compact_text(defaults.get("wr_p2", "")) or MY_PHONE
    if phone:
        updates["wr_p2"] = phone

    if not _compact_text(defaults.get("wr_name", "")):
        updates["wr_name"] = "관리자"

    # 상태/회사형태/협회/설립년도 select 값 보정
    wr17_map = _select_label_value_map(form, "wr_17")
    wr2_map = _select_label_value_map(form, "wr_2")
    wr3_map = _select_label_value_map(form, "wr_3")
    wr6_map = _select_label_value_map(form, "wr_6")

    if status_label is not None:
        updates["wr_17"] = _select_value_from_text(wr17_map, status_label) or str(defaults.get("wr_17", "")).strip() or "1"

    company_type = _compact_text(item.get("company_type", ""))
    if company_type:
        mapped_type = _select_value_from_text(wr2_map, company_type)
        if mapped_type:
            updates["wr_2"] = mapped_type

    founded_year = _to_year_text(item.get("founded_year", ""))
    if founded_year:
        mapped_year = _select_value_from_text(wr3_map, founded_year)
        if mapped_year:
            updates["wr_3"] = mapped_year

    assoc = _compact_text(item.get("association", ""))
    if assoc:
        mapped_assoc = _select_value_from_text(wr6_map, assoc)
        if mapped_assoc:
            updates["wr_6"] = mapped_assoc

    # 라디오 항목
    updates["wr_12"] = "없음"
    updates["wr_16"] = "빈공란"

    location_bucket = _guess_location_bucket(item.get("location", ""))
    if location_bucket:
        updates["chk2"] = location_bucket

    # 실적 행(mp_*[]) 구성
    _, cate2_map = _extract_mna_cate_maps(form_html)
    cate2_lookup = _build_cate2_lookup(cate2_map)
    sales_rows = _build_sales_rows(item, cate2_lookup)
    raw_license_lines = [x for x in _split_text_lines(item.get("license", "")) if _compact_text(x)]
    generic_only_license = bool(raw_license_lines) and not bool(_filtered_display_licenses(item.get("license", "")))
    if sales_rows:
        for key in (
            "mp_cate1[]",
            "mp_cate2[]",
            "mp_year[]",
            "mp_money[]",
            "mp_2020[]",
            "mp_2021[]",
            "mp_2022[]",
            "mp_2023[]",
            "mp_2024[]",
            "mp_2025[]",
        ):
            updates[key] = [row.get(key, "") for row in sales_rows]
    elif generic_only_license:
        for key in (
            "mp_cate1[]",
            "mp_cate2[]",
            "mp_year[]",
            "mp_money[]",
            "mp_2020[]",
            "mp_2021[]",
            "mp_2022[]",
            "mp_2023[]",
            "mp_2024[]",
            "mp_2025[]",
        ):
            updates[key] = []

    # html 모드 + 링크
    updates["html"] = "html1"
    source_url = _compact_text(item.get("source_url", ""))
    if source_url and "wr_link1" in defaults and not _compact_text(defaults.get("wr_link1", "")):
        updates["wr_link1"] = source_url

    return updates


class MnaBoardPublisher:
    """seoulmna.co.kr mna 게시판 업로드 클라이언트 (G5 기반)."""

    _process_guard_depth = 0
    _process_guard_lock_file = ""
    _process_guard_session_id = ""

    def __init__(self, site_url, board_slug, admin_id, admin_pw):
        self.site_url = str(site_url).rstrip("/")
        self.site_host = _host_of(self.site_url)
        self.board_slug = str(board_slug).strip() or "mna"
        self.admin_id = str(admin_id or "").strip()
        self.admin_pw = str(admin_pw or "").strip()
        self._validate_site_domain()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
            }
        )
        self._last_write_url = ""
        self.daily_limit_state_file = SEOUL_DAILY_LIMIT_STATE_FILE
        self.daily_request_cap = int(SEOUL_DAILY_REQUEST_CAP)
        self.daily_write_cap = int(SEOUL_DAILY_WRITE_CAP)
        self._daily_limit_state = self._load_daily_limit_state()
        self._traffic_guard_enabled = bool(
            SEOUL_TRAFFIC_GUARD_ENABLED
            and (self.site_host in LISTING_ALLOWED_HOSTS)
            and bool(self.admin_id)
            and bool(self.admin_pw)
        )
        self._guard_request_buffer = int(SEOUL_TRAFFIC_GUARD_REQUEST_BUFFER)
        self._guard_write_buffer = int(SEOUL_TRAFFIC_GUARD_WRITE_BUFFER)
        self._guard_min_interval_sec = float(SEOUL_TRAFFIC_GUARD_MIN_INTERVAL_SEC)
        self._guard_report_file = str(SEOUL_TRAFFIC_GUARD_REPORT_FILE or "").strip()
        self._guard_session_dir = str(SEOUL_TRAFFIC_GUARD_SESSION_DIR or "").strip()
        self._guard_lock_file = str(SEOUL_TRAFFIC_GUARD_LOCK_FILE or "").strip()
        self._guard_lock_stale_sec = int(SEOUL_TRAFFIC_GUARD_LOCK_STALE_SEC)
        self._guard_started_at = datetime.now()
        self._guard_closed = False
        self._guard_lock_acquired = False
        self._guard_session_id = ""
        self._guard_request_count = 0
        self._guard_write_count = 0
        self._guard_error_count = 0
        self._guard_last_error = ""
        self._guard_last_request_tick = 0.0
        self._guard_preflight = {}
        if self._traffic_guard_enabled:
            self._start_traffic_guard()
        atexit.register(self.close)

    def _validate_site_domain(self):
        if not self.site_host:
            raise ValueError("[domain-guard] SITE_URL host is empty.")
        if self.site_host in BLOG_HOSTS:
            raise ValueError(
                "[domain-guard] SITE_URL points to seoulmna.kr(blog). "
                "all.py listing publisher must target seoulmna.co.kr only."
            )
        if STRICT_DOMAIN_GUARD and self.site_host not in LISTING_ALLOWED_HOSTS:
            raise ValueError(
                f"[domain-guard] SITE_URL host '{self.site_host}' is not allowed. "
                "Use seoulmna.co.kr for listing uploads."
            )

    def _daily_slot(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _load_daily_limit_state(self):
        slot = self._daily_slot()
        data = {"date": slot, "requests": 0, "writes": 0}
        path = str(self.daily_limit_state_file or "").strip()
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    data["date"] = str(raw.get("date", slot)).strip() or slot
                    data["requests"] = max(0, int(raw.get("requests", 0) or 0))
                    data["writes"] = max(0, int(raw.get("writes", 0) or 0))
            except Exception:
                pass
        if str(data.get("date", "")) != slot:
            data = {"date": slot, "requests": 0, "writes": 0}
        return data

    def _save_daily_limit_state(self):
        path = str(self.daily_limit_state_file or "").strip()
        if not path:
            return
        try:
            _ensure_parent_dir(path)
            payload = dict(self._daily_limit_state or {})
            payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _ensure_daily_limit_slot(self):
        slot = self._daily_slot()
        if str((self._daily_limit_state or {}).get("date", "")) == slot:
            return
        self._daily_limit_state = {"date": slot, "requests": 0, "writes": 0}
        self._save_daily_limit_state()

    def _is_write_mutation(self, method, url):
        method_u = str(method or "").upper()
        url_txt = str(url or "")
        return method_u == "POST" and "write_update.php" in url_txt

    def _guard_payload_base(self):
        return {
            "session_id": str(self._guard_session_id or ""),
            "site_url": str(self.site_url),
            "board_slug": str(self.board_slug),
            "pid": int(os.getpid()),
            "started_at": self._guard_started_at.isoformat(timespec="seconds"),
            "request_buffer": int(self._guard_request_buffer),
            "write_buffer": int(self._guard_write_buffer),
            "min_interval_sec": float(self._guard_min_interval_sec),
            "session_requests": int(self._guard_request_count),
            "session_writes": int(self._guard_write_count),
            "session_errors": int(self._guard_error_count),
            "last_error": str(self._guard_last_error or ""),
        }

    def _save_guard_report(self, phase, extra=None):
        if not self._traffic_guard_enabled:
            return
        payload = self._guard_payload_base()
        payload["phase"] = str(phase or "")
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if isinstance(extra, dict):
            payload.update(extra)
        latest_path = str(self._guard_report_file or "").strip()
        if latest_path:
            try:
                _ensure_parent_dir(latest_path)
                with open(latest_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        session_dir = str(self._guard_session_dir or "").strip()
        if session_dir and self._guard_session_id:
            try:
                os.makedirs(session_dir, exist_ok=True)
                session_path = os.path.join(session_dir, f"{self._guard_session_id}.json")
                with open(session_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _load_lock_payload(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_lock_payload(self, path, payload):
        _ensure_parent_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _acquire_traffic_guard_lock(self):
        lock_path = str(self._guard_lock_file or "").strip()
        if not lock_path:
            return

        if (
            int(MnaBoardPublisher._process_guard_depth) > 0
            and str(MnaBoardPublisher._process_guard_lock_file) == lock_path
        ):
            MnaBoardPublisher._process_guard_depth += 1
            self._guard_lock_acquired = True
            self._guard_session_id = str(MnaBoardPublisher._process_guard_session_id or "")
            return

        if os.path.exists(lock_path):
            now_ts = time.time()
            age_sec = max(0.0, now_ts - float(os.path.getmtime(lock_path)))
            lock_payload = self._load_lock_payload(lock_path)
            lock_pid = int(lock_payload.get("pid", 0) or 0)
            lock_sid = str(lock_payload.get("session_id", "")).strip()
            if lock_pid == int(os.getpid()):
                self._guard_lock_acquired = True
                self._guard_session_id = lock_sid or datetime.now().strftime("%Y%m%d_%H%M%S")
                MnaBoardPublisher._process_guard_depth = 1
                MnaBoardPublisher._process_guard_lock_file = lock_path
                MnaBoardPublisher._process_guard_session_id = self._guard_session_id
                return
            if age_sec <= float(self._guard_lock_stale_sec):
                raise RuntimeError(
                    "co.kr traffic-guard lock active: another task appears to be running "
                    f"(age={int(age_sec)}s, lock={lock_path})"
                )
            try:
                os.remove(lock_path)
            except Exception as exc:
                raise RuntimeError(
                    "co.kr traffic-guard stale lock cleanup failed "
                    f"(lock={lock_path}, age={int(age_sec)}s): {exc}"
                ) from exc

        sid = datetime.now().strftime("%Y%m%d_%H%M%S")
        sid = f"{sid}_{os.getpid()}_{int(time.time() * 1000) % 1000:03d}"
        payload = {
            "session_id": sid,
            "pid": int(os.getpid()),
            "site_url": str(self.site_url),
            "board_slug": str(self.board_slug),
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_lock_payload(lock_path, payload)
        self._guard_lock_acquired = True
        self._guard_session_id = sid
        MnaBoardPublisher._process_guard_depth = 1
        MnaBoardPublisher._process_guard_lock_file = lock_path
        MnaBoardPublisher._process_guard_session_id = sid

    def _release_traffic_guard_lock(self):
        if not self._guard_lock_acquired:
            return
        lock_path = str(self._guard_lock_file or "").strip()
        if not lock_path:
            self._guard_lock_acquired = False
            return

        if (
            int(MnaBoardPublisher._process_guard_depth) > 0
            and str(MnaBoardPublisher._process_guard_lock_file) == lock_path
        ):
            MnaBoardPublisher._process_guard_depth -= 1
            if MnaBoardPublisher._process_guard_depth <= 0:
                try:
                    if os.path.exists(lock_path):
                        payload = self._load_lock_payload(lock_path)
                        sid = str(payload.get("session_id", "")).strip()
                        expected = str(MnaBoardPublisher._process_guard_session_id or "").strip()
                        if (not sid) or (sid == expected):
                            os.remove(lock_path)
                except Exception:
                    pass
                MnaBoardPublisher._process_guard_depth = 0
                MnaBoardPublisher._process_guard_lock_file = ""
                MnaBoardPublisher._process_guard_session_id = ""
        self._guard_lock_acquired = False

    def _start_traffic_guard(self):
        self._acquire_traffic_guard_lock()
        self._guard_preflight = self.daily_limit_summary()
        self._save_guard_report(
            "preflight",
            {
                "preflight": dict(self._guard_preflight or {}),
                "message": "co.kr task guard armed",
            },
        )

    def _enforce_traffic_guard_before_request(self, method, url):
        if not self._traffic_guard_enabled:
            return
        min_gap = max(0.0, float(self._guard_min_interval_sec))
        if min_gap > 0 and self._guard_last_request_tick > 0:
            elapsed = max(0.0, float(time.monotonic() - self._guard_last_request_tick))
            if elapsed < min_gap:
                time.sleep(min_gap - elapsed)

        self._ensure_daily_limit_slot()
        state = dict(self._daily_limit_state or {})
        req_used = int(state.get("requests", 0) or 0)
        write_used = int(state.get("writes", 0) or 0)
        req_cap = int(self.daily_request_cap or 0)
        write_cap = int(self.daily_write_cap or 0)
        req_stop = max(0, req_cap - int(self._guard_request_buffer))
        write_stop = max(0, write_cap - int(self._guard_write_buffer))

        if req_cap > 0 and req_used >= req_stop:
            self._save_guard_report(
                "blocked",
                {
                    "reason": "request_headroom",
                    "daily": self.daily_limit_summary(),
                    "requested_method": str(method or "").upper(),
                    "requested_url": str(url or "")[:300],
                },
            )
            raise RuntimeError(
                "co.kr traffic guard stop: request headroom exhausted "
                f"({req_used}/{req_cap}, buffer={self._guard_request_buffer})"
            )

        if self._is_write_mutation(method, url) and write_cap > 0 and write_used >= write_stop:
            self._save_guard_report(
                "blocked",
                {
                    "reason": "write_headroom",
                    "daily": self.daily_limit_summary(),
                    "requested_method": str(method or "").upper(),
                    "requested_url": str(url or "")[:300],
                },
            )
            raise RuntimeError(
                "co.kr traffic guard stop: write headroom exhausted "
                f"({write_used}/{write_cap}, buffer={self._guard_write_buffer})"
            )

    def _record_guard_request(self, method, url, error_msg=""):
        if not self._traffic_guard_enabled:
            return
        self._guard_request_count += 1
        if self._is_write_mutation(method, url):
            self._guard_write_count += 1
        if error_msg:
            self._guard_error_count += 1
            self._guard_last_error = str(error_msg or "")[:500]
        self._guard_last_request_tick = time.monotonic()
        if error_msg or self._is_write_mutation(method, url) or (self._guard_request_count % 25 == 0):
            self._save_guard_report(
                "in_progress",
                {
                    "daily": self.daily_limit_summary(),
                    "last_method": str(method or "").upper(),
                    "last_url": str(url or "")[:300],
                },
            )

    def _track_daily_limit(self, method, url):
        self._ensure_daily_limit_slot()
        state = self._daily_limit_state
        req_used = max(0, int(state.get("requests", 0) or 0))
        write_used = max(0, int(state.get("writes", 0) or 0))
        req_next = req_used + 1
        method_u = str(method or "").upper()
        url_txt = str(url or "")
        is_write_mutation = self._is_write_mutation(method_u, url_txt)
        write_next = write_used + (1 if is_write_mutation else 0)

        if self.daily_request_cap > 0 and req_next > self.daily_request_cap:
            raise RuntimeError(
                f"seoulmna.co.kr 자동화 일일 요청 상한 초과 ({req_used}/{self.daily_request_cap})"
            )
        if self.daily_write_cap > 0 and is_write_mutation and write_next > self.daily_write_cap:
            raise RuntimeError(
                f"seoulmna.co.kr 자동화 일일 수정 상한 초과 ({write_used}/{self.daily_write_cap})"
            )

        state["requests"] = req_next
        if is_write_mutation:
            state["writes"] = write_next
        state["last_request_at"] = datetime.now().isoformat(timespec="seconds")
        state["last_method"] = method_u
        state["last_url"] = url_txt[:300]
        self._save_daily_limit_state()

    def _request(self, method, url, **kwargs):
        method_u = str(method or "").upper()
        self._enforce_traffic_guard_before_request(method_u, url)
        try:
            self._track_daily_limit(method_u, url)
            if method_u == "GET":
                res = self.session.get(url, **kwargs)
            else:
                res = self.session.post(url, **kwargs)
            self._record_guard_request(method_u, url, error_msg="")
            return res
        except Exception as exc:
            self._record_guard_request(method_u, url, error_msg=str(exc))
            raise

    def get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._request("POST", url, **kwargs)

    def daily_limit_summary(self):
        self._ensure_daily_limit_slot()
        state = dict(self._daily_limit_state or {})
        return {
            "date": str(state.get("date", "")),
            "requests": int(state.get("requests", 0) or 0),
            "writes": int(state.get("writes", 0) or 0),
            "request_cap": int(self.daily_request_cap),
            "write_cap": int(self.daily_write_cap),
            "state_file": str(self.daily_limit_state_file or ""),
        }

    def close(self):
        if self._guard_closed:
            return
        self._guard_closed = True
        try:
            if self._traffic_guard_enabled:
                ended_at = datetime.now()
                elapsed = max(0.0, (ended_at - self._guard_started_at).total_seconds())
                self._save_guard_report(
                    "postflight",
                    {
                        "preflight": dict(self._guard_preflight or {}),
                        "postflight": self.daily_limit_summary(),
                        "finished_at": ended_at.isoformat(timespec="seconds"),
                        "duration_sec": round(elapsed, 3),
                        "cleanup": {"session_closed": True, "lock_release_attempted": True},
                    },
                )
        finally:
            try:
                self.session.close()
            except Exception:
                pass
            if self._traffic_guard_enabled:
                self._release_traffic_guard_lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _write_url(self):
        return f"{self.site_url}/bbs/write.php?bo_table={self.board_slug}"

    def _login_url(self):
        return f"{self.site_url}/bbs/login.php"

    def _board_list_url(self):
        return f"{self.site_url}/bbs/board.php?bo_table={self.board_slug}"

    def _extract_board_wr_id(self, url):
        src = str(url or "").strip()
        if not src:
            return 0
        m = re.search(r"[?&]wr_id=(\d+)", src)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return 0
        m2 = re.search(rf"/{re.escape(self.board_slug)}/(\d+)(?:$|[/?#])", src)
        if m2:
            try:
                return int(m2.group(1))
            except ValueError:
                return 0
        return 0

    def _discover_latest_board_post_url(self, subject_hint=""):
        try:
            res = self.get(self._board_list_url(), timeout=20)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            items = []
            for a in soup.select("td.td_subject a[href]"):
                href = str(a.get("href", "")).strip()
                if not href:
                    continue
                abs_url = urljoin(res.url, href)
                if (f"/{self.board_slug}/" not in abs_url) and (f"bo_table={self.board_slug}" not in abs_url):
                    continue
                title = " ".join(a.get_text(" ", strip=True).split())
                items.append((title, abs_url))
            if not items:
                return ""
            needle = str(subject_hint or "").strip()
            if needle:
                for title, abs_url in items:
                    if needle in title:
                        return abs_url
            return items[0][1]
        except Exception:
            return ""

    def _find_form(self, soup):
        forms = soup.select("form")
        if not forms:
            return None
        for form in forms:
            if form.select_one("input[name='wr_subject']") or form.select_one("textarea[name='wr_content']"):
                return form
        return forms[0]

    def _find_input_name(self, form, candidates, input_type=None):
        for name in candidates:
            if form.select_one(f"input[name='{name}']"):
                return name
        if input_type:
            tag = form.select_one(f"input[type='{input_type}'][name]")
            if tag:
                return tag.get("name")
        return None

    def _collect_form_defaults(self, form):
        payload = {}

        def _put(name, value):
            if name not in payload:
                payload[name] = value
                return
            prev = payload.get(name)
            if isinstance(prev, list):
                prev.append(value)
                payload[name] = prev
            else:
                payload[name] = [prev, value]

        checkable_names = set()
        for inp in form.select("input[name]"):
            name = inp.get("name")
            if not name:
                continue
            typ = (inp.get("type") or "text").lower()
            if typ in {"checkbox", "radio"}:
                checkable_names.add(name)

        for inp in form.select("input[name]"):
            name = inp.get("name")
            if not name:
                continue
            typ = (inp.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "reset", "file"}:
                continue
            if typ == "hidden" and name in checkable_names:
                # Keep checked checkbox/radio values only for duplicated names.
                # Some G5 skins add a hidden fallback value before notice/fix checkboxes;
                # posting both can flip fixed/notice state unexpectedly on edit submit.
                continue
            if typ in {"checkbox", "radio"} and not inp.has_attr("checked"):
                continue
            _put(name, inp.get("value", ""))

        for sel in form.select("select[name]"):
            name = sel.get("name")
            selected_opts = sel.select("option[selected]")
            chosen = ""
            if selected_opts:
                # Some legacy forms mark both blank and real option as selected.
                # Prefer the last non-empty selected value.
                for opt in selected_opts:
                    val = str(opt.get("value", "")).strip()
                    if val:
                        chosen = val
                if not chosen:
                    chosen = str(selected_opts[-1].get("value", "")).strip()
            else:
                opt = sel.select_one("option")
                chosen = str(opt.get("value", "")).strip() if opt else ""
            _put(name, chosen)

        for ta in form.select("textarea[name]"):
            name = ta.get("name")
            _put(name, ta.text or "")

        return payload

    def _has_write_permission(self):
        write_url = self._write_url()
        res = self.get(write_url, timeout=20)
        if res.status_code != 200:
            return False
        if "html.gethompy.com/503.html" in str(res.url) or "일일 데이터 전송량 초과안내" in str(res.text):
            return False
        text = res.text
        if "글을 쓸 권한이 없습니다" in text:
            return False
        soup = BeautifulSoup(text, "html.parser")
        form = self._find_form(soup)
        if not form:
            return False
        has_subject = bool(form.select_one("input[name='wr_subject']"))
        has_content = bool(form.select_one("textarea[name='wr_content']"))
        return has_subject and has_content

    def login(self):
        if not self.admin_id or not self.admin_pw:
            raise ValueError("ADMIN_ID/ADMIN_PW 미설정: .env에 사이트 로그인 정보를 설정하세요.")

        params = {"url": f"/bbs/write.php?bo_table={self.board_slug}"}
        res = self.get(self._login_url(), params=params, timeout=20)
        res.raise_for_status()
        if "html.gethompy.com/503.html" in str(res.url) or "일일 데이터 전송량 초과안내" in str(res.text):
            raise RuntimeError("호스팅 트래픽 초과(일일 데이터 전송량 초과)로 로그인 불가")

        soup = BeautifulSoup(res.text, "html.parser")
        form = soup.select_one("form#flogin, form[name*='login'], form[action*='login_check']")
        if not form:
            if self._has_write_permission():
                return True
            raise RuntimeError("로그인 폼을 찾지 못했습니다.")

        action = form.get("action") or "/bbs/login_check.php"
        action_url = urljoin(res.url, action)
        payload = self._collect_form_defaults(form)

        id_name = self._find_input_name(form, ["mb_id", "login_id", "id", "user_id"], input_type="text")
        pw_name = self._find_input_name(form, ["mb_password", "password", "pw", "user_pw"], input_type="password")

        if not id_name or not pw_name:
            raise RuntimeError("로그인 폼 필드를 찾지 못했습니다.")

        payload[id_name] = self.admin_id
        payload[pw_name] = self.admin_pw

        post_res = self.post(
            action_url,
            data=payload,
            headers={"Referer": res.url},
            allow_redirects=True,
            timeout=20,
        )
        post_res.raise_for_status()

        if not self._has_write_permission():
            alert = _safe_alert_text(post_res.text)
            detail = f" ({alert})" if alert else ""
            raise RuntimeError(f"사이트 로그인 실패 또는 글쓰기 권한 없음{detail}")

        return True

    def _get_write_form(self, wr_id=None):
        if wr_id is None:
            write_url = self._write_url()
        else:
            write_url = f"{self.site_url}/bbs/write.php?bo_table={self.board_slug}&w=u&wr_id={int(wr_id)}"
        res = self.get(write_url, timeout=20)
        res.raise_for_status()

        if "글을 쓸 권한이 없습니다" in res.text:
            alert = _safe_alert_text(res.text)
            detail = f" ({alert})" if alert else ""
            raise RuntimeError(f"글쓰기 권한이 없습니다{detail}")

        soup = BeautifulSoup(res.text, "html.parser")
        form = self._find_form(soup)
        if not form:
            raise RuntimeError("글쓰기 폼을 찾지 못했습니다.")

        action = form.get("action") or "/bbs/write_update.php"
        action_url = urljoin(res.url, action)
        defaults = self._collect_form_defaults(form)
        self._last_write_url = res.url
        # Listing schema guard is only valid for MNA listing board.
        if SCHEMA_GUARD_ENABLED and str(self.board_slug).strip() == str(MNA_BOARD_SLUG).strip():
            ok, reason = _validate_seoul_write_form_schema(
                res.text,
                context=f"{'edit' if wr_id is not None else 'write'}:{self.board_slug}",
            )
            _schema_guard("seoul_write_form", ok, reason, sample=res.text[:500])
        return action_url, defaults, form, res.text

    def _submit_write(self, action_url, payload, referer=None, validate_memo=False):
        if validate_memo and isinstance(payload, dict) and "wr_20" in payload:
            ok, diag = _validate_admin_memo_format(payload.get("wr_20", ""), require_br=bool(ADMIN_MEMO_REQUIRE_BR))
            if not ok:
                raise ValueError(
                    "관리자메모 포맷 오류: "
                    + ",".join(diag.get("errors", []))
                    + f" (uid={diag.get('uid','')}, url={diag.get('url','')})"
                )

        res = self.post(
            action_url,
            data=payload,
            headers={"Referer": referer or self._last_write_url or self._write_url()},
            allow_redirects=True,
            timeout=25,
        )
        res.raise_for_status()

        alert = _safe_alert_text(res.text)
        hard_fail_tokens = ["권한", "오류", "실패", "존재하지", "금지", "차단", "토큰 에러"]
        if alert and any(token in alert for token in hard_fail_tokens):
            raise RuntimeError(alert)

        final_url = res.url
        m = re.search(r"document\.location(?:\.replace)?\((['\"])(.*?)\1\)", res.text)
        if m:
            final_url = urljoin(res.url, m.group(2))
        return {"url": final_url, "alert": alert}

    def publish_listing(self, item):
        action_url, payload, form, form_html = self._get_write_form()
        updates = _build_mna_payload_updates(item, form, form_html, payload)
        subject = str(updates.get("wr_subject", "")).strip()

        payload["bo_table"] = self.board_slug
        payload.update(updates)

        if "wr_name" in payload and not str(payload.get("wr_name", "")).strip():
            payload["wr_name"] = MY_COMPANY_NAME

        submit = self._submit_write(action_url, payload, validate_memo=True)

        return {
            "subject": subject,
            "url": submit.get("url", ""),
            "alert": submit.get("alert", ""),
        }

    def get_edit_payload(self, wr_id):
        action_url, defaults, form, form_html = self._get_write_form(wr_id=wr_id)
        return action_url, defaults, form, form_html

    def update_listing(self, wr_id, item):
        action_url, payload, form, form_html = self._get_write_form(wr_id=wr_id)
        updates = _build_mna_payload_updates(item, form, form_html, payload, status_label=None)
        subject = str(updates.get("wr_subject", payload.get("wr_subject", ""))).strip()
        payload["bo_table"] = self.board_slug
        payload.update(updates)
        submit = self._submit_write(action_url, payload, validate_memo=True)
        return {"subject": subject, "url": submit.get("url", ""), "alert": submit.get("alert", "")}

    def set_listing_status(self, wr_id, status_label):
        action_url, payload, form, _ = self._get_write_form(wr_id=wr_id)
        status_map = _select_label_value_map(form, "wr_17")
        status_val = _select_value_from_text(status_map, status_label)
        if not status_val:
            raise ValueError(f"상태값 매핑 실패: {status_label}")
        current = str(payload.get("wr_17", "")).strip()
        if current == status_val:
            return {"subject": str(payload.get("wr_subject", "")).strip(), "url": f"{self.site_url}/mna/{int(wr_id)}", "alert": "already_set"}
        payload["bo_table"] = self.board_slug
        payload["wr_17"] = status_val
        submit = self._submit_write(action_url, payload, validate_memo=False)
        return {"subject": str(payload.get("wr_subject", "")).strip(), "url": submit.get("url", ""), "alert": submit.get("alert", "")}

    def submit_edit_updates(self, action_url, payload, updates):
        post_payload = dict(payload or {})
        post_payload["bo_table"] = self.board_slug
        post_payload.update(dict(updates or {}))
        need_validate_memo = isinstance(updates, dict) and ("wr_20" in updates)
        return self._submit_write(action_url, post_payload, validate_memo=need_validate_memo)

    def publish_custom_html(self, subject, html_content, wr_id=None, link1=""):
        target_wr_id = int(wr_id or 0)
        if target_wr_id > 0:
            action_url, payload, _form, _form_html = self._get_write_form(wr_id=target_wr_id)
        else:
            action_url, payload, _form, _form_html = self._get_write_form()

        post_payload = dict(payload or {})
        post_payload["bo_table"] = self.board_slug
        post_payload["wr_subject"] = str(subject or "").strip()
        post_payload["wr_content"] = str(html_content or "")
        post_payload["html"] = "html1"
        if "wr_name" in post_payload and not str(post_payload.get("wr_name", "")).strip():
            post_payload["wr_name"] = MY_COMPANY_NAME
        if link1 and "wr_link1" in post_payload and not str(post_payload.get("wr_link1", "")).strip():
            post_payload["wr_link1"] = str(link1 or "").strip()

        submit = self._submit_write(action_url, post_payload, validate_memo=False)
        final_url = str(submit.get("url", "")).strip()
        if target_wr_id > 0 and (not final_url or "/bbs/write.php?bo_table=" in final_url):
            final_url = f"{self.site_url}/{self.board_slug}/{int(target_wr_id)}"
        if target_wr_id <= 0 and (not final_url or "/bbs/write.php?bo_table=" in final_url):
            discovered = self._discover_latest_board_post_url(subject_hint=post_payload.get("wr_subject", ""))
            if discovered:
                final_url = str(discovered).strip()
        out_wr_id = int(target_wr_id or 0)
        if out_wr_id <= 0:
            out_wr_id = self._extract_board_wr_id(final_url)
        return {
            "subject": str(post_payload.get("wr_subject", "")).strip(),
            "url": final_url,
            "alert": submit.get("alert", ""),
            "mode": "update" if target_wr_id > 0 else "create",
            "wr_id": int(out_wr_id or 0),
        }


def _normalize_sync_status_label(status_label):
    s = _compact_text(status_label)
    if s in {"가능", "보류", "완료"}:
        return s
    if "완료" in s:
        return "완료"
    if "보류" in s:
        return "보류"
    return "가능"


def _detect_defer_request_reason(*texts):
    patterns = list(DEFER_REQUEST_PATTERNS or [])
    if not patterns:
        return ""
    merged = " ".join(_compact_text(x).lower() for x in texts if _compact_text(x))
    if not merged:
        return ""
    for token in patterns:
        if token and token in merged:
            return token
    return ""


def _enqueue_deferred_requeue(uid, wr_id, reason, source_status=""):
    uid_txt = str(uid or "").strip()
    if not uid_txt:
        return
    path = str(DEFER_QUEUE_FILE or "").strip()
    if not path:
        return
    payload = _load_json_file(path, default={}) or {}
    rows = list(payload.get("items", []) or [])
    row = {
        "uid": uid_txt,
        "wr_id": int(wr_id or 0),
        "reason": _compact_text(reason),
        "source_status": _compact_text(source_status),
        "queued_at": datetime.now().isoformat(timespec="seconds"),
        "retry_after": (datetime.now() + timedelta(days=7)).isoformat(timespec="seconds"),
    }
    rows = [x for x in rows if str((x or {}).get("uid", "")).strip() != uid_txt]
    rows.append(row)
    payload["items"] = rows
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_json_file(path, payload)


def _sheet_rows_equal(old_row, new_row):
    for idx, val in enumerate(list(new_row or [])):
        old_val = old_row[idx] if idx < len(old_row or []) else ""
        if _normalize_compare_text(old_val) != _normalize_compare_text(val):
            return False
    return True


def _reconcile_sheet_sync(worksheet, runtime, uid, status_label, item=None, dry_run=False, row_no_override=None):
    uid = str(uid or "").strip()
    if not uid:
        return {"action": "skip_no_uid", "uid": uid}

    status_label = _normalize_sync_status_label(status_label)
    uid_to_row = runtime.get("uid_to_row", {})
    all_values = runtime.get("all_values", [])
    row_idx = uid_to_row.get(uid)

    if item is None:
        if not row_idx:
            return {"action": "skip_no_row", "uid": uid}
        old_row = all_values[row_idx - 1] if (row_idx - 1) < len(all_values) else []
        before_row = list(old_row or [])
        old_no = _row_text(old_row, 0)
        old_status = _normalize_sync_status_label(_row_text(old_row, 1))
        row_no = _resolve_sheet_row_no(
            old_no=old_no,
            row_no_override=row_no_override,
            fallback_no=int(runtime.get("last_no", 0)) + 1,
            allocate_if_missing=False,
        )
        after_row = list(before_row)
        while len(after_row) < 2:
            after_row.append("")
        after_row[0] = row_no
        after_row[1] = status_label
        row_no_changed = _normalize_compare_text(old_no) != _normalize_compare_text(row_no)
        status_changed = old_status != status_label
        if not status_changed and not row_no_changed:
            return {
                "action": "same",
                "uid": uid,
                "row_idx": row_idx,
                "row_no": row_no,
                "before_status": old_status,
                "after_status": status_label,
                "before_row": before_row,
                "after_row": list(before_row),
            }
        if not dry_run:
            cell = f"A{row_idx}:B{row_idx}"
            try:
                worksheet.update(values=[[row_no, status_label]], range_name=cell)
            except TypeError:
                worksheet.update(cell, [[row_no, status_label]])
        if (row_idx - 1) < len(all_values):
            all_values[row_idx - 1] = list(after_row)
        alignment_change = "status_only"
        if row_no_changed and status_changed:
            alignment_change = "row_no_and_status"
        elif row_no_changed:
            alignment_change = "row_no_only"
        return {
            "action": "status_only",
            "alignment_change": alignment_change,
            "uid": uid,
            "row_idx": row_idx,
            "row_no": row_no,
            "status": status_label,
            "before_status": old_status,
            "after_status": status_label,
            "row_no_changed": row_no_changed,
            "status_changed": status_changed,
            "before_row": before_row,
            "after_row": after_row,
            "before_exists": True,
        }

    if row_idx:
        old_row = all_values[row_idx - 1] if (row_idx - 1) < len(all_values) else []
        before_row = list(old_row or [])
        old_no = _row_text(old_row, 0)
        row_no = _resolve_sheet_row_no(
            old_no=old_no,
            row_no_override=row_no_override,
            fallback_no=int(runtime.get("last_no", 0)) + 1,
            allocate_if_missing=False,
        )
        new_row = _build_sheet_row(
            item,
            row_no=row_no,
            status_label=status_label,
            old_memo=_row_text(old_row, 31),
            keep_display_col=_row_text(old_row, 35),
            keep_subject_col=_row_text(old_row, 36),
        )
        if _sheet_rows_equal(old_row, new_row):
            return {
                "action": "same",
                "uid": uid,
                "row_idx": row_idx,
                "row_no": row_no,
                "before_row": before_row,
                "after_row": list(before_row),
                "before_exists": True,
            }
        if not dry_run:
            cell = f"A{row_idx}"
            try:
                worksheet.update(values=[new_row], range_name=cell)
            except TypeError:
                worksheet.update(cell, [new_row])
        if (row_idx - 1) < len(all_values):
            all_values[row_idx - 1] = list(new_row)
        return {
            "action": "updated",
            "uid": uid,
            "row_idx": row_idx,
            "row_no": row_no,
            "before_row": before_row,
            "after_row": list(new_row),
            "before_exists": True,
        }

    row_no = _resolve_sheet_row_no(
        old_no="",
        row_no_override=row_no_override,
        fallback_no=int(runtime.get("last_no", 0)) + 1,
        allocate_if_missing=False,
    )
    row_idx = max(2, int(runtime.get("last_row", 1)) + 1)
    new_row = _build_sheet_row(item, row_no=row_no, status_label=status_label, keep_display_col="", keep_subject_col="")
    if not dry_run:
        cell = f"A{row_idx}"
        try:
            worksheet.update(values=[new_row], range_name=cell)
        except TypeError:
            worksheet.update(cell, [new_row])

    while len(all_values) < row_idx:
        all_values.append([])
    all_values[row_idx - 1] = list(new_row)
    uid_to_row[uid] = row_idx
    row_no_num = _sheet_no_to_int(row_no)
    if row_no_num > int(runtime.get("last_no", 0) or 0):
        runtime["last_no"] = row_no_num
    runtime["last_row"] = row_idx
    return {
        "action": "appended",
        "uid": uid,
        "row_idx": row_idx,
        "row_no": row_no,
        "before_row": [],
        "after_row": list(new_row),
        "before_exists": False,
    }


def _sheet_row_from_runtime(runtime, uid):
    rt = dict(runtime or {})
    uid_key = str(uid or "").strip()
    if not uid_key:
        return []
    uid_to_row = dict(rt.get("uid_to_row", {}))
    row_idx = uid_to_row.get(uid_key)
    if not isinstance(row_idx, int) or row_idx <= 1:
        return []
    all_values = list(rt.get("all_values", []) or [])
    if (row_idx - 1) < len(all_values):
        return list(all_values[row_idx - 1] or [])
    return []


def _sanitize_credit_display_col(value):
    txt = str(value or "").strip()
    if not txt:
        return ""
    # AJ(신용 등급 표시)에는 가격/협의 문구를 쓰지 않는다.
    price_markers = ("협의", "억", "만", "~", "/")
    if any(marker in txt for marker in price_markers):
        return ""
    return txt


def _sanitize_credit_subject_col(value):
    txt = _compact_text(value)
    if not txt:
        return ""
    txt = txt.replace("⭐", "").replace("★", "").replace("🌟", "").strip()
    if not txt:
        return ""
    # AK(신용 주체)에는 가격/협의 문구를 쓰지 않는다.
    if any(marker in txt for marker in ("협의", "억", "만", "~")):
        return ""
    return txt


def _extract_credit_subject_candidates(item, reviewed_memo):
    subject_candidates = []
    for raw in (
        (item or {}).get("license", ""),
        (item or {}).get("claim_price", ""),
        (item or {}).get("price_trace_summary", ""),
        (item or {}).get("price_raw", ""),
        reviewed_memo,
        (item or {}).get("memo", ""),
    ):
        txt = str(raw or "")
        if not txt:
            continue
        for m in re.finditer(r"\(([^()]{2,40})\)", txt):
            cand = _compact_text(m.group(1))
            if not cand:
                continue
            low = cand.lower()
            if low in {"종합", "전문", "수정하세요", "삭제", "협의중"}:
                continue
            if any(token in cand for token in ("건설정보", "행정사", "법무", "컨설팅", "MNA", "mna")):
                subject_candidates.append(cand)
                continue
            if len(cand) >= 4 and not re.search(r"^\d+$", cand):
                subject_candidates.append(cand)
    return subject_candidates


def _build_credit_subject_col(item, reviewed_memo, keep_subject_col="", keep_display_col=""):
    uid = str((item or {}).get("uid", "")).strip()
    forced = _compact_text(CREDIT_SUBJECT_UID_OVERRIDES.get(uid, ""))
    if forced:
        return forced

    candidates = []

    keep_subject = _sanitize_credit_subject_col(keep_subject_col)
    if keep_subject:
        candidates.extend([x.strip() for x in keep_subject.split("/") if _compact_text(x)])

    keep_display = _sanitize_credit_display_col(keep_display_col)
    disp = keep_display.replace("⭐", "🌟").replace("★", "🌟").strip()
    if disp.startswith("🌟"):
        tail = _sanitize_credit_subject_col(disp.lstrip("🌟").strip())
        if tail:
            candidates.extend([x.strip() for x in tail.split("/") if _compact_text(x)])

    candidates.extend(_extract_credit_subject_candidates(item, reviewed_memo))

    if not candidates:
        return ""
    seen = set()
    uniq = []
    for cand in candidates:
        key = _normalize_compare_text(cand)
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(cand)
    return " / ".join(uniq[:2])


_CREDIT_GRADE_SCORE = {
    "AAA": 100,
    "AA+": 95,
    "AA": 94,
    "AA-": 93,
    "A+": 90,
    "A": 89,
    "A-": 88,
    "BBB+": 85,
    "BBB": 84,
    "BBB-": 83,
    "BB+": 80,
    "BB": 79,
    "BB-": 78,
    "B+": 72,
    "B": 71,
    "B-": 70,
    "CCC+": 64,
    "CCC": 63,
    "CCC-": 62,
    "CC": 55,
    "C": 50,
    "D": 0,
}

_CREDIT_GRADE_PATTERN = re.compile(
    r"(?<![A-Z])(AAA|AA[\+\-0]?|A[\+\-0]?|BBB[\+\-0]?|BB[\+\-0]?|B[\+\-0]?|CCC[\+\-0]?|CC|C|D)(?![A-Z])",
    flags=re.I,
)


def _normalize_credit_grade_token(token):
    t = _compact_text(token).upper().replace("＋", "+").replace("－", "-")
    if not t:
        return ""
    if t.endswith("0"):
        t = t[:-1]
    if t == "AAA+":
        t = "AAA"
    return t


def _iter_credit_grade_tokens(text):
    src = str(text or "")
    if not src:
        return []
    out = []
    for raw_line in _split_text_lines(src):
        line = str(raw_line or "").strip()
        norm = _compact_text(line)
        if not norm:
            continue
        upper_line = line.upper()
        is_context_line = any(key in norm for key in ("신용", "등급", "조합", "외부"))
        if not is_context_line:
            simple = _normalize_credit_grade_token(norm)
            if simple in _CREDIT_GRADE_SCORE:
                out.append(simple)
            continue
        for match in _CREDIT_GRADE_PATTERN.finditer(upper_line):
            token = _normalize_credit_grade_token(match.group(1))
            if token in _CREDIT_GRADE_SCORE:
                out.append(token)
    return out


def _has_bb_plus_or_higher_credit(text):
    threshold = _CREDIT_GRADE_SCORE.get("BB+", 80)
    for token in _iter_credit_grade_tokens(text):
        score = _CREDIT_GRADE_SCORE.get(token)
        if score is not None and score >= threshold:
            return True
    return False


def _build_credit_display_col(item, reviewed_memo, keep_display_col):
    prev = _sanitize_credit_display_col(keep_display_col)
    prev_norm = prev.replace("⭐", "🌟").replace("★", "🌟").strip()
    prev_has_star = prev_norm.startswith("🌟")
    src = [reviewed_memo, (item or {}).get("memo", ""), (item or {}).get("association", ""), prev]
    for key in ("external_credit", "ext_credit", "coop_credit", "association_credit"):
        src.append((item or {}).get(key, ""))
    merged = "\n".join(str(x or "") for x in src if _compact_text(x))
    has_star = prev_has_star or _has_bb_plus_or_higher_credit(merged)
    if not has_star:
        return ""
    return "🌟"


def _build_sheet_row(item, row_no, status_label="가능", old_memo="", keep_display_col="", keep_subject_col=""):
    status_label = _normalize_sync_status_label(status_label)
    uid = str((item or {}).get("uid", "")).strip()
    reviewed_memo = _review_memo_typo_for_sheet(uid, (item or {}).get("memo", ""))
    if _compact_text(old_memo):
        reviewed_memo = _merge_sheet_memo_preserve_credit(old_memo, reviewed_memo)
    credit_display_col = _build_credit_display_col(item, reviewed_memo, keep_display_col)
    credit_subject_col = _build_credit_subject_col(item, reviewed_memo, keep_subject_col, keep_display_col)
    raw_license_lines = [x for x in _split_text_lines((item or {}).get("license", "")) if _compact_text(x)]
    generic_only_license = bool(raw_license_lines) and not bool(_filtered_display_licenses((item or {}).get("license", "")))
    display_license_lines = _display_license_lines((item or {}).get("license", ""))
    claim_price_text = _normalize_claim_price_for_sheet(
        (item or {}).get("claim_price", ""),
        uid=uid,
        licenses=", ".join(display_license_lines[:4]),
    )
    license_text = item.get("license", "")
    license_year_text = item.get("license_year", "")
    specialty_text = item.get("specialty", "")
    y20_text = item.get("y20", "")
    y21_text = item.get("y21", "")
    y22_text = item.get("y22", "")
    y23_text = item.get("y23", "")
    y24_text = item.get("y24", "")
    y25_text = item.get("y25", "")
    if generic_only_license:
        license_year_text = ""
        specialty_text = ""
        y20_text = ""
        y21_text = ""
        y22_text = ""
        y23_text = ""
        y24_text = ""
        y25_text = ""
    public_price_text = "협의"
    return [
        row_no,
        status_label,
        license_text,
        license_year_text,
        specialty_text,
        y20_text,
        y21_text,
        y22_text,
        y23_text,
        y24_text,
        "",
        "",
        y25_text,
        item.get("founded_year", ""),
        str(item.get("shares", "")).replace("좌", ""),
        item.get("company_type", ""),
        item.get("location", ""),
        str(item.get("balance", "")).replace("만", ""),
        public_price_text,
        item.get("capital", ""),
        item.get("association", ""),
        item.get("debt_ratio", ""),
        "",
        item.get("liquidity_ratio", ""),
        "",
        "",
        "",
        "",
        "",
        "",
        item.get("surplus", ""),
        reviewed_memo,
        MY_COMPANY_NAME,
        claim_price_text,
        str(item.get("uid", "")),
        credit_display_col,
        credit_subject_col,
        item.get("price_trace_summary", "") or item.get("price_raw", ""),
        item.get("price_source", ""),
        item.get("price_evidence", ""),
        item.get("price_confidence", ""),
        item.get("price_fallback", ""),
    ]


def _sheet_basis_from_row(row):
    src = list(row or [])
    return {
        "sheet_price": _row_text(src, 18),
        "sheet_claim_price": _row_text(src, 33),
    }


def _apply_sheet_basis_to_item(item, row):
    out = dict(item or {})
    basis = _sheet_basis_from_row(row)
    for key, val in basis.items():
        clean = _compact_text(val)
        if clean:
            out[key] = clean
    return out


def _load_sheet_basis_map(uid_filter=None):
    uid_set = {str(x).strip() for x in (uid_filter or []) if str(x).strip()}
    out = {}
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    client = gspread.authorize(creds)
    ws = client.open(SHEET_NAME).sheet1
    values = ws.get_all_values()
    for row in values[1:]:
        uid = ""
        for idx in (34, 33, 32):
            cand = extract_id_strict(_row_text(row, idx))
            if cand:
                uid = cand
                break
        if not uid:
            continue
        if uid_set and uid not in uid_set:
            continue
        out[uid] = _sheet_basis_from_row(row)
    return out


def _detect_sheet_row_jump(all_values):
    total_rows = len(all_values or [])
    anchors = []
    orphans = []

    for idx, row in enumerate(list(all_values or [])[1:], start=2):
        if _is_listing_anchor_row(row):
            anchors.append(idx)
        elif any(_compact_text(cell) for cell in list(row or [])):
            orphans.append(idx)

    gaps = []
    for prev, cur in zip(anchors, anchors[1:]):
        if cur - prev > 1:
            gaps.append({"from": prev, "to": cur, "gap": cur - prev - 1})

    max_gap = max([g["gap"] for g in gaps], default=0)
    has_risk = bool(orphans) or max_gap >= 200
    return {
        "total_rows": total_rows,
        "anchor_count": len(anchors),
        "orphan_count": len(orphans),
        "first_anchor_row": anchors[0] if anchors else 0,
        "last_anchor_row": anchors[-1] if anchors else 0,
        "orphans_head": orphans[:30],
        "orphans_tail": orphans[-30:],
        "gaps": gaps[:50],
        "max_gap": int(max_gap),
        "has_risk": bool(has_risk),
    }


def _log_sheet_row_jump_watchdog(report, context=""):
    payload = dict(report or {})
    payload["context"] = str(context or "")
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = str(SHEET_ROW_JUMP_WATCHDOG_FILE or "").strip()
    if not path:
        return
    try:
        _ensure_parent_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _assert_sheet_row_watchdog(all_values, context="", allow_risk=False):
    report = _detect_sheet_row_jump(all_values)
    _log_sheet_row_jump_watchdog(report, context=context)
    if report.get("has_risk") and (not allow_risk) and SHEET_ROW_JUMP_ABORT_ON_RISK:
        raise RuntimeError(
            "시트 행 점프 위험 감지: "
            f"anchors={report.get('anchor_count',0)}, "
            f"orphans={report.get('orphan_count',0)}, "
            f"max_gap={report.get('max_gap',0)} "
            f"(watchdog={SHEET_ROW_JUMP_WATCHDOG_FILE})"
        )
    return report


def _analyze_sheet_rows(all_values):
    real_last_row = 1
    last_my_number = 0
    existing_web_ids = {}

    if len(all_values) > 1:
        for idx, row in enumerate(all_values):
            if idx == 0:
                continue

            if _is_listing_anchor_row(row):
                real_last_row = idx + 1

            num = _sheet_no_to_int(_row_text(row, 0))
            if num > last_my_number:
                last_my_number = num

            found_id = _extract_sheet_uid_from_row(row)
            if found_id:
                existing_web_ids[found_id] = idx + 1

    return {
        "real_last_row": real_last_row,
        "last_my_number": last_my_number,
        "existing_web_ids": existing_web_ids,
    }


def _build_sheet_no_uid_map(all_values):
    out = {}
    if len(all_values) <= 1:
        return out
    for row in all_values[1:]:
        no = _sheet_no_to_int(_row_text(row, 0))
        if no <= 0:
            continue
        uid = _extract_sheet_uid_from_row(row)
        if uid:
            out[no] = uid
    return out


def _extract_item_from_detail_link(driver, link):
    origin_uid = str(link).split("uid=")[1].split("&")[0]
    driver.get(link)
    time.sleep(1)
    if SCHEMA_GUARD_ENABLED:
        page_html = driver.page_source or ""
        ok, reason = _validate_nowmna_detail_schema(page_html, uid=origin_uid)
        _schema_guard("nowmna_detail", ok, reason, sample=page_html[:500])

    l_lic, l_yr, l_sp = [], [], []
    l_20, l_21, l_22, l_23, l_24, l_25 = [], [], [], [], [], []

    try:
        tbl = None
        candidates = driver.find_elements(
            By.XPATH,
            "//table[(.//*[contains(text(), '면허년도')]) or ((.//*[contains(text(), '2020')]) and (.//*[contains(text(), '2024')]))]",
        )
        for cand in candidates:
            if len(cand.find_elements(By.TAG_NAME, "tr")) >= 2:
                tbl = cand
                break
        if tbl is None:
            raise RuntimeError("sales_table_not_found")
        col_map = {
            "license": 0,
            "year": 1,
            "specialty": 2,
            "y20": 3,
            "y21": 4,
            "y22": 5,
            "y23": 6,
            "y24": 7,
            "y25": 8,
        }

        for r in tbl.find_elements(By.TAG_NAME, "tr"):
            cs = r.find_elements(By.XPATH, "./th|./td")
            if len(cs) < 2:
                continue

            cell_texts = [clean_text_save(c.text) for c in cs]
            header_hit = sum(1 for txt in cell_texts if ("업종" in txt or "면허" in txt or re.search(r"20\d{2}", txt)))
            if header_hit >= 2:
                col_map = _build_nowmna_sales_col_map(cell_texts)
                continue

            def _cell(idx_key):
                idx = int(col_map.get(idx_key, -1) or -1)
                if idx < 0 or idx >= len(cs):
                    return ""
                return clean_text_save(cs[idx].text)

            txt_lic = _cell("license")
            if not txt_lic or "업종" in txt_lic or "면허" in txt_lic:
                continue

            converted_name = normalize_license(txt_lic)
            row_year = _cell("year")
            row_sp = _cell("specialty")
            row_y20 = _cell("y20")
            row_y21 = _cell("y21")
            row_y22 = _cell("y22")
            row_y23 = _cell("y23")
            row_y24 = _cell("y24")
            row_y25 = _cell("y25")

            if not any(
                _compact_text(v)
                for v in (converted_name, row_year, row_sp, row_y20, row_y21, row_y22, row_y23, row_y24, row_y25)
            ):
                continue

            l_lic.append(converted_name)
            l_yr.append(row_year)
            l_sp.append(row_sp)
            l_20.append(row_y20)
            l_21.append(row_y21)
            l_22.append(row_y22)
            l_23.append(row_y23)
            l_24.append(row_y24)
            l_25.append(row_y25)
    except Exception:
        pass

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        fallback_rows = _extract_nowmna_sales_rows_from_body_text(body_text)
        existing_license_keys = {
            _normalize_license_key(raw)
            for raw in l_lic
            if _normalize_license_key(raw)
        }
        for row in fallback_rows:
            row_license = _compact_text(row.get("license", ""))
            row_key = _normalize_license_key(row_license)
            if not row_key or row_key in existing_license_keys:
                continue
            existing_license_keys.add(row_key)
            l_lic.append(row_license)
            l_yr.append(_compact_text(row.get("year", "")))
            l_sp.append(_compact_text(row.get("specialty", "")))
            l_20.append(_compact_text(row.get("y20", "")))
            l_21.append(_compact_text(row.get("y21", "")))
            l_22.append(_compact_text(row.get("y22", "")))
            l_23.append(_compact_text(row.get("y23", "")))
            l_24.append(_compact_text(row.get("y24", "")))
            l_25.append(_compact_text(row.get("y25", "")))
    except Exception:
        pass

    loc = get_value_by_label(driver, ["소재지"])
    price_raw = get_value_by_label(driver, ["양도가", "매매가", "최종 양도가", "최종가"])
    claim_price = get_value_by_label(driver, ["청구 양도가", "청구가", "양도가 범위", "범위값", "가격범위", "청구 양도가/범위값"])
    comp = get_value_by_label(driver, ["회사형태"])
    found_dt = get_value_by_label(driver, ["법인설립일", "법인년도"]).replace("년", "")
    cap = get_value_by_label(driver, ["자본금"]).replace("억", "")
    assoc = get_value_by_label(driver, ["협회가입", "협회"])
    debt = get_value_by_label(driver, ["부채비율"])
    liq = get_value_by_label(driver, ["유동비율"])
    surplus = get_value_by_label(driver, ["잉여금"])
    shares_raw = get_value_by_label(driver, ["출자좌수", "좌수", "공제조합출자좌수"])
    bal_raw = get_value_by_label(driver, ["대출후남은잔액", "잔액"])
    shares_raw, bal_raw = _normalize_shares_balance(shares_raw, bal_raw)

    memo = get_value_by_label(driver, ["비고", "특이사항"])
    if not memo:
        try:
            memo = driver.find_element(By.XPATH, "//div[contains(@class, 'view_memo')]").text
        except Exception:
            pass
    memo_license_lines = _extract_license_lines_from_text(memo)
    primary_has_only_generic = bool([x for x in l_lic if _compact_text(x)]) and not bool(_filtered_display_licenses(l_lic))
    if memo_license_lines and (not primary_has_only_generic):
        l_lic = _merge_license_lines(l_lic, memo_license_lines) or list(l_lic)

    f_lic = _join_lines_preserve_alignment(l_lic)
    f_yr = _join_lines_preserve_alignment(l_yr)
    f_sp = _join_lines_preserve_alignment(l_sp)

    y20 = _join_lines_preserve_alignment(l_20)
    y21 = _join_lines_preserve_alignment(l_21)
    y22 = _join_lines_preserve_alignment(l_22)
    y23 = _join_lines_preserve_alignment(l_23)
    y24 = _join_lines_preserve_alignment(l_24)
    y25 = _join_lines_preserve_alignment(l_25)

    price_trace = resolve_yangdo_price_trace(price_raw, claim_price, memo)
    price = price_trace["price"]
    if price != (price_raw or "").strip():
        print(
            "      [가격보정] "
            f"UID {origin_uid}: normalized='{price}' "
            f"(source={price_trace['source']}, confidence={price_trace['confidence']}, "
            f"claim_present={'Y' if _compact_text(claim_price) else 'N'})"
        )

    item = {
        "uid": str(origin_uid),
        "source_url": link,
        "license": f_lic,
        "license_year": f_yr,
        "specialty": f_sp,
        "y20": y20,
        "y21": y21,
        "y22": y22,
        "y23": y23,
        "y24": y24,
        "y25": y25,
        "location": loc,
        "price": price,
        "price_trace_summary": _build_price_trace_summary(price_trace, price_raw, claim_price),
        "claim_price": claim_price,
        "price_source": price_trace["source"],
        "price_evidence": price_trace["evidence"],
        "price_confidence": price_trace["confidence"],
        "price_fallback": price_trace["fallback_used"],
        "company_type": comp,
        "founded_year": found_dt,
        "capital": cap,
        "association": assoc,
        "debt_ratio": debt,
        "liquidity_ratio": liq,
        "surplus": surplus,
        "shares": shares_raw,
        "balance": bal_raw,
        "memo": memo,
    }
    return item


def _upsert_item_to_sheet(worksheet, all_values, item, status_label="가능", row_no_override=None):
    context = _analyze_sheet_rows(all_values)
    existing_web_ids = context["existing_web_ids"]
    uid = str(item.get("uid", "")).strip()
    if not uid:
        raise ValueError("uid 누락: 시트 반영 불가")
    status_label = _normalize_sync_status_label(status_label)

    update_row_idx = existing_web_ids.get(uid)
    if isinstance(update_row_idx, int) and update_row_idx > 1:
        old_row = all_values[update_row_idx - 1] if (update_row_idx - 1) < len(all_values) else []
        old_no = _row_text(old_row, 0) if old_row else ""
        row_no = _resolve_sheet_row_no(
            old_no=old_no,
            row_no_override=row_no_override,
            fallback_no=context["last_my_number"] + 1,
            allocate_if_missing=False,
        )
        old_memo = _row_text(old_row, 31)
        old_claim_price = _row_text(old_row, 33)
        ok_item, item_issues = _validate_item_for_sheet(item, old_claim_price)
        if not ok_item and (status_label != "완료"):
            return {"action": "skipped_invalid", "row_idx": 0, "row_no": 0, "issues": list(item_issues)}
        item_for_update = dict(item or {})
        # --uid 재수집 시 원본 페이지에 청구양도가가 비어 있더라도
        # 기존 시트 AH(청구양도가)를 지우지 않도록 보존한다.
        if (not _compact_text(item_for_update.get("claim_price", ""))) and _compact_text(old_claim_price):
            item_for_update["claim_price"] = old_claim_price
        row_values = _build_sheet_row(
            item_for_update,
            row_no,
            status_label=status_label,
            old_memo=old_memo,
            keep_display_col=_row_text(old_row, 35),
            keep_subject_col=_row_text(old_row, 36),
        )
        cell = f"A{update_row_idx}"
        try:
            worksheet.update(values=[row_values], range_name=cell)
        except TypeError:
            worksheet.update(cell, [row_values])
        return {"action": "updated", "row_idx": update_row_idx, "row_no": row_no}

    ok_item, item_issues = _validate_item_for_sheet(item)
    if not ok_item and (status_label != "완료"):
        return {"action": "skipped_invalid", "row_idx": 0, "row_no": 0, "issues": list(item_issues)}

    insert_row_idx = context["real_last_row"] + 1
    row_no = _resolve_sheet_row_no(
        old_no="",
        row_no_override=row_no_override,
        fallback_no=context["last_my_number"] + 1,
        allocate_if_missing=False,
    )
    row_values = _build_sheet_row(item, row_no, status_label=status_label, keep_display_col="", keep_subject_col="")
    cell = f"A{insert_row_idx}"
    try:
        worksheet.update(values=[row_values], range_name=cell)
    except TypeError:
        worksheet.update(cell, [row_values])
    return {"action": "appended", "row_idx": insert_row_idx, "row_no": row_no}


def _extract_source_uid_from_text(text):
    src = str(text or "")
    m = re.search(r"[?&]uid=(\d{3,8})", src, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"\bUID\s*[:#]?\s*(\d{3,8})\b", src, flags=re.I)
    if m:
        return m.group(1)
    return ""


def _extract_uid_from_admin_memo(memo_text):
    src = str(memo_text or "")
    m = re.search(r"UID\s*(\d{4,6})", src, flags=re.I)
    if m:
        return m.group(1)
    for line in _split_text_lines(src):
        if "http" in line.lower():
            continue
        m2 = re.match(r"^\s*(\d{4,6})(?:\s|$)", line)
        if m2:
            return m2.group(1)
    fallback = _extract_source_uid_from_text(src)
    if fallback:
        return fallback
    return ""


def _extract_license_hint_from_admin_memo(memo_text, uid):
    src_uid = str(uid or "").strip()
    for line in _split_text_lines(memo_text):
        norm = _compact_text(line)
        if not norm.upper().startswith("UID "):
            continue
        if src_uid:
            m = re.match(rf"UID\s*{re.escape(src_uid)}\s*(.*)$", norm, flags=re.I)
            if m:
                return _compact_text(m.group(1))
        m2 = re.match(r"UID\s*\d{4,6}\s*(.*)$", norm, flags=re.I)
        if m2:
            return _compact_text(m2.group(1))
    return ""


def _extract_nowmna_url_hint(memo_text, payload, uid):
    payload_src = dict(payload or {})
    for key in ("wr_link1", "wr_link2"):
        cand = _compact_text(payload_src.get(key, ""))
        if cand and _is_allowed_nowmna_url(cand):
            return cand
    urls = re.findall(r"https?://[^\s<>'\"]+", str(memo_text or ""))
    for url in urls:
        if _is_allowed_nowmna_url(url):
            return _compact_text(url)
    uid_key = str(uid or "").strip()
    if uid_key:
        return _safe_nowmna_detail_link(uid_key)
    return ""


def _build_admin_memo_from_sheet_basis(uid, current_memo, payload, sheet_basis):
    basis = dict(sheet_basis or {})
    memo = str(current_memo or "")
    uid_key = str(uid or "").strip()
    item = {
        "uid": uid_key,
        "license": _extract_license_hint_from_admin_memo(memo, uid_key),
        "source_url": _extract_nowmna_url_hint(memo, payload, uid_key),
        "sheet_price": _compact_text(basis.get("sheet_price", "")),
        "sheet_claim_price": _normalize_multiline_text(basis.get("sheet_claim_price", "")),
    }
    return _build_mna_admin_memo(item)


def _is_togun_scope_text(text):
    src = re.sub(r"\s+", "", _compact_text(text)).lower()
    if not src:
        return False
    if "토건" in src or "토목건축" in src:
        return True
    return ("토목" in src) and ("건축" in src)


def _resolve_admin_memo_scope_text(uid, current_memo, payload):
    uid_key = str(uid or "").strip()
    payload_src = dict(payload or {})
    parts = [
        _extract_license_hint_from_admin_memo(current_memo, uid_key),
        _compact_text(payload_src.get("wr_6", "")),
        _compact_text(payload_src.get("wr_subject", "")),
        _compact_text(payload_src.get("ca_name", "")),
    ]
    return " ".join([p for p in parts if p]).strip()


def _extract_seoul_wr_ids_from_html(html):
    out = []
    seen = set()
    for m in re.finditer(r"/mna/(\d{1,9})", str(html or "")):
        wr_id = int(m.group(1))
        if wr_id in seen:
            continue
        seen.add(wr_id)
        out.append(wr_id)
    return out


def _extract_max_page_from_mna_html(html):
    max_page = 1
    for m in re.finditer(r"[?&]page=(\d+)", str(html or ""), flags=re.I):
        try:
            max_page = max(max_page, int(m.group(1)))
        except Exception:
            continue
    return max_page


def _collect_seoul_wr_ids(session, max_pages=0, delay_sec=0.0, resume_wr_id=0):
    base_url = f"{SITE_URL}/mna"
    out = []
    seen = set()
    scanned_pages = 0
    resume_wr_id = max(0, int(resume_wr_id or 0))

    first = session.get(base_url, timeout=20)
    first.raise_for_status()
    first_ids = _extract_seoul_wr_ids_from_html(first.text)
    detected_max = _extract_max_page_from_mna_html(first.text)
    latest_wr_id = max(first_ids) if first_ids else 0
    page_size_guess = max(1, len(first_ids) or 40)
    scan_start_page = 1
    if resume_wr_id > 0 and latest_wr_id > resume_wr_id:
        approx_page = int((latest_wr_id - resume_wr_id) / page_size_guess) + 1
        scan_start_page = max(1, approx_page - 2)

    if scan_start_page <= 1:
        scanned_pages = 1
        for wid in first_ids:
            if wid in seen:
                continue
            seen.add(wid)
            out.append(wid)

    if max_pages > 0:
        total_pages = max(scan_start_page, max_pages)
    elif detected_max > 1:
        total_pages = max(scan_start_page, detected_max)
    else:
        total_pages = max(scan_start_page, 1000)

    no_new_streak = 0
    loop_start = 2 if scan_start_page <= 1 else scan_start_page
    for page in range(loop_start, total_pages + 1):
        page_url = f"{base_url}?page={page}"
        try:
            res = session.get(page_url, timeout=20)
            res.raise_for_status()
        except Exception:
            continue
        scanned_pages = page
        ids = _extract_seoul_wr_ids_from_html(res.text)
        added = 0
        for wid in ids:
            if wid in seen:
                continue
            seen.add(wid)
            out.append(wid)
            added += 1

        if added == 0:
            no_new_streak += 1
        else:
            no_new_streak = 0

        if max_pages <= 0 and detected_max <= 1 and page >= 5 and no_new_streak >= 3:
            break

        if delay_sec > 0:
            time.sleep(delay_sec)

    return out, scanned_pages


def _build_admin_memo_fix_traffic_plan(limit_info, target_count, dry_run=False, request_buffer=80, write_buffer=8):
    req_used = int(limit_info.get("requests", 0) or 0)
    write_used = int(limit_info.get("writes", 0) or 0)
    req_cap = int(limit_info.get("request_cap", 0) or 0)
    write_cap = int(limit_info.get("write_cap", 0) or 0)

    req_remaining = max(0, req_cap - req_used)
    write_remaining = max(0, write_cap - write_used)
    fixed_login_req = 2
    per_target_req = 1
    per_target_write = 0 if dry_run else 1

    usable_req = max(0, req_remaining - max(0, int(request_buffer)) - fixed_login_req)
    req_limit = usable_req // max(1, per_target_req)

    if per_target_write <= 0:
        write_limit = int(target_count)
    else:
        usable_write = max(0, write_remaining - max(0, int(write_buffer)))
        write_limit = usable_write // per_target_write

    safe_limit = max(0, min(int(target_count), int(req_limit), int(write_limit)))
    return {
        "targets": int(target_count),
        "mode": "dry-run" if dry_run else "apply",
        "request_buffer": max(0, int(request_buffer)),
        "write_buffer": max(0, int(write_buffer)),
        "fixed_login_req": fixed_login_req,
        "per_target_req": per_target_req,
        "per_target_write": per_target_write,
        "req_remaining": req_remaining,
        "write_remaining": write_remaining,
        "req_limit": int(req_limit),
        "write_limit": int(write_limit),
        "safe_limit": int(safe_limit),
    }


def _print_admin_memo_fix_traffic_plan(limit_info, plan):
    print("📋 관리자메모 트래픽 사전계획:")
    print(
        "   - 일일상태: "
        f"요청 {limit_info['requests']}/{limit_info['request_cap']} "
        f"수정 {limit_info['writes']}/{limit_info['write_cap']}"
    )
    print(
        "   - 추정치: "
        f"fixed_login_req={plan['fixed_login_req']} "
        f"per_target_req={plan['per_target_req']} "
        f"per_target_write={plan['per_target_write']}"
    )
    print(
        "   - 버퍼반영한도: "
        f"req_limit={plan['req_limit']} write_limit={plan['write_limit']}"
    )
    print(f"   - 이번 실행 안전 상한: {plan['safe_limit']} / {plan['targets']}")


def _load_admin_memo_fix_state(path, expected_signature):
    base = {
        "signature": str(expected_signature or ""),
        "processed_wr_ids": set(),
        "last_success_wr_id": 0,
        "updated_at": "",
    }
    target = str(path or "").strip()
    if not target or not os.path.exists(target):
        return base
    try:
        with open(target, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return base
        if str(raw.get("signature", "")).strip() != str(expected_signature or "").strip():
            return base
        processed = set()
        for token in list(raw.get("processed_wr_ids", []) or []):
            txt = str(token).strip()
            if txt.isdigit():
                processed.add(int(txt))
        base["processed_wr_ids"] = processed
        last_wr = str(raw.get("last_success_wr_id", "")).strip()
        base["last_success_wr_id"] = int(last_wr) if last_wr.isdigit() else 0
        base["updated_at"] = str(raw.get("updated_at", "")).strip()
        return base
    except Exception:
        return base


def _save_admin_memo_fix_state(path, signature, processed_wr_ids, last_success_wr_id=0):
    target = str(path or "").strip()
    if not target:
        return
    try:
        _ensure_parent_dir(target)
        payload = {
            "signature": str(signature or ""),
            "processed_wr_ids": sorted({int(x) for x in (processed_wr_ids or set())}),
            "count": len(set(processed_wr_ids or set())),
            "last_success_wr_id": int(last_success_wr_id or 0),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def run_fix_admin_memo(
    max_pages=0,
    limit=0,
    dry_run=False,
    include_non_raw=False,
    togun_only=False,
    license_filter="",
    delay_sec=0.0,
    request_buffer=80,
    write_buffer=8,
    plan_only=False,
    state_file="logs/admin_memo_sync_state.json",
    reset_state=False,
):
    max_pages = max(0, int(max_pages or 0))
    limit = max(0, int(limit or 0))
    delay_sec = max(0.0, float(delay_sec or 0.0))
    request_buffer = max(0, int(request_buffer or 0))
    write_buffer = max(0, int(write_buffer or 0))
    state_file = str(state_file or "").strip()
    license_filter_norm = re.sub(r"\s+", "", _compact_text(license_filter)).lower()
    state_signature = (
        "admin-memo-v2"
        f"|include_non_raw={1 if include_non_raw else 0}"
        "|memo_br=1"
        f"|togun_only={1 if togun_only else 0}"
        f"|license_filter={license_filter_norm}"
    )

    probe = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, "", "")
    probe_limit_info = probe.daily_limit_summary()
    if plan_only:
        if int(limit or 0) > 0:
            planned_targets = int(limit or 0)
        elif max_pages > 0:
            planned_targets = max_pages * 40
        else:
            planned_targets = 999999
        processed_count = 0
        if state_file and (not dry_run):
            state = _load_admin_memo_fix_state(state_file, state_signature)
            processed_count = len(set(state.get("processed_wr_ids", set()) or set()))
        plan = _build_admin_memo_fix_traffic_plan(
            limit_info=probe_limit_info,
            target_count=planned_targets,
            dry_run=bool(dry_run),
            request_buffer=request_buffer,
            write_buffer=write_buffer,
        )
        _print_admin_memo_fix_traffic_plan(probe_limit_info, plan)
        if processed_count > 0:
            print(f"↩️ 상태파일 누적 처리건: {processed_count}건 ({state_file})")
        print("✅ 계획 출력만 실행 완료 (네트워크 요청 없음)")
        print("   참고: 정확한 대상 수는 dry-run/apply 실행 시 집계됩니다.")
        return

    req_cap = int(probe_limit_info.get("request_cap", 0) or 0)
    req_used = int(probe_limit_info.get("requests", 0) or 0)
    write_cap = int(probe_limit_info.get("write_cap", 0) or 0)
    write_used = int(probe_limit_info.get("writes", 0) or 0)
    if req_cap > 0:
        req_remaining = max(0, req_cap - req_used)
        min_req_for_run = max(1, request_buffer) + 2  # login + 최소 동작 여유
        if req_remaining <= min_req_for_run:
            print(
                "⏸️ 관리자메모 교정 대기: 요청 상한 헤드룸 부족 "
                f"(remaining={req_remaining}, need>{min_req_for_run})"
            )
            return
    if (not dry_run) and write_cap > 0:
        write_remaining = max(0, write_cap - write_used)
        min_write_for_run = max(0, write_buffer) + 1
        if write_remaining <= min_write_for_run:
            print(
                "⏸️ 관리자메모 교정 대기: 수정 상한 헤드룸 부족 "
                f"(remaining={write_remaining}, need>{min_write_for_run})"
            )
            return

    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        print("❌ ADMIN_ID/ADMIN_PW 미설정: 관리자메모 교정을 실행할 수 없습니다.")
        return

    publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, admin_id, admin_pw)
    try:
        publisher.login()
    except Exception as e:
        print(f"❌ 사이트 로그인 실패: {e}")
        return
    limit_info = publisher.daily_limit_summary()
    print(
        f"🧮 일일 상한: 요청 {limit_info['requests']}/{limit_info['request_cap']} / "
        f"수정 {limit_info['writes']}/{limit_info['write_cap']} "
        f"(state={limit_info['state_file']})"
    )

    use_state = bool(state_file) and (not dry_run)
    processed_wr_ids = set()
    resume_wr_id = 0
    if use_state:
        if reset_state:
            _save_admin_memo_fix_state(state_file, state_signature, set(), last_success_wr_id=0)
            print(f"♻️ 관리자메모 상태 초기화: {state_file}")
        state = _load_admin_memo_fix_state(state_file, state_signature)
        processed_wr_ids = set(state.get("processed_wr_ids", set()) or set())
        resume_wr_id = int(state.get("last_success_wr_id", 0) or 0)
        if processed_wr_ids:
            print(f"↩️ 이전 실행 재개: 이미 처리된 WR {len(processed_wr_ids)}건")
        if resume_wr_id > 0:
            print(f"↩️ 번호 재개 커서: WR {resume_wr_id}부터 계속")

    print("📚 [메모교정1] seoul 게시글 목록 수집 중...")
    wr_ids, scanned_pages = _collect_seoul_wr_ids(
        publisher,
        max_pages=max_pages,
        delay_sec=0.0,
        resume_wr_id=resume_wr_id if use_state else 0,
    )
    wr_ids = sorted(set(wr_ids), reverse=True)
    if use_state and resume_wr_id > 0:
        wr_ids = [wid for wid in wr_ids if int(wid) <= int(resume_wr_id)]
    print(f"   게시글 {len(wr_ids)}건 (스캔 페이지 {scanned_pages})")
    if wr_ids:
        preview = ", ".join(str(x) for x in wr_ids[:5])
        suffix = " ..." if len(wr_ids) > 5 else ""
        print(f"   처리 순서: 최신 WR 우선 ({preview}{suffix})")
    if not wr_ids:
        print("✅ 교정 대상 게시글이 없습니다.")
        return

    last_success_wr_id = int(resume_wr_id or 0)

    def _mark_processed_state(wr_id):
        nonlocal last_success_wr_id
        if not use_state:
            return
        wid = int(wr_id or 0)
        if wid > 0:
            processed_wr_ids.add(wid)
            if last_success_wr_id <= 0 or wid < last_success_wr_id:
                last_success_wr_id = wid
        _save_admin_memo_fix_state(
            state_file,
            state_signature,
            processed_wr_ids,
            last_success_wr_id=last_success_wr_id,
        )

    remaining_wr_ids = sorted(
        (wid for wid in wr_ids if wid not in processed_wr_ids),
        reverse=True,
    )
    if use_state and not remaining_wr_ids:
        print("✅ 상태파일 기준 미처리 대상이 없습니다.")
        return

    plan = _build_admin_memo_fix_traffic_plan(
        limit_info=limit_info,
        target_count=len(remaining_wr_ids) if use_state else len(wr_ids),
        dry_run=bool(dry_run),
        request_buffer=request_buffer,
        write_buffer=write_buffer,
    )
    _print_admin_memo_fix_traffic_plan(limit_info, plan)
    if plan_only:
        print("✅ 계획 출력만 실행(요청/수정 미실행)")
        return
    safe_limit = int(plan.get("safe_limit", 0) or 0)
    if safe_limit <= 0:
        print("⚠️ 안전 상한이 0건입니다. 버퍼/일일상한 확인 후 재실행하세요.")
        return
    if limit <= 0:
        limit = safe_limit
    elif limit > safe_limit:
        print(f"⚠️ 요청한 상한 {limit}건을 안전 상한 {safe_limit}건으로 조정합니다.")
        limit = safe_limit

    print("📄 [메모교정2] 시트 기준값 로드 중...")
    try:
        sheet_basis_map = _load_sheet_basis_map()
    except Exception as e:
        print(f"❌ 시트 로드 실패: {e}")
        return
    print(f"   시트 기준값 매핑 {len(sheet_basis_map)}건")
    if togun_only:
        print("   🎯 대상 필터: 토건/토목건축")
    elif license_filter_norm:
        print(f"   🎯 대상 필터: '{license_filter_norm}' 포함")

    stats = {
        "scanned": 0,
        "raw_candidates": 0,
        "updated": 0,
        "planned": 0,
        "same": 0,
        "skip_non_raw": 0,
        "skip_scope": 0,
        "skip_no_uid": 0,
        "skip_no_sheet": 0,
        "failed": 0,
        "stop_headroom": 0,
    }

    target_wr_ids = remaining_wr_ids if use_state else wr_ids
    if target_wr_ids:
        print(f"🚀 관리자메모 교정 시작: 최신 -> 과거 (첫 WR {target_wr_ids[0]})")
    for idx, wr_id in enumerate(target_wr_ids, start=1):
        if limit > 0 and (stats["updated"] + stats["planned"]) >= limit:
            print(f"⚠️ 메모 교정 상한 도달: {limit}건")
            break

        live = publisher.daily_limit_summary()
        req_stop = int(live.get("request_cap", 0) or 0) - max(1, request_buffer)
        if int(live.get("requests", 0) or 0) >= req_stop:
            stats["stop_headroom"] += 1
            print("⚠️ 요청 헤드룸 임계 도달 -> 중단")
            break
        if not dry_run:
            write_stop = int(live.get("write_cap", 0) or 0) - max(0, write_buffer)
            if int(live.get("writes", 0) or 0) >= write_stop:
                stats["stop_headroom"] += 1
                print("⚠️ 수정 헤드룸 임계 도달 -> 중단")
                break

        stats["scanned"] += 1
        try:
            action_url, payload, _form, _form_html = publisher.get_edit_payload(wr_id)
            current_memo = str(payload.get("wr_20", "") or "")

            uid = _extract_uid_from_admin_memo(current_memo)
            if not uid:
                view_url = f"{SITE_URL}/mna/{wr_id}"
                try:
                    view_res = publisher.get(view_url, timeout=20)
                    view_res.raise_for_status()
                    uid = _extract_source_uid_from_text(view_res.text)
                except Exception:
                    uid = ""

            if not uid:
                stats["skip_no_uid"] += 1
                print(f"   - [{idx}/{len(target_wr_ids)}] WR {wr_id}: UID 미식별 -> 스킵")
                if use_state:
                    _mark_processed_state(wr_id)
                continue

            scope_text = _resolve_admin_memo_scope_text(uid, current_memo, payload)
            if togun_only:
                if not _is_togun_scope_text(scope_text):
                    stats["skip_scope"] += 1
                    if use_state:
                        _mark_processed_state(wr_id)
                    continue
            elif license_filter_norm:
                scope_norm = re.sub(r"\s+", "", _compact_text(scope_text)).lower()
                if license_filter_norm not in scope_norm:
                    stats["skip_scope"] += 1
                    if use_state:
                        _mark_processed_state(wr_id)
                    continue

            is_raw_based = "원문양도가" in current_memo
            if is_raw_based:
                stats["raw_candidates"] += 1
            if (not include_non_raw) and (not is_raw_based):
                stats["skip_non_raw"] += 1
                if use_state:
                    _mark_processed_state(wr_id)
                continue

            basis = dict(sheet_basis_map.get(uid, {}) or {})
            if not basis:
                stats["skip_no_sheet"] += 1
                print(f"   - [{idx}/{len(target_wr_ids)}] WR {wr_id}/UID {uid}: 시트 기준값 없음 -> 스킵")
                if use_state:
                    _mark_processed_state(wr_id)
                continue

            new_memo = _build_admin_memo_from_sheet_basis(uid, current_memo, payload, basis)
            if _normalize_compare_text(current_memo) == _normalize_compare_text(new_memo):
                stats["same"] += 1
                if use_state:
                    _mark_processed_state(wr_id)
                continue

            if dry_run:
                stats["planned"] += 1
                print(f"   🧪 [{idx}/{len(target_wr_ids)}] WR {wr_id}/UID {uid}: 관리자메모 교정 예정")
            else:
                publisher.submit_edit_updates(action_url, payload, {"wr_20": new_memo})
                stats["updated"] += 1
                print(f"   ✅ [{idx}/{len(target_wr_ids)}] WR {wr_id}/UID {uid}: 관리자메모 교정 완료")

            if use_state:
                _mark_processed_state(wr_id)

            if delay_sec > 0:
                time.sleep(delay_sec)
        except Exception as e:
            stats["failed"] += 1
            print(f"   ❌ [{idx}/{len(target_wr_ids)}] WR {wr_id}: 교정 실패 ({e})")

    mode = "dry-run" if dry_run else "apply"
    remain_count = (
        len([wid for wid in wr_ids if wid not in processed_wr_ids])
        if use_state
        else max(0, len(target_wr_ids) - stats["scanned"])
    )
    print(
        f"\n✅ 관리자메모 교정 요약 ({mode}) -> "
        f"스캔 {stats['scanned']} / 원문기반후보 {stats['raw_candidates']} / "
        f"교정 {stats['updated']} / 예정 {stats['planned']} / 동일 {stats['same']} / "
        f"비원문스킵 {stats['skip_non_raw']} / 대상외스킵 {stats['skip_scope']} / UID없음 {stats['skip_no_uid']} / "
        f"시트값없음 {stats['skip_no_sheet']} / 실패 {stats['failed']} / "
        f"헤드룸중단 {stats['stop_headroom']}"
    )
    if use_state:
        print(
            f"🧾 상태파일: {state_file} (처리 {len(processed_wr_ids)}건, 잔여 {max(0, int(remain_count))}건)"
        )


def run_fix_admin_memo_uid(
    uid,
    dry_run=False,
    include_non_raw=True,
    max_pages=0,
    delay_sec=0.0,
):
    uid = str(uid or "").strip()
    if not uid or not uid.isdigit():
        print(f"❌ 잘못된 UID: {uid}")
        return

    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        print("❌ ADMIN_ID/ADMIN_PW 미설정: 관리자메모 교정을 실행할 수 없습니다.")
        return

    publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, admin_id, admin_pw)
    try:
        publisher.login()
    except Exception as e:
        print(f"❌ 사이트 로그인 실패: {e}")
        return

    print(f"🎯 UID 단건 관리자메모 교정 시작: uid={uid}")
    wr_ids, scanned_pages = _collect_seoul_wr_ids(publisher, max_pages=max_pages, delay_sec=0.0)
    wr_ids = sorted(set(wr_ids), reverse=True)
    print(f"   게시글 {len(wr_ids)}건 (스캔 페이지 {scanned_pages})")

    basis_map = _load_sheet_basis_map(uid_filter=[uid])
    basis = dict(basis_map.get(uid, {}) or {})
    if not basis:
        print(f"❌ 시트 기준값 없음: uid={uid}")
        return

    found = False
    for idx, wr_id in enumerate(wr_ids, start=1):
        try:
            action_url, payload, _form, _form_html = publisher.get_edit_payload(wr_id)
            current_memo = str(payload.get("wr_20", "") or "")
            found_uid = _extract_uid_from_admin_memo(current_memo)
            if not found_uid:
                view_url = f"{SITE_URL}/mna/{wr_id}"
                try:
                    view_res = publisher.get(view_url, timeout=20)
                    view_res.raise_for_status()
                    found_uid = _extract_source_uid_from_text(view_res.text)
                except Exception:
                    found_uid = ""
            if found_uid != uid:
                continue

            found = True
            is_raw_based = "원문양도가" in current_memo
            if (not include_non_raw) and (not is_raw_based):
                print(f"   - WR {wr_id}/UID {uid}: 원문기반 아님 -> 스킵")
                break

            new_memo = _build_admin_memo_from_sheet_basis(uid, current_memo, payload, basis)
            if _normalize_compare_text(current_memo) == _normalize_compare_text(new_memo):
                print(f"   ✅ WR {wr_id}/UID {uid}: 이미 최신 포맷")
                break

            if dry_run:
                print(f"   🧪 WR {wr_id}/UID {uid}: 교정 예정")
                print("   [before]")
                print(current_memo)
                print("   [after]")
                print(new_memo)
            else:
                publisher.submit_edit_updates(action_url, payload, {"wr_20": new_memo})
                print(f"   ✅ WR {wr_id}/UID {uid}: 관리자메모 교정 완료")
            break
        except Exception as e:
            print(f"   ❌ [{idx}/{len(wr_ids)}] WR {wr_id}: 처리 실패 ({e})")
            if delay_sec > 0:
                time.sleep(delay_sec)

    if not found:
        print(f"⚠️ UID {uid} 를 포함한 게시글을 찾지 못했습니다.")


def _map_nowmna_status_to_seoul(status_text, marker_srcs=None):
    text = _compact_text(status_text)
    markers = " ".join([str(x or "").lower() for x in (marker_srcs or [])])

    if "계약완료" in text or "완료" in text:
        return "완료"
    if "계약보류" in text or "계약 보류" in text or "보류" in text:
        return "보류"
    if "계약가능" in text or "계약 가능" in text or "진행중" in text or "계약중" in text:
        return "가능"

    if "c.gif" in markers:
        return "완료"
    if "b.gif" in markers:
        return "보류"
    if "a.gif" in markers or "d.gif" in markers:
        return "가능"

    return "가능"


def _collect_nowmna_uid_status_map(max_pages=0, delay_sec=0.0):
    pages_limit = max(1, int(max_pages or RECONCILE_NOWMNA_MAX_PAGES))
    uid_set = set()
    status_map = {}
    empty_streak = 0
    scanned_pages = 0

    for page in range(1, pages_limit + 1):
        list_url = f"{TARGET_URL}?page_no={page}"
        try:
            res = requests.get(list_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            res.raise_for_status()
        except Exception:
            continue

        res.encoding = "cp949"
        scanned_pages = page
        html = res.text
        if SCHEMA_GUARD_ENABLED:
            ok, reason = _validate_nowmna_list_schema(html, page_no=page)
            if _is_soft_empty_nowmna_list_page(ok, reason, page_no=page, html=html):
                _append_log_line(
                    SCHEMA_ALERT_LOG,
                    (
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t"
                        f"nowmna_list\tsoft-empty-pass\t{_compact_text(reason)}"
                    ),
                )
            else:
                _schema_guard("nowmna_list", ok, reason, sample=html[:500])
        soup = BeautifulSoup(html, "html.parser")
        page_uids = set()
        for tr in soup.select("tr"):
            tds = tr.select("td")
            if len(tds) < 2:
                continue
            uid = _compact_text(tds[0].get_text(" ", strip=True))
            if not uid.isdigit():
                continue
            page_uids.add(uid)
            marker_srcs = [img.get("src", "") for img in tds[1].select("img")]
            status_text = _compact_text(tds[1].get_text(" ", strip=True))
            status_map[uid] = _map_nowmna_status_to_seoul(status_text, marker_srcs)

        if not page_uids:
            for m in re.finditer(r"yangdo_view1\.php\?uid=(\d{3,8})", html, flags=re.I):
                uid = m.group(1)
                page_uids.add(uid)
                status_map.setdefault(uid, "가능")

        uid_set.update(page_uids)
        if page_uids:
            empty_streak = 0
        else:
            empty_streak += 1
            if page >= 5 and empty_streak >= 3:
                break

        if delay_sec > 0:
            time.sleep(delay_sec)

    return uid_set, status_map, scanned_pages


def _trim_trailing_empty(values):
    out = list(values or [])
    while out and not str(out[-1]).strip():
        out.pop()
    return out


def _normalize_compare_text(value):
    src = str(value or "")
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    src = re.sub(r"<br\s*/?>", "<br>", src, flags=re.I)
    src = re.sub(r"[ \t]+", " ", src)
    src = re.sub(r"\n{2,}", "\n", src)
    return src.strip()


def _normalize_compare_value(value):
    if isinstance(value, list):
        norm = [_normalize_compare_text(v) for v in value]
        return _trim_trailing_empty(norm)
    return _normalize_compare_text(value)


def _normalize_sales_compare_list(values, key=""):
    raw_list = values if isinstance(values, list) else [values]
    norm = []
    blank_tokens = {"", "-", "0", "0.0", "신규", "신규면허", "건축신규", "실적없음", "+", "없음"}
    for raw in raw_list:
        txt = _normalize_compare_text(raw)
        txt_no_comma = txt.replace(",", "")
        if txt_no_comma in blank_tokens:
            txt = ""
        elif key == "mp_money[]":
            num = _number_token(txt_no_comma)
            if num:
                try:
                    txt = str(int(float(num) + 0.5))
                except Exception:
                    txt = _trim_decimal(num)
            else:
                txt = txt_no_comma
        else:
            num = _number_token(txt_no_comma)
            if num:
                txt = _trim_decimal(num)
            else:
                txt = txt_no_comma
        norm.append(txt)
    return _trim_trailing_empty(norm)


SYNC_EXCLUDED_UPDATE_KEYS = {
    "wr_17",
    "wr_12",
    "wr_16",
    "wr_name",
    "wr_sang",
    "wr_p2",
    "html",
    "wr_link1",
    "chk2",
}


SALES_ARRAY_KEYS = (
    "mp_cate1[]",
    "mp_cate2[]",
    "mp_year[]",
    "mp_money[]",
    "mp_2020[]",
    "mp_2021[]",
    "mp_2022[]",
    "mp_2023[]",
    "mp_2024[]",
    "mp_2025[]",
)


def _coerce_payload_list(value):
    if isinstance(value, list):
        return list(value)
    if value is None:
        return []
    return [value]


def _merge_blank_sales_with_existing(updates, defaults):
    out = dict(updates or {})
    base = dict(defaults or {})
    row_structure_changed = False
    if ("mp_cate1[]" in out) and ("mp_cate2[]" in out):
        row_structure_changed = (
            _normalize_sales_compare_list(out.get("mp_cate1[]", []), key="mp_cate1[]")
            != _normalize_sales_compare_list(base.get("mp_cate1[]", []), key="mp_cate1[]")
        ) or (
            _normalize_sales_compare_list(out.get("mp_cate2[]", []), key="mp_cate2[]")
            != _normalize_sales_compare_list(base.get("mp_cate2[]", []), key="mp_cate2[]")
        )
    for key in SALES_ARRAY_KEYS:
        if key not in out:
            continue
        new_vals = _coerce_payload_list(out.get(key, []))
        old_vals = _coerce_payload_list(base.get(key, []))
        if not new_vals and not old_vals:
            continue
        if row_structure_changed:
            if key == "mp_year[]":
                out[key] = [_to_year_text(v) for v in new_vals]
            else:
                out[key] = list(new_vals)
            continue
        max_len = max(len(new_vals), len(old_vals))
        last_non_empty = -1
        for rev_idx in range(len(new_vals) - 1, -1, -1):
            if _compact_text(new_vals[rev_idx]):
                last_non_empty = rev_idx
                break
        merged = []
        for idx in range(max_len):
            new_val = new_vals[idx] if idx < len(new_vals) else ""
            old_val = old_vals[idx] if idx < len(old_vals) else ""
            if key == "mp_year[]":
                new_year = _to_year_text(new_val)
                old_year = _to_year_text(old_val)
                if new_year and old_year and new_year != old_year:
                    merged.append(old_year)
                elif new_year:
                    merged.append(new_year)
                elif old_year:
                    merged.append(old_year)
                else:
                    merged.append("")
                continue
            if _compact_text(new_val):
                merged.append(new_val)
                continue
            if idx < len(new_vals) and last_non_empty >= 0 and idx <= last_non_empty:
                # Keep explicit interior blanks from source to prevent row-shift carry-over.
                merged.append(new_val)
                continue
            merged.append(old_val if _compact_text(old_val) else new_val)
        merged = _trim_trailing_empty(merged)
        if merged != _trim_trailing_empty(new_vals):
            out[key] = merged
    return out


def _build_sync_updates(item, form, form_html, defaults):
    updates = _build_mna_payload_updates(item, form, form_html, defaults, status_label=None)
    updates = _merge_blank_sales_with_existing(updates, defaults)
    for key in SYNC_EXCLUDED_UPDATE_KEYS:
        updates.pop(key, None)
    return updates


def _diff_payload_updates(current_payload, target_updates):
    diffs = []
    for key, target_value in dict(target_updates or {}).items():
        current_value = current_payload.get(key, [] if isinstance(target_value, list) else "")
        if key in SALES_ARRAY_KEYS:
            current_cmp = _normalize_sales_compare_list(current_value, key=key)
            target_cmp = _normalize_sales_compare_list(target_value, key=key)
            if current_cmp != target_cmp:
                diffs.append(key)
            continue
        if isinstance(target_value, list):
            current_cmp = current_value if isinstance(current_value, list) else [current_value]
            target_cmp = target_value
        elif isinstance(current_value, list):
            current_cmp = current_value
            target_cmp = [target_value]
        else:
            current_cmp = current_value
            target_cmp = target_value

        if _normalize_compare_value(current_cmp) != _normalize_compare_value(target_cmp):
            diffs.append(key)
    return diffs


RECONCILE_SITE_AUDIT_KEYS = (
    "wr_subject",
    "wr_content",
    "wr_1",
    "wr_2",
    "wr_3",
    "wr_4",
    "wr_5",
    "wr_6",
    "wr_7",
    "wr_8",
    "wr_10",
    "wr_19",
    "wr_20",
    "wr_17",
    "mp_cate1[]",
    "mp_cate2[]",
    "mp_year[]",
    "mp_money[]",
    "mp_2020[]",
    "mp_2021[]",
    "mp_2022[]",
    "mp_2023[]",
    "mp_2024[]",
    "mp_2025[]",
)


def _copy_payload_value(value):
    if isinstance(value, list):
        return list(value)
    if value is None:
        return ""
    return str(value)


def _payload_subset(payload, keys=None):
    out = {}
    src = dict(payload or {})
    for key in (list(keys) if keys else src.keys()):
        if key not in src:
            continue
        out[key] = _copy_payload_value(src.get(key))
    return out


def _payload_after_updates(before_payload, updates):
    out = dict(before_payload or {})
    for key, value in dict(updates or {}).items():
        out[key] = _copy_payload_value(value)
    return out


def _payload_change_map(before_payload, after_payload):
    before = dict(before_payload or {})
    after = dict(after_payload or {})
    keys = sorted(set(before.keys()) | set(after.keys()))
    changes = {}
    for key in keys:
        b = before.get(key, "")
        a = after.get(key, "")
        if isinstance(b, list) and not isinstance(a, list):
            a_cmp = [a]
            b_cmp = b
        elif isinstance(a, list) and not isinstance(b, list):
            a_cmp = a
            b_cmp = [b]
        else:
            a_cmp = a
            b_cmp = b
        if _normalize_compare_value(b_cmp) == _normalize_compare_value(a_cmp):
            continue
        changes[key] = {"before": b, "after": a}
    return changes


def _sheet_row_change_map(before_row, after_row, header_row=None):
    before = list(before_row or [])
    after = list(after_row or [])
    if not before and not after:
        return {}
    max_len = max(len(before), len(after))
    changes = {}
    for idx in range(max_len):
        b = before[idx] if idx < len(before) else ""
        a = after[idx] if idx < len(after) else ""
        if _normalize_compare_text(b) == _normalize_compare_text(a):
            continue
        col_a1 = _col_to_a1(idx + 1)
        header = _row_text(header_row or [], idx)
        key = f"{col_a1}:{header}" if header else col_a1
        changes[key] = {"before": b, "after": a}
    return changes


def _new_reconcile_audit(mode, options):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return {
        "run_id": run_id,
        "mode": mode,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": "",
        "options": dict(options or {}),
        "stats": {},
        "entries": [],
    }


def _save_reconcile_audit(audit_obj):
    audit = dict(audit_obj or {})
    run_id = str(audit.get("run_id", "")).strip() or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    _ensure_parent_dir(os.path.join(RECONCILE_AUDIT_DIR, "dummy.txt"))
    os.makedirs(RECONCILE_AUDIT_DIR, exist_ok=True)

    json_path = os.path.join(RECONCILE_AUDIT_DIR, f"reconcile_{run_id}.json")
    md_path = os.path.join(RECONCILE_AUDIT_DIR, f"reconcile_{run_id}.md")
    csv_path = os.path.join(RECONCILE_AUDIT_DIR, f"reconcile_{run_id}.csv")
    latest_path = os.path.join(RECONCILE_AUDIT_DIR, "latest_reconcile_snapshot.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump({"latest_snapshot": json_path, "run_id": run_id}, f, ensure_ascii=False, indent=2)

    entries = list(audit.get("entries", []))
    csv_fields = [
        "wr_id",
        "uid",
        "source_status",
        "result",
        "site_action",
        "sheet_action",
        "site_keys",
        "sheet_changes",
        "message",
        "error",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in entries:
            writer.writerow(
                {
                    "wr_id": row.get("wr_id", ""),
                    "uid": row.get("uid", ""),
                    "source_status": row.get("source_status", ""),
                    "result": row.get("result", ""),
                    "site_action": row.get("site_action", ""),
                    "sheet_action": row.get("sheet_action", ""),
                    "site_keys": ",".join(row.get("site_changed_keys", []) or []),
                    "sheet_changes": len(row.get("sheet_changes", {}) or {}),
                    "message": row.get("message", ""),
                    "error": row.get("error", ""),
                }
            )

    stats = dict(audit.get("stats", {}))
    lines = [
        f"# Reconcile Report {run_id}",
        "",
        f"- 모드: `{audit.get('mode', '')}`",
        f"- 시작: `{audit.get('started_at', '')}`",
        f"- 종료: `{audit.get('finished_at', '')}`",
        f"- 총 항목: `{len(entries)}`",
        f"- 통계: `{json.dumps(stats, ensure_ascii=False)}`",
        "",
        "## 최근 변경",
        "",
    ]
    for row in entries[:50]:
        lines.append(
            f"- WR {row.get('wr_id', '')} / UID {row.get('uid', '')} / "
            f"결과={row.get('result', '')} / site={row.get('site_action', '')} / "
            f"sheet={row.get('sheet_action', '')} / "
            f"키={','.join(row.get('site_changed_keys', []) or [])}"
        )
    with open(md_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    return {"json": json_path, "md": md_path, "csv": csv_path, "latest": latest_path}


def _resolve_latest_reconcile_snapshot(snapshot_path=""):
    direct = str(snapshot_path or "").strip()
    if direct:
        return direct
    latest_path = os.path.join(RECONCILE_AUDIT_DIR, "latest_reconcile_snapshot.json")
    if not os.path.exists(latest_path):
        return ""
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("latest_snapshot", "")).strip()
    except Exception:
        return ""


def _parse_iso_local(ts_text):
    src = str(ts_text or "").strip()
    if not src:
        return None
    try:
        return datetime.fromisoformat(src)
    except Exception:
        return None


def _enter_reconcile_guard(force=False):
    lock_path = str(RECONCILE_LOCK_FILE or "").strip() or "logs/reconcile.lock"
    state_path = str(RECONCILE_RUN_STATE_FILE or "").strip() or "logs/reconcile_run_state.json"
    min_interval = max(0, int(RECONCILE_MIN_INTERVAL_SEC or 0))
    stale_sec = max(60, int(RECONCILE_LOCK_STALE_SEC or 7200))
    now = datetime.now()

    _ensure_parent_dir(lock_path)
    _ensure_parent_dir(state_path)

    if os.path.exists(lock_path):
        try:
            age = time.time() - os.path.getmtime(lock_path)
        except Exception:
            age = 0
        if age > stale_sec:
            try:
                os.remove(lock_path)
                print(f"⚠️ reconcile stale lock 제거: {lock_path} (age={int(age)}s)")
            except Exception:
                pass

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "pid": os.getpid(),
                    "started_at": now.isoformat(timespec="seconds"),
                    "force": bool(force),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except FileExistsError:
        print(f"⏭️ 대조 스킵: 이미 실행 중(lock={lock_path})")
        return None
    except Exception as e:
        print(f"❌ 대조 가드 실패: lock 생성 오류 ({e})")
        return None

    if (not force) and min_interval > 0:
        state = _load_json_file(state_path, default={}) or {}
        last_started = _parse_iso_local(state.get("last_started_at", ""))
        if last_started is not None:
            elapsed = (now - last_started).total_seconds()
            if elapsed < min_interval:
                remain = int(max(1, min_interval - elapsed))
                print(
                    f"⏭️ 대조 스킵: 최소 실행 간격({min_interval}s) 미충족 "
                    f"(남은 {remain}s, state={state_path})"
                )
                try:
                    os.remove(lock_path)
                except Exception:
                    pass
                return None

    run_state = _load_json_file(state_path, default={}) or {}
    run_state["last_started_at"] = now.isoformat(timespec="seconds")
    run_state["last_pid"] = os.getpid()
    run_state["last_force"] = bool(force)
    _save_json_file(state_path, run_state)
    return {"lock_path": lock_path, "state_path": state_path}


def _leave_reconcile_guard(guard_ctx):
    ctx = dict(guard_ctx or {})
    lock_path = str(ctx.get("lock_path", "")).strip()
    state_path = str(ctx.get("state_path", "")).strip()

    if state_path:
        run_state = _load_json_file(state_path, default={}) or {}
        run_state["last_finished_at"] = datetime.now().isoformat(timespec="seconds")
        _save_json_file(state_path, run_state)

    if lock_path and os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except Exception:
            pass


def _safe_nowmna_detail_link(uid):
    return f"http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1"


def _publish_to_site(items, allow_low_quality=False):
    if not items:
        print("✅ 업로드할 신규 매물이 없습니다.")
        return

    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()

    if not admin_id or not admin_pw:
        print("[skip] upload disabled because ADMIN_ID/ADMIN_PW is missing in .env")
        return

    state = _load_upload_state(UPLOAD_STATE_FILE)
    uploaded_uids = state.get("uploaded_uids", {})

    publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, admin_id, admin_pw)
    try:
        publisher.login()
    except Exception as e:
        print(f"❌ 사이트 로그인 실패: {e}")
        return
    limit_info = publisher.daily_limit_summary()
    print(
        f"🧮 일일 상한: 요청 {limit_info['requests']}/{limit_info['request_cap']} / "
        f"수정 {limit_info['writes']}/{limit_info['write_cap']} "
        f"(state={limit_info['state_file']})"
    )

    sheet_basis_map = {}
    try:
        target_uids = [str(it.get("uid", "")).strip() for it in items if str(it.get("uid", "")).strip()]
        sheet_basis_map = _load_sheet_basis_map(target_uids)
        if sheet_basis_map:
            print(f"   ℹ️ 시트 기준 메모 주입: {len(sheet_basis_map)}건")
    except Exception as e:
        print(f"   ⚠️ 시트 기준 메모 로드 실패(원본값 fallback): {e}")
        sheet_basis_map = {}

    enriched_items = []
    for src in items:
        item = dict(src or {})
        uid = str(item.get("uid", "")).strip()
        basis = sheet_basis_map.get(uid, {})
        if basis:
            item.update({k: v for k, v in basis.items() if _compact_text(v)})
        enriched_items.append(item)

    ordered_items = sorted(enriched_items, key=lambda x: _to_num_key(x.get("uid")))
    skipped = 0
    pending_items = []
    for item in ordered_items:
        uid = str(item.get("uid", "")).strip()
        if not uid:
            continue
        if uid in uploaded_uids:
            skipped += 1
            continue
        quality = _evaluate_listing_quality(item)
        item["_quality"] = quality
        if not quality.get("ok", False):
            _append_low_quality_queue(item, quality)
            msg = (
                f"   ⚠️ 저품질 후보 UID {uid}: score={quality.get('score',0)} "
                f"reasons={','.join(quality.get('reasons', []))} "
                f"recommended_images={quality.get('recommended_images', 0)}"
            )
            print(msg)
            if LISTING_QUALITY_GATE_STRICT and (not allow_low_quality):
                skipped += 1
                continue
        pending_items.append(item)

    if not pending_items:
        print(f"✅ 업로드할 신규 매물이 없습니다. (이미 업로드 스킵 {skipped}건)")
        return

    success = 0
    failed = 0
    batch_size = max(1, int(UPLOAD_MAX_PER_RUN))
    batch_no = 0

    while pending_items:
        batch_no += 1
        batch = pending_items[:batch_size]
        pending_items = pending_items[batch_size:]

        print(
            f"   ▶ 업로드 배치 {batch_no}: {len(batch)}건 "
            f"(남은 대기 {len(pending_items)}건)"
        )

        for item in batch:
            uid = str(item.get("uid", "")).strip()
            if not uid:
                continue

            try:
                quality = dict(item.get("_quality", {}) or {})
                if quality:
                    print(
                        f"   ℹ️ UID {uid} 품질점수={quality.get('score',0)} "
                        f"/ 권장이미지={quality.get('recommended_images', 0)}장"
                    )
                out = _resolve_publish_listing_result(
                    publisher,
                    item,
                    publisher.publish_listing(item),
                    max_pages=RECONCILE_SEOUL_MAX_PAGES,
                )
                uploaded_uids[uid] = {
                    "published_at": datetime.now().isoformat(timespec="seconds"),
                    "url": out.get("url", ""),
                    "subject": out.get("subject", ""),
                    "source_url": item.get("source_url", ""),
                }
                uid_num = int(uid) if str(uid).isdigit() else 0
                last_uid_num = int(state.get("last_uploaded_uid", 0) or 0)
                if uid_num > 0 and uid_num >= last_uid_num:
                    state["last_uploaded_uid"] = uid_num
                    state["last_uploaded_uid_text"] = str(uid)
                    state["last_uploaded_wr_id"] = int(_extract_site_wr_id(out.get("url", "")) or 0)
                    state["last_upload_success_at"] = datetime.now().isoformat(timespec="seconds")
                state["uploaded_uids"] = uploaded_uids
                _save_upload_state(UPLOAD_STATE_FILE, state)
                success += 1
                print(f"   ✅ 업로드 완료: UID {uid} -> {out.get('url', '')}")
                if UPLOAD_DELAY_SEC:
                    time.sleep(UPLOAD_DELAY_SEC)
            except Exception as e:
                failed += 1
                print(f"   ❌ 업로드 실패: UID {uid} ({e})")

        if not UPLOAD_AUTO_CONTINUE and pending_items:
            print(
                f"⚠️ 업로드 배치 상한({batch_size}) 도달: "
                f"남은 {len(pending_items)}건은 다음 실행에서 이어집니다."
            )
            break

    print(
        f"\n📤 업로드 요약 -> 성공 {success}건 / 스킵 {skipped}건 / 실패 {failed}건 "
        f"(state: {UPLOAD_STATE_FILE}, auto_continue={UPLOAD_AUTO_CONTINUE})"
    )


def run_scraper(upload_enabled=None, allow_sheet_jump=False, allow_low_quality_upload=False):
    if upload_enabled is None:
        upload_enabled = UPLOAD_ENABLED

    print("📂 [1] 구글 시트 ID 분석 중...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        worksheet = client.open(SHEET_NAME).sheet1
        all_values = worksheet.get_all_values()
        _ensure_price_trace_headers(worksheet, all_values)
        all_values = worksheet.get_all_values()
        watchdog = _assert_sheet_row_watchdog(
            all_values,
            context="run_scraper",
            allow_risk=bool(allow_sheet_jump),
        )
        if watchdog.get("has_risk"):
            print(
                "⚠️ 시트 행 점프 위험 감지: "
                f"orphans={watchdog.get('orphan_count',0)}, max_gap={watchdog.get('max_gap',0)} "
                f"(allow_sheet_jump={bool(allow_sheet_jump)})"
            )
    except Exception as e:
        print(f"❌ 시트 연결 실패: {e}")
        return

    sheet_ctx = _analyze_sheet_rows(all_values)
    real_last_row = sheet_ctx["real_last_row"]
    last_my_number = sheet_ctx["last_my_number"]
    existing_web_ids = sheet_ctx["existing_web_ids"]
    upload_state = _load_upload_state(UPLOAD_STATE_FILE)
    resume_uid_floor = _extract_last_uploaded_uid(upload_state)

    start_row_index = real_last_row + 1
    print(f"   👉 저장 시작 위치: {start_row_index}행")
    print(f"   👉 식별된 원본 ID: {len(existing_web_ids)}개")
    if resume_uid_floor > 0:
        print(f"   ↩️ 업로드 재개 기준 UID: {resume_uid_floor} 이후만 수집")

    print("\n🚀 [2] 웹사이트 스캔 시작...")
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    new_items_urls = []
    consecutive_dupes = 0
    resume_floor_hits = 0

    for page in range(1, SCAN_PAGES + 1):
        url = f"{TARGET_URL}?page_no={page}"
        print(f"   📖 {page}페이지...")
        driver.get(url)
        time.sleep(1)
        if SCHEMA_GUARD_ENABLED:
            ok, reason = _validate_nowmna_list_schema(driver.page_source or "", page_no=page)
            if _is_soft_empty_nowmna_list_page(
                ok,
                reason,
                page_no=page,
                html=(driver.page_source or ""),
            ):
                _append_log_line(
                    SCHEMA_ALERT_LOG,
                    (
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t"
                        f"nowmna_list_scraper\tsoft-empty-pass\t{_compact_text(reason)}"
                    ),
                )
            else:
                _schema_guard("nowmna_list_scraper", ok, reason, sample=(driver.page_source or "")[:500])

        rows = driver.find_elements(By.TAG_NAME, "tr")

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) <= 6:
                    continue

                uid = cols[0].text.strip()
                if not uid.isdigit():
                    continue

                uid_num = int(uid)
                if resume_uid_floor > 0 and uid_num <= resume_uid_floor:
                    resume_floor_hits += 1
                    if resume_floor_hits >= STOP_IF_DUPLICATE_COUNT:
                        print(f"\n⏭️ [재개중단] 마지막 업로드 성공 UID({resume_uid_floor}) 경계 도달.")
                        consecutive_dupes = STOP_IF_DUPLICATE_COUNT
                        break
                    continue

                if uid in existing_web_ids:
                    consecutive_dupes += 1
                    if consecutive_dupes >= STOP_IF_DUPLICATE_COUNT:
                        print(f"\n⛔ [종료] 기존 매물({uid}) 연속 발견됨.")
                        break
                    continue

                consecutive_dupes = 0
                full_link = f"http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1"

                if full_link in new_items_urls:
                    continue

                raw_lic = cols[2].text
                conv_lic = normalize_license(raw_lic)
                print(f"      [🚨신규] {uid}번 - {conv_lic}")

                new_items_urls.append(full_link)
                existing_web_ids[uid] = "Current_Session"
            except Exception:
                continue

        if consecutive_dupes >= STOP_IF_DUPLICATE_COUNT:
            break

    new_items_urls.reverse()

    if not new_items_urls:
        print("\n✅ 업데이트할 내역이 없습니다.")
        _safe_quit(driver)
        return

    print(f"\n🔎 최종 신규 매물: {len(new_items_urls)}개 -> 상세 수집 시작")

    collected_items = []
    collected_status = {}
    sheet_runtime = {
        "uid_to_row": dict(existing_web_ids),
        "all_values": all_values,
        "last_row": int(real_last_row),
        "last_no": int(last_my_number),
    }

    for link in new_items_urls:
        origin_uid = link.split("uid=")[1].split("&")[0]
        try:
            item = _extract_item_from_detail_link(driver, link)
            f_lic = str(item.get("license", "")).strip()
            ok_item, item_issues = _validate_item_for_sheet(item)
            status_label = _derive_sheet_status_for_new_item(item, item_issues)
            skip_site_publish = _should_skip_site_publish_for_item(item, status_label, item_issues)
            if skip_site_publish:
                sheet_out = _reconcile_sheet_sync(
                    worksheet=worksheet,
                    runtime=sheet_runtime,
                    uid=origin_uid,
                    status_label="완료",
                    item=item,
                    dry_run=False,
                    row_no_override="",
                )
                print(
                    f"   -> {origin_uid} 수집완료 ({f_lic or '-'}) / "
                    f"시트 완료처리 ({','.join(item_issues) if item_issues else 'status=완료'})"
                )
                continue

            collected_items.append(item)
            collected_status[origin_uid] = status_label
            print(f"   -> {origin_uid} 수집완료 ({f_lic})")

        except Exception as e:
            print(f"   ⚠️ 에러 ({link}): {e}")

    _safe_quit(driver)

    if upload_enabled:
        if collected_items:
            print("\n📤 [4] seoulmna.co.kr 업로드 시작...")
            _publish_to_site(
                collected_items,
                allow_low_quality=bool(allow_low_quality_upload),
            )
        else:
            print("\nℹ️ 업로드 대상 신규 매물 없음(시트 완료처리만 반영).")
    else:
        print("\nℹ️ 업로드 생략(--no-upload).")

    upload_state_after = _load_upload_state(UPLOAD_STATE_FILE) if upload_enabled else {}
    uploaded_uids_after = dict(upload_state_after.get("uploaded_uids", {}) or {}) if isinstance(upload_state_after, dict) else {}
    synced_count = 0
    for item in collected_items:
        uid = str(item.get("uid", "")).strip()
        if not uid:
            continue
        row_no_override = ""
        if upload_enabled:
            site_url = str((uploaded_uids_after.get(uid, {}) or {}).get("url", "")).strip()
            row_no_override = _extract_site_wr_id(site_url) or ""
        sheet_out = _reconcile_sheet_sync(
            worksheet=worksheet,
            runtime=sheet_runtime,
            uid=uid,
            status_label=collected_status.get(uid, "가능"),
            item=item,
            dry_run=False,
            row_no_override=row_no_override,
        )
        synced_count += 1
        print(
            f"   ✅ 시트 동기화: uid={uid} "
            f"row={sheet_out.get('row_idx', 0)} / 번호={sheet_out.get('row_no', '') or '-'}"
        )

    if (not collected_items) and (not new_items_urls):
        return
    if synced_count > 0:
        print(f"✅ 시트 동기화 완료: {synced_count}건")


def run_single_uid(uid, upload_enabled=None, allow_sheet_jump=False, allow_low_quality_upload=False):
    uid = str(uid or "").strip()
    if not uid or not uid.isdigit():
        print(f"❌ 잘못된 uid: '{uid}'")
        return

    if upload_enabled is None:
        upload_enabled = UPLOAD_ENABLED

    print(f"🎯 [UID 모드] 대상 등록번호: {uid}")
    print("📂 [1] 구글 시트 연결 중...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        worksheet = client.open(SHEET_NAME).sheet1
        all_values = worksheet.get_all_values()
        _ensure_price_trace_headers(worksheet, all_values)
        all_values = worksheet.get_all_values()
        watchdog = _assert_sheet_row_watchdog(
            all_values,
            context=f"run_single_uid:{uid}",
            allow_risk=bool(allow_sheet_jump),
        )
        if watchdog.get("has_risk"):
            print(
                "⚠️ 시트 행 점프 위험 감지: "
                f"orphans={watchdog.get('orphan_count',0)}, max_gap={watchdog.get('max_gap',0)} "
                f"(allow_sheet_jump={bool(allow_sheet_jump)})"
            )
    except Exception as e:
        print(f"❌ 시트 연결 실패: {e}")
        return

    print("🌐 [2] 원본 상세 수집 중...")
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    link = f"http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1"
    try:
        item = _extract_item_from_detail_link(driver, link)
    except Exception as e:
        _safe_quit(driver)
        print(f"❌ 상세 수집 실패(uid={uid}): {e}")
        return
    _safe_quit(driver)

    print(
        "   수집 결과: "
        f"면허={_compact_text(item.get('license', '')) or '-'} / "
        f"양도가={_compact_text(item.get('price', '')) or '-'} / "
        f"소재지={_compact_text(item.get('location', '')) or '-'}"
    )

    ok_item, item_issues = _validate_item_for_sheet(item)
    status_label = _derive_sheet_status_for_new_item(item, item_issues)
    skip_site_publish = _should_skip_site_publish_for_item(item, status_label, item_issues)
    row_no_override = ""

    if skip_site_publish:
        print(
            "ℹ️ 사이트 업로드 생략: "
            f"uid={uid} / reason={','.join(item_issues) if item_issues else 'status=완료'}"
        )
    elif upload_enabled:
        print("📤 [4] 사이트 업로드 진행...")
        _publish_to_site([item], allow_low_quality=bool(allow_low_quality_upload))
        upload_state_after = _load_upload_state(UPLOAD_STATE_FILE)
        uploaded_uids_after = (
            dict(upload_state_after.get("uploaded_uids", {}) or {})
            if isinstance(upload_state_after, dict)
            else {}
        )
        site_url = str((uploaded_uids_after.get(uid, {}) or {}).get("url", "")).strip()
        row_no_override = _extract_site_wr_id(site_url) or ""
    else:
        print("ℹ️ 사이트 업로드 생략(--no-upload).")

    print("🧾 [3] 26양도매물 시트 반영 중...")
    try:
        upsert = _upsert_item_to_sheet(
            worksheet,
            all_values,
            item,
            status_label=("완료" if skip_site_publish else status_label),
            row_no_override=row_no_override,
        )
        if upsert.get("action") == "skipped_invalid":
            print(f"❌ 시트 반영 중단(uid={uid}): {','.join(upsert.get('issues', []))}")
            return
        action_txt = "갱신" if upsert["action"] == "updated" else "추가"
        print(
            f"   ✅ 시트 {action_txt} 완료: "
            f"row={upsert['row_idx']} / 번호={upsert['row_no'] or '-'} / uid={uid}"
        )
    except Exception as e:
        print(f"❌ 시트 반영 실패: {e}")
        return


def run_reconcile_published(
    nowmna_max_pages=0,
    seoul_max_pages=0,
    max_updates=0,
    delay_sec=0.0,
    dry_run=False,
    status_only=False,
    audit_tag="",
    force_run=False,
    sheet_only=False,
    allow_sheet_jump=False,
):
    nowmna_max_pages = max(1, int(nowmna_max_pages or RECONCILE_NOWMNA_MAX_PAGES))
    seoul_max_pages = max(0, int(seoul_max_pages or RECONCILE_SEOUL_MAX_PAGES))
    max_updates = max(0, int(max_updates or RECONCILE_MAX_UPDATES))
    delay_sec = max(0.0, float(delay_sec if delay_sec > 0 else RECONCILE_DELAY_SEC))
    mode_text = "dry-run" if dry_run else "apply"
    audit = _new_reconcile_audit(
        mode=mode_text,
        options={
            "nowmna_max_pages": nowmna_max_pages,
            "seoul_max_pages": seoul_max_pages,
            "max_updates": max_updates,
            "delay_sec": delay_sec,
            "status_only": bool(status_only),
            "force_run": bool(force_run),
            "sheet_only": bool(sheet_only),
            "tag": str(audit_tag or "").strip(),
        },
    )
    guard_ctx = _enter_reconcile_guard(force=bool(force_run))
    if not guard_ctx:
        return
    atexit.register(_leave_reconcile_guard, guard_ctx)

    print("🔎 [대조1] nowmna 전체 UID/상태 수집 중...")
    nowmna_uids, nowmna_status_map, nowmna_pages = _collect_nowmna_uid_status_map(
        max_pages=nowmna_max_pages,
        delay_sec=0.0,
    )
    print(
        f"   nowmna UID: {len(nowmna_uids)}건 (스캔 페이지 {nowmna_pages}) / "
        f"상태매핑 {len(nowmna_status_map)}건"
    )
    if not nowmna_uids:
        print("❌ nowmna UID 수집 실패: 0건")
        _leave_reconcile_guard(guard_ctx)
        return

    worksheet = None
    sheet_no_uid = {}
    sheet_runtime = None
    sheet_header = []
    site_wr_authoritative = {}
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        worksheet = client.open(SHEET_NAME).sheet1
        all_values = worksheet.get_all_values()
        watchdog = _assert_sheet_row_watchdog(
            all_values,
            context="run_reconcile_published",
            allow_risk=bool(allow_sheet_jump),
        )
        if watchdog.get("has_risk"):
            print(
                "⚠️ 시트 행 점프 위험 감지: "
                f"orphans={watchdog.get('orphan_count',0)}, max_gap={watchdog.get('max_gap',0)}"
            )
        sheet_header = list(all_values[0]) if all_values else []
        sheet_ctx = _analyze_sheet_rows(all_values)
        sheet_no_uid = _build_sheet_no_uid_map(all_values)
        print(f"   시트 UID 매핑: {len(sheet_no_uid)}건 (번호->원본UID)")
        sheet_runtime = {
            "uid_to_row": dict(sheet_ctx.get("existing_web_ids", {})),
            "all_values": all_values,
            "last_row": int(sheet_ctx.get("real_last_row", 1)),
            "last_no": int(sheet_ctx.get("last_my_number", 0)),
        }
        site_wr_authoritative = dict(_seed_site_wr_map_from_upload_state() or {})
    except Exception as e:
        print(f"   ⚠️ 시트 UID 매핑 로드 실패: {e}")

    if worksheet is None or sheet_runtime is None:
        print("❌ 시트 로드 실패: nowmna↔시트 기준 대조를 진행할 수 없습니다.")
        _leave_reconcile_guard(guard_ctx)
        return

    print("🧾 [대조2] nowmna↔구글시트 기준 변경 UID 선별 중...")
    uid_to_row = dict(sheet_runtime.get("uid_to_row", {}))
    if not uid_to_row:
        print("✅ 시트에 UID 매핑이 없어 반영할 대상이 없습니다.")
        _leave_reconcile_guard(guard_ctx)
        return

    auth_admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    auth_admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if auth_admin_id and auth_admin_pw:
        unresolved_uids = sorted(
            [uid for uid in uid_to_row.keys() if str(uid or "").strip() and int(site_wr_authoritative.get(uid, 0) or 0) <= 0],
            key=lambda x: int(x) if str(x).isdigit() else 0,
        )
        if unresolved_uids:
            auth_publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, auth_admin_id, auth_admin_pw)
            try:
                auth_publisher.login()
                discovered, diag = _discover_site_wr_map_from_board(
                    auth_publisher,
                    unresolved_uids,
                    max_pages=seoul_max_pages,
                )
                for map_uid, wr_id in dict(discovered or {}).items():
                    wr_id_num = int(wr_id or 0)
                    if wr_id_num > 0:
                        site_wr_authoritative[str(map_uid)] = wr_id_num
                mapped = len([uid for uid in unresolved_uids if int(site_wr_authoritative.get(uid, 0) or 0) > 0])
                print(
                    f"   co.kr UID→WR 기준맵: 대상 {len(unresolved_uids)}건 / 매핑 {mapped}건 "
                    f"(pages={diag.get('scanned_pages', 0)}, wr_scan={diag.get('scanned_wr_ids', 0)})"
                )
            except Exception as e:
                print(f"   ⚠️ co.kr UID→WR 기준맵 로드 실패: {e}")
            finally:
                try:
                    auth_publisher.close()
                except Exception:
                    pass

    candidate_jobs = []
    prefetched_items = {}
    precheck_driver = None
    precheck_options = webdriver.ChromeOptions()
    probe_runtime = {
        "uid_to_row": dict(sheet_runtime.get("uid_to_row", {})),
        "all_values": [list(row or []) for row in list(sheet_runtime.get("all_values", []) or [])],
        "last_row": int(sheet_runtime.get("last_row", 1)),
        "last_no": int(sheet_runtime.get("last_no", 0)),
    }
    sorted_uid_rows = sorted(uid_to_row.items(), key=lambda kv: int(kv[1]) if str(kv[1]).isdigit() else 0)
    try:
        for uid, row_idx in sorted_uid_rows:
            uid = str(uid or "").strip()
            if not uid:
                continue
            row = _sheet_row_from_runtime(sheet_runtime, uid)
            wr_id_text = _row_text(row, 0)
            current_sheet_wr_id = _sheet_no_to_int(wr_id_text)
            deleted_on_source = uid not in nowmna_uids
            source_status = "완료" if deleted_on_source else str(nowmna_status_map.get(uid, "가능")).strip() or "가능"
            if source_status not in {"가능", "보류", "완료"}:
                source_status = "가능"
            site_wr_id = int(site_wr_authoritative.get(uid, 0) or 0)
            effective_wr_id = current_sheet_wr_id
            row_no_override = None
            if site_wr_id > 0:
                effective_wr_id = site_wr_id
                row_no_override = site_wr_id
            elif source_status == "완료":
                effective_wr_id = 0
                row_no_override = "__CLEAR__"

            item = None
            if not status_only and source_status != "완료":
                try:
                    if uid not in prefetched_items:
                        if precheck_driver is None:
                            precheck_driver = webdriver.Chrome(
                                service=Service(ChromeDriverManager().install()),
                                options=precheck_options,
                            )
                        source_link = _safe_nowmna_detail_link(uid)
                        prefetched_items[uid] = _extract_item_from_detail_link(precheck_driver, source_link)
                    raw_item = prefetched_items.get(uid)
                    if raw_item:
                        item = _apply_sheet_basis_to_item(dict(raw_item), row)
                        prefetched_items[uid] = item
                except Exception:
                    item = None

            defer_reason = ""
            if isinstance(item, dict) and item:
                defer_reason = _detect_defer_request_reason(
                    item.get("memo", ""),
                    item.get("claim_price", ""),
                    item.get("price", ""),
                    _row_text(row, 33),
                )
                if defer_reason:
                    source_status = "완료"
                    deleted_on_source = True

            probe_item = None if (status_only or source_status == "완료") else item
            probe_out = _reconcile_sheet_sync(
                worksheet=worksheet,
                runtime=probe_runtime,
                uid=uid,
                status_label=source_status,
                item=probe_item,
                dry_run=True,
                row_no_override=row_no_override,
            )
            probe_action = str((probe_out or {}).get("action", "")).strip()
            if probe_action not in {"updated", "appended", "status_only"}:
                continue

            candidate_jobs.append(
                {
                    "wr_id": effective_wr_id,
                    "uid": uid,
                    "source_status": source_status,
                    "deleted_on_source": bool(deleted_on_source),
                    "defer_reason": defer_reason,
                    "item": item,
                    "probe_action": probe_action,
                    "row_no_override": row_no_override,
                    "sheet_wr_id": current_sheet_wr_id,
                    "site_wr_id": site_wr_id,
                }
            )
    finally:
        _safe_quit(precheck_driver)
    candidate_jobs = sorted(candidate_jobs, key=lambda x: int(x.get("wr_id", 0)), reverse=True)
    print(
        f"   변경 후보: {len(candidate_jobs)}건 / 시트 UID {len(uid_to_row)}건 "
        f"(변경 없으면 seoul 반영 생략)"
    )
    if not candidate_jobs:
        print("✅ nowmna↔시트 기준 변경사항 없음: seoulmna 반영 생략")
        _leave_reconcile_guard(guard_ctx)
        return

    if sheet_only:
        print("🧾 [대조3] sheet-only 모드: seoul 반영(로그인/수정) 생략, 구글시트만 반영")
        stats = {
            "same": 0,
            "updated": 0,
            "completed": 0,
            "already_completed": 0,
            "no_uid": 0,
            "failed": 0,
            "sheet_updated": 0,
            "sheet_appended": 0,
            "sheet_status_only": 0,
            "sheet_rowno_only": 0,
            "sheet_rowno_and_status": 0,
            "sheet_same": 0,
            "sheet_skipped": 0,
            "sheet_failed": 0,
        }
        applied_changes = 0

        def _consume_sheet_out_sheet_only(sheet_out):
            action = str((sheet_out or {}).get("action", "")).strip()
            if action == "status_only":
                alignment_change = str((sheet_out or {}).get("alignment_change", "status_only")).strip() or "status_only"
                if alignment_change == "row_no_only":
                    stats["sheet_rowno_only"] += 1
                elif alignment_change == "row_no_and_status":
                    stats["sheet_rowno_and_status"] += 1
                else:
                    stats["sheet_status_only"] += 1
            elif action == "updated":
                stats["sheet_updated"] += 1
            elif action == "appended":
                stats["sheet_appended"] += 1
            elif action == "same":
                stats["sheet_same"] += 1
            else:
                stats["sheet_skipped"] += 1
            return action

        for idx, job in enumerate(candidate_jobs, start=1):
            if max_updates > 0 and applied_changes >= max_updates:
                print(f"⚠️ 변경 상한 도달: {max_updates}건")
                break

            wr_id = int(job.get("wr_id", 0) or 0)
            uid = str(job.get("uid", "")).strip()
            source_status = str(job.get("source_status", "가능")).strip() or "가능"
            if source_status not in {"가능", "보류", "완료"}:
                source_status = "가능"

            entry = {
                "wr_id": wr_id,
                "uid": uid,
                "source_status": source_status,
                "result": "",
                "site_action": "skipped_sheet_only",
                "sheet_action": "",
                "site_changed_keys": [],
                "site_changes": {},
                "sheet_changes": {},
                "message": f"precheck={str(job.get('probe_action', '')).strip()}",
                "error": "",
                "rollback": {},
            }
            audit["entries"].append(entry)

            if not uid:
                stats["no_uid"] += 1
                entry["result"] = "skip_no_uid"
                entry["message"] = "UID 미식별"
                print(f"   - [{idx}/{len(candidate_jobs)}] WR {wr_id}: UID 미식별 -> 스킵")
                continue

            item = None if (status_only or source_status == "완료") else job.get("item")
            if not isinstance(item, dict):
                item = None
            try:
                sheet_out = _reconcile_sheet_sync(
                    worksheet=worksheet,
                    runtime=sheet_runtime,
                    uid=uid,
                    status_label=source_status,
                    item=item,
                    dry_run=dry_run,
                    row_no_override=job.get("row_no_override"),
                )
                sheet_action = _consume_sheet_out_sheet_only(sheet_out)
                entry["sheet_action"] = sheet_action
                entry["sheet_changes"] = _sheet_row_change_map(
                    sheet_out.get("before_row", []),
                    sheet_out.get("after_row", []),
                    header_row=sheet_header,
                )
                if sheet_action in {"updated", "appended", "status_only"}:
                    stats["updated"] += 1
                    applied_changes += 1
                    entry["result"] = "planned_sheet_only" if dry_run else "sheet_only_updated"
                    entry["rollback"]["sheet"] = {
                        "action": sheet_action,
                        "row_idx": sheet_out.get("row_idx", 0),
                        "before_exists": bool(sheet_out.get("before_exists", True)),
                        "before_row": list(sheet_out.get("before_row", []) or []),
                    }
                    print(
                        f"   {'🧪' if dry_run else '✅'} [{idx}/{len(candidate_jobs)}] WR {wr_id}/UID {uid}: "
                        f"시트 반영 ({sheet_action})"
                    )
                elif sheet_action == "same":
                    stats["same"] += 1
                    entry["result"] = "same"
                    print(f"   - [{idx}/{len(candidate_jobs)}] WR {wr_id}/UID {uid}: 시트 동일 -> 스킵")
                else:
                    stats["same"] += 1
                    entry["result"] = "sheet_skipped"
                    print(f"   - [{idx}/{len(candidate_jobs)}] WR {wr_id}/UID {uid}: 시트 스킵 ({sheet_action})")
            except Exception as se:
                stats["failed"] += 1
                stats["sheet_failed"] += 1
                entry["result"] = "failed"
                entry["sheet_action"] = "failed"
                entry["error"] = str(se)
                print(f"   ❌ [{idx}/{len(candidate_jobs)}] WR {wr_id}/UID {uid}: 시트 반영 실패 ({se})")

            if delay_sec > 0:
                time.sleep(delay_sec)

        audit["finished_at"] = datetime.now().isoformat(timespec="seconds")
        audit["stats"] = dict(stats)
        audit_paths = _save_reconcile_audit(audit)
        print(
            f"\n✅ 대조 요약 ({'dry-run' if dry_run else 'apply'}, sheet-only) -> "
            f"동일스킵 {stats['same']} / "
            f"시트반영 {stats['updated']} / "
            f"실패 {stats['failed']} / "
            f"시트갱신 {stats['sheet_updated']} / "
            f"시트추가 {stats['sheet_appended']} / "
            f"시트상태 {stats['sheet_status_only']} / "
            f"시트번호 {stats['sheet_rowno_only']} / "
            f"시트번호+상태 {stats['sheet_rowno_and_status']} / "
            f"시트동일 {stats['sheet_same']} / "
            f"시트스킵 {stats['sheet_skipped']} / "
            f"시트실패 {stats['sheet_failed']}"
        )
        print(
            "🧾 대조 리포트 저장: "
            f"{audit_paths.get('json', '')}, {audit_paths.get('md', '')}, {audit_paths.get('csv', '')}"
        )
        _leave_reconcile_guard(guard_ctx)
        return

    print("🌐 [대조3] seoul 반영 단계 시작(로그인 포함)...")
    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        print("❌ ADMIN_ID/ADMIN_PW 미설정: seoul 반영을 실행할 수 없습니다.")
        _leave_reconcile_guard(guard_ctx)
        return

    publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, admin_id, admin_pw)
    try:
        publisher.login()
    except Exception as e:
        print(f"❌ 사이트 로그인 실패: {e}")
        _leave_reconcile_guard(guard_ctx)
        return
    limit_info = publisher.daily_limit_summary()
    print(
        f"🧮 일일 상한: 요청 {limit_info['requests']}/{limit_info['request_cap']} / "
        f"수정 {limit_info['writes']}/{limit_info['write_cap']} "
        f"(state={limit_info['state_file']})"
    )

    options = webdriver.ChromeOptions()
    driver = None
    item_cache = dict(prefetched_items)
    no_site_jobs = [x for x in candidate_jobs if int(x.get("wr_id", 0) or 0) <= 0]
    site_jobs = [x for x in candidate_jobs if int(x.get("wr_id", 0) or 0) > 0]
    seoul_wr_ids = [int(x.get("wr_id", 0)) for x in site_jobs if str(x.get("wr_id", "")).isdigit() and int(x.get("wr_id", 0)) > 0]
    job_by_wr_id = {int(x["wr_id"]): x for x in site_jobs if str(x.get("wr_id", "")).isdigit() and int(x.get("wr_id", 0)) > 0}

    stats = {
        "same": 0,
        "updated": 0,
        "completed": 0,
        "already_completed": 0,
        "no_uid": 0,
        "failed": 0,
        "sheet_updated": 0,
        "sheet_appended": 0,
        "sheet_status_only": 0,
        "sheet_rowno_only": 0,
        "sheet_rowno_and_status": 0,
        "sheet_same": 0,
        "sheet_skipped": 0,
        "sheet_failed": 0,
    }
    applied_changes = 0

    def _consume_sheet_out(sheet_out):
        action = str((sheet_out or {}).get("action", "")).strip()
        if action == "status_only":
            alignment_change = str((sheet_out or {}).get("alignment_change", "status_only")).strip() or "status_only"
            if alignment_change == "row_no_only":
                stats["sheet_rowno_only"] += 1
            elif alignment_change == "row_no_and_status":
                stats["sheet_rowno_and_status"] += 1
            else:
                stats["sheet_status_only"] += 1
        elif action == "updated":
            stats["sheet_updated"] += 1
        elif action == "appended":
            stats["sheet_appended"] += 1
        elif action == "same":
            stats["sheet_same"] += 1
        else:
            stats["sheet_skipped"] += 1
        return action

    try:
        for idx, job in enumerate(no_site_jobs, start=1):
            if max_updates > 0 and applied_changes >= max_updates:
                print(f"⚠️ 변경 상한 도달: {max_updates}건")
                break

            uid = str(job.get("uid", "")).strip()
            source_status = str(job.get("source_status", "가능")).strip() or "가능"
            if source_status not in {"가능", "보류", "완료"}:
                source_status = "가능"
            entry = {
                "wr_id": 0,
                "uid": uid,
                "source_status": source_status,
                "result": "",
                "site_action": "skipped_no_site_wr",
                "sheet_action": "",
                "site_changed_keys": [],
                "site_changes": {},
                "sheet_changes": {},
                "message": "co.kr authoritative wr_id 없음",
                "error": "",
                "rollback": {},
            }
            audit["entries"].append(entry)

            item = None if (status_only or source_status == "완료") else job.get("item")
            if not isinstance(item, dict):
                item = None
            try:
                if dry_run and item is not None:
                    stats["updated"] += 1
                    applied_changes += 1
                    entry["result"] = "planned_publish_missing_site"
                    entry["site_action"] = "planned_insert"
                    entry["message"] = "co.kr 신규 게시 예정 (site wr_id 없음)"
                    print(
                        f"   🧪 [no-site {idx}/{len(no_site_jobs)}] UID {uid}: "
                        "co.kr 신규 등록 예정"
                    )
                    continue

                if (not dry_run) and item is not None:
                    publish_out = _resolve_publish_listing_result(
                        publisher,
                        item,
                        publisher.publish_listing(item),
                        max_pages=seoul_max_pages,
                    )
                    new_wr_id = int(publish_out.get("wr_id", 0) or 0)
                    entry["wr_id"] = new_wr_id
                    entry["site_action"] = "inserted"
                    entry["site_changes"] = {
                        "inserted": {
                            "before": "",
                            "after": publish_out.get("url", ""),
                        }
                    }
                    entry["site_changed_keys"] = ["inserted"]
                    entry["message"] = (
                        f"co.kr 신규 등록 생성 uid={uid} -> wr_id={new_wr_id}"
                        if new_wr_id > 0
                        else f"co.kr 신규 등록 생성 uid={uid}"
                    )
                    entry["rollback"]["site"] = {
                        "wr_id": new_wr_id,
                        "url": publish_out.get("url", ""),
                        "subject": publish_out.get("subject", ""),
                    }
                    job["row_no_override"] = new_wr_id if new_wr_id > 0 else ""
                    sheet_out = _reconcile_sheet_sync(
                        worksheet=worksheet,
                        runtime=sheet_runtime,
                        uid=uid,
                        status_label=source_status,
                        item=item,
                        dry_run=False,
                        row_no_override=job.get("row_no_override"),
                    )
                    sheet_action = _consume_sheet_out(sheet_out)
                    entry["sheet_action"] = sheet_action
                    entry["sheet_changes"] = _sheet_row_change_map(
                        sheet_out.get("before_row", []),
                        sheet_out.get("after_row", []),
                        header_row=sheet_header,
                    )
                    if sheet_action in {"updated", "appended", "status_only"}:
                        stats["updated"] += 1
                        applied_changes += 1
                        entry["result"] = "published_missing_site"
                        entry["rollback"]["sheet"] = {
                            "action": sheet_action,
                            "row_idx": sheet_out.get("row_idx", 0),
                            "before_exists": bool(sheet_out.get("before_exists", True)),
                            "before_row": list(sheet_out.get("before_row", []) or []),
                        }
                    print(
                        f"   ✅ [no-site {idx}/{len(no_site_jobs)}] UID {uid}: "
                        f"co.kr 신규 등록 후 시트 동기화 ({sheet_action})"
                    )
                    continue

                sheet_out = _reconcile_sheet_sync(
                    worksheet=worksheet,
                    runtime=sheet_runtime,
                    uid=uid,
                    status_label=source_status,
                    item=item,
                    dry_run=dry_run,
                    row_no_override=job.get("row_no_override"),
                )
                sheet_action = _consume_sheet_out(sheet_out)
                entry["sheet_action"] = sheet_action
                entry["sheet_changes"] = _sheet_row_change_map(
                    sheet_out.get("before_row", []),
                    sheet_out.get("after_row", []),
                    header_row=sheet_header,
                )
                if sheet_action in {"updated", "appended", "status_only"}:
                    stats["updated"] += 1
                    applied_changes += 1
                    entry["result"] = "planned_sheet_only_no_site" if dry_run else "sheet_only_no_site"
                    entry["rollback"]["sheet"] = {
                        "action": sheet_action,
                        "row_idx": sheet_out.get("row_idx", 0),
                        "before_exists": bool(sheet_out.get("before_exists", True)),
                        "before_row": list(sheet_out.get("before_row", []) or []),
                    }
                    print(
                        f"   {'🧪' if dry_run else '✅'} [no-site {idx}/{len(no_site_jobs)}] UID {uid}: "
                        f"시트만 동기화 ({sheet_action})"
                    )
                elif sheet_action == "same":
                    stats["same"] += 1
                    entry["result"] = "same"
                    print(f"   - [no-site {idx}/{len(no_site_jobs)}] UID {uid}: 동일 -> 스킵")
                else:
                    stats["same"] += 1
                    entry["result"] = "sheet_skipped"
                    print(f"   - [no-site {idx}/{len(no_site_jobs)}] UID {uid}: 시트 스킵 ({sheet_action})")
            except Exception as se:
                stats["failed"] += 1
                stats["sheet_failed"] += 1
                entry["result"] = "failed"
                entry["sheet_action"] = "failed"
                entry["error"] = str(se)
                print(f"   ❌ [no-site {idx}/{len(no_site_jobs)}] UID {uid}: 시트 반영 실패 ({se})")

        for idx, wr_id in enumerate(seoul_wr_ids, start=1):
            if max_updates > 0 and applied_changes >= max_updates:
                print(f"⚠️ 변경 상한 도달: {max_updates}건")
                break

            entry = {
                "wr_id": int(wr_id),
                "uid": "",
                "source_status": "",
                "result": "",
                "site_action": "",
                "sheet_action": "",
                "site_changed_keys": [],
                "site_changes": {},
                "sheet_changes": {},
                "message": "",
                "error": "",
                "rollback": {},
            }
            audit["entries"].append(entry)

            try:
                job = dict(job_by_wr_id.get(int(wr_id), {}) or {})
                uid = str(job.get("uid", "")).strip()
                if not uid:
                    stats["no_uid"] += 1
                    entry["result"] = "skip_no_uid"
                    entry["message"] = "UID 미식별"
                    print(f"   - [{idx}/{len(seoul_wr_ids)}] WR {wr_id}: UID 미식별 -> 스킵")
                    continue

                entry["uid"] = uid
                deleted_on_source = bool(job.get("deleted_on_source"))
                defer_reason = _compact_text(job.get("defer_reason", ""))
                source_status = str(job.get("source_status", "가능")).strip() or "가능"
                if source_status not in {"가능", "보류", "완료"}:
                    source_status = "가능"
                entry["source_status"] = source_status
                if str(job.get("probe_action", "")).strip():
                    entry["message"] = f"precheck={str(job.get('probe_action', '')).strip()}"
                preloaded_item = job.get("item")
                if isinstance(preloaded_item, dict) and preloaded_item:
                    item_cache[uid] = dict(preloaded_item)

                action_url, payload, form, form_html = publisher.get_edit_payload(wr_id)
                before_site = _payload_subset(payload, RECONCILE_SITE_AUDIT_KEYS)
                status_map = _select_label_value_map(form, "wr_17")
                target_status_val = _select_value_from_text(status_map, source_status)
                current_status_val = str(payload.get("wr_17", "")).strip()
                status_changed = bool(target_status_val and current_status_val != target_status_val)

                if source_status == "완료":
                    if defer_reason:
                        reason = f"요청패턴 감지({defer_reason})"
                    else:
                        reason = "삭제건" if deleted_on_source else "원본상태=계약완료"
                    if status_changed:
                        site_updates_status = {"wr_17": target_status_val}
                        after_status_site = _payload_after_updates(
                            before_site,
                            _payload_subset(site_updates_status, RECONCILE_SITE_AUDIT_KEYS),
                        )
                        status_site_changes = _payload_change_map(before_site, after_status_site)
                        entry["site_changes"] = status_site_changes
                        entry["site_changed_keys"] = sorted(status_site_changes.keys())
                    sheet_action = None
                    if worksheet is not None and sheet_runtime is not None:
                        try:
                            sheet_out = _reconcile_sheet_sync(
                                worksheet=worksheet,
                                runtime=sheet_runtime,
                                uid=uid,
                                status_label="완료",
                                item=None,
                                dry_run=dry_run,
                                row_no_override=job.get("row_no_override"),
                            )
                            sheet_action = _consume_sheet_out(sheet_out)
                            entry["sheet_action"] = sheet_action
                            entry["sheet_changes"] = _sheet_row_change_map(
                                sheet_out.get("before_row", []),
                                sheet_out.get("after_row", []),
                                header_row=sheet_header,
                            )
                            if sheet_action in {"updated", "appended", "status_only"}:
                                entry["rollback"]["sheet"] = {
                                    "action": sheet_action,
                                    "row_idx": sheet_out.get("row_idx", 0),
                                    "before_exists": bool(sheet_out.get("before_exists", True)),
                                    "before_row": list(sheet_out.get("before_row", []) or []),
                                }
                        except Exception as se:
                            stats["sheet_failed"] += 1
                            entry["sheet_action"] = "failed"
                            entry["error"] = f"sheet_sync_failed:{se}"
                            print(f"   ⚠️ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 시트 완료상태 동기화 실패 ({se})")
                    if status_changed:
                        if dry_run:
                            stats["completed"] += 1
                            applied_changes += 1
                            entry["result"] = "planned_complete"
                            entry["site_action"] = "planned"
                            if defer_reason:
                                entry["message"] = (
                                    (entry.get("message", "") + " / " if entry.get("message") else "")
                                    + f"deferred={defer_reason}"
                                )
                            print(
                                f"   🧪 [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"{reason} -> 상태 완료 예정"
                                f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                            )
                        else:
                            publisher.submit_edit_updates(action_url, payload, {"wr_17": target_status_val})
                            if defer_reason:
                                _enqueue_deferred_requeue(uid, wr_id, defer_reason, source_status="완료")
                            stats["completed"] += 1
                            applied_changes += 1
                            entry["result"] = "completed"
                            entry["site_action"] = "updated"
                            entry["rollback"]["site"] = {
                                "wr_id": int(wr_id),
                                "updates": _payload_subset(payload, ("wr_17",)),
                            }
                            print(
                                f"   ✅ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"{reason} -> 상태 완료"
                                f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                            )
                    else:
                        stats["already_completed"] += 1
                        entry["result"] = "already_completed"
                        entry["site_action"] = "same"
                        if defer_reason and (not dry_run):
                            _enqueue_deferred_requeue(uid, wr_id, defer_reason, source_status="완료")
                        print(
                            f"   - [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                            f"{reason} (이미 완료)"
                            f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                        )
                    if delay_sec > 0:
                        time.sleep(delay_sec)
                    continue

                if status_only:
                    sheet_action = None
                    if worksheet is not None and sheet_runtime is not None:
                        try:
                            sheet_out = _reconcile_sheet_sync(
                                worksheet=worksheet,
                                runtime=sheet_runtime,
                                uid=uid,
                                status_label=source_status,
                                item=None,
                                dry_run=dry_run,
                                row_no_override=job.get("row_no_override"),
                            )
                            sheet_action = _consume_sheet_out(sheet_out)
                            entry["sheet_action"] = sheet_action
                            entry["sheet_changes"] = _sheet_row_change_map(
                                sheet_out.get("before_row", []),
                                sheet_out.get("after_row", []),
                                header_row=sheet_header,
                            )
                            if sheet_action in {"updated", "appended", "status_only"}:
                                entry["rollback"]["sheet"] = {
                                    "action": sheet_action,
                                    "row_idx": sheet_out.get("row_idx", 0),
                                    "before_exists": bool(sheet_out.get("before_exists", True)),
                                    "before_row": list(sheet_out.get("before_row", []) or []),
                                }
                        except Exception as se:
                            stats["sheet_failed"] += 1
                            entry["sheet_action"] = "failed"
                            entry["error"] = f"sheet_sync_failed:{se}"
                            print(f"   ⚠️ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 시트 상태 동기화 실패 ({se})")

                    if status_changed:
                        site_updates_status = {"wr_17": target_status_val}
                        after_status_site = _payload_after_updates(
                            before_site,
                            _payload_subset(site_updates_status, RECONCILE_SITE_AUDIT_KEYS),
                        )
                        status_site_changes = _payload_change_map(before_site, after_status_site)
                        entry["site_changes"] = status_site_changes
                        entry["site_changed_keys"] = sorted(status_site_changes.keys())
                        if dry_run:
                            stats["updated"] += 1
                            applied_changes += 1
                            entry["result"] = "planned_status_only"
                            entry["site_action"] = "planned"
                            print(
                                f"   🧪 [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"상태전용 동기화 예정({source_status})"
                                f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                            )
                        else:
                            publisher.submit_edit_updates(action_url, payload, {"wr_17": target_status_val})
                            stats["updated"] += 1
                            applied_changes += 1
                            entry["result"] = "status_only_updated"
                            entry["site_action"] = "updated"
                            entry["rollback"]["site"] = {
                                "wr_id": int(wr_id),
                                "updates": _payload_subset(payload, ("wr_17",)),
                            }
                            print(
                                f"   ✅ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"상태전용 동기화({source_status})"
                                f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                            )
                    elif str(entry.get("sheet_action", "")) in {"updated", "appended", "status_only"}:
                        stats["updated"] += 1
                        applied_changes += 1
                        entry["result"] = "sheet_only_status"
                        entry["site_action"] = "same"
                        print(
                            f"   {'🧪' if dry_run else '✅'} [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                            f"시트 상태만 동기화 ({entry['sheet_action']})"
                        )
                    else:
                        stats["same"] += 1
                        entry["result"] = "same"
                        entry["site_action"] = "same"
                        print(f"   - [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 동일 -> 스킵")
                    if delay_sec > 0:
                        time.sleep(delay_sec)
                    continue

                if uid not in item_cache:
                    source_link = _safe_nowmna_detail_link(uid)
                    if driver is None:
                        driver = webdriver.Chrome(
                            service=Service(ChromeDriverManager().install()),
                            options=options,
                        )
                    item_cache[uid] = _extract_item_from_detail_link(driver, source_link)

                item = item_cache.get(uid)
                if not item:
                    sheet_action = None
                    if worksheet is not None and sheet_runtime is not None:
                        try:
                            sheet_out = _reconcile_sheet_sync(
                                worksheet=worksheet,
                                runtime=sheet_runtime,
                                uid=uid,
                                status_label=source_status,
                                item=None,
                                dry_run=dry_run,
                                row_no_override=job.get("row_no_override"),
                            )
                            sheet_action = _consume_sheet_out(sheet_out)
                            entry["sheet_action"] = sheet_action
                            entry["sheet_changes"] = _sheet_row_change_map(
                                sheet_out.get("before_row", []),
                                sheet_out.get("after_row", []),
                                header_row=sheet_header,
                            )
                            if sheet_action in {"updated", "appended", "status_only"}:
                                entry["rollback"]["sheet"] = {
                                    "action": sheet_action,
                                    "row_idx": sheet_out.get("row_idx", 0),
                                    "before_exists": bool(sheet_out.get("before_exists", True)),
                                    "before_row": list(sheet_out.get("before_row", []) or []),
                                }
                        except Exception as se:
                            stats["sheet_failed"] += 1
                            entry["sheet_action"] = "failed"
                            entry["error"] = f"sheet_sync_failed:{se}"
                            print(f"   ⚠️ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 시트 상태 동기화 실패 ({se})")
                    if status_changed:
                        site_updates_status = {"wr_17": target_status_val}
                        after_status_site = _payload_after_updates(
                            before_site,
                            _payload_subset(site_updates_status, RECONCILE_SITE_AUDIT_KEYS),
                        )
                        status_site_changes = _payload_change_map(before_site, after_status_site)
                        entry["site_changes"] = status_site_changes
                        entry["site_changed_keys"] = sorted(status_site_changes.keys())
                        if dry_run:
                            stats["updated"] += 1
                            applied_changes += 1
                            entry["result"] = "planned_status_fallback"
                            entry["site_action"] = "planned"
                            print(
                                f"   🧪 [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"원본 상세수집 실패 -> 상태 {source_status} 변경 예정"
                                f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                            )
                        else:
                            publisher.submit_edit_updates(action_url, payload, {"wr_17": target_status_val})
                            stats["updated"] += 1
                            applied_changes += 1
                            entry["result"] = "status_fallback_updated"
                            entry["site_action"] = "updated"
                            entry["rollback"]["site"] = {
                                "wr_id": int(wr_id),
                                "updates": _payload_subset(payload, ("wr_17",)),
                            }
                            print(
                                f"   ✅ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"원본 상세수집 실패 -> 상태 {source_status} 반영"
                                f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                            )
                    else:
                        if str(entry.get("sheet_action", "")) in {"updated", "appended", "status_only"}:
                            stats["updated"] += 1
                            applied_changes += 1
                            entry["result"] = "sheet_only_no_detail"
                            entry["site_action"] = "same"
                            print(
                                f"   {'🧪' if dry_run else '✅'} [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                                f"시트만 동기화 ({entry['sheet_action']})"
                            )
                        else:
                            stats["failed"] += 1
                            entry["result"] = "failed_no_detail"
                            entry["site_action"] = "failed"
                            entry["error"] = entry.get("error", "") or "원본 상세 수집 실패"
                            print(f"   ❌ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 원본 수집 실패")
                    continue

                item = dict(item)
                sheet_row_for_uid = _sheet_row_from_runtime(sheet_runtime, uid)
                if sheet_row_for_uid:
                    item = _apply_sheet_basis_to_item(item, sheet_row_for_uid)

                sync_updates = _build_sync_updates(item, form, form_html, payload)
                diff_keys = _diff_payload_updates(payload, sync_updates)
                if status_changed:
                    sync_updates["wr_17"] = target_status_val
                    diff_keys = list(diff_keys) + [f"wr_17({source_status})"]
                site_update_subset = _payload_subset(sync_updates, RECONCILE_SITE_AUDIT_KEYS)
                after_site = _payload_after_updates(before_site, site_update_subset)
                site_changes = _payload_change_map(before_site, after_site)
                entry["site_changes"] = site_changes
                entry["site_changed_keys"] = sorted(site_changes.keys())

                sheet_action = None
                if worksheet is not None and sheet_runtime is not None:
                    try:
                        sheet_out = _reconcile_sheet_sync(
                            worksheet=worksheet,
                            runtime=sheet_runtime,
                            uid=uid,
                            status_label=source_status,
                            item=item,
                            dry_run=dry_run,
                            row_no_override=job.get("row_no_override"),
                        )
                        sheet_action = _consume_sheet_out(sheet_out)
                        entry["sheet_action"] = sheet_action
                        entry["sheet_changes"] = _sheet_row_change_map(
                            sheet_out.get("before_row", []),
                            sheet_out.get("after_row", []),
                            header_row=sheet_header,
                        )
                        if sheet_action in {"updated", "appended", "status_only"}:
                            entry["rollback"]["sheet"] = {
                                "action": sheet_action,
                                "row_idx": sheet_out.get("row_idx", 0),
                                "before_exists": bool(sheet_out.get("before_exists", True)),
                                "before_row": list(sheet_out.get("before_row", []) or []),
                            }
                    except Exception as se:
                        stats["sheet_failed"] += 1
                        entry["sheet_action"] = "failed"
                        entry["error"] = f"sheet_sync_failed:{se}"
                        print(f"   ⚠️ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 시트 동기화 실패 ({se})")

                if not diff_keys and sheet_action in {"same", "skip_no_row", "skip_no_uid", ""}:
                    stats["same"] += 1
                    entry["result"] = "same"
                    entry["site_action"] = "same"
                    print(f"   - [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: 동일 -> 스킵")
                    continue

                if not diff_keys and sheet_action in {"updated", "appended", "status_only"}:
                    stats["updated"] += 1
                    applied_changes += 1
                    entry["result"] = "sheet_only"
                    entry["site_action"] = "same"
                    print(
                        f"   {'🧪' if dry_run else '✅'} [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                        f"시트만 동기화 ({sheet_action})"
                    )
                    if delay_sec > 0:
                        time.sleep(delay_sec)
                    continue

                if max_updates > 0 and applied_changes >= max_updates:
                    print(f"⚠️ 변경 상한 도달: {max_updates}건")
                    break

                if dry_run:
                    stats["updated"] += 1
                    applied_changes += 1
                    entry["result"] = "planned_update"
                    entry["site_action"] = "planned"
                    print(
                        f"   🧪 [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                        f"갱신 예정 ({', '.join(diff_keys[:6])}{'...' if len(diff_keys) > 6 else ''})"
                        f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                    )
                else:
                    publisher.submit_edit_updates(action_url, payload, sync_updates)
                    stats["updated"] += 1
                    applied_changes += 1
                    entry["result"] = "updated"
                    entry["site_action"] = "updated"
                    entry["rollback"]["site"] = {
                        "wr_id": int(wr_id),
                        "updates": _payload_subset(payload, sync_updates.keys()),
                    }
                    print(
                        f"   ✅ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}/UID {uid}: "
                        f"갱신 ({', '.join(diff_keys[:6])}{'...' if len(diff_keys) > 6 else ''})"
                        f"{' / 시트=' + str(sheet_action) if sheet_action else ''}"
                    )
                if delay_sec > 0:
                    time.sleep(delay_sec)

            except Exception as e:
                stats["failed"] += 1
                entry["result"] = "failed"
                entry["site_action"] = "failed"
                entry["error"] = str(e)
                print(f"   ❌ [{idx}/{len(seoul_wr_ids)}] WR {wr_id}: {e}")

    finally:
        _safe_quit(driver)

    audit["finished_at"] = datetime.now().isoformat(timespec="seconds")
    audit["stats"] = dict(stats)
    audit_paths = _save_reconcile_audit(audit)

    print(
        f"\n✅ 대조 요약 ({'dry-run' if dry_run else 'apply'}) -> "
        f"동일스킵 {stats['same']} / "
        f"내용갱신 {stats['updated']} / "
        f"삭제완료처리 {stats['completed']} / "
        f"이미완료 {stats['already_completed']} / "
        f"UID없음 {stats['no_uid']} / "
        f"실패 {stats['failed']} / "
        f"시트갱신 {stats['sheet_updated']} / "
        f"시트추가 {stats['sheet_appended']} / "
        f"시트상태 {stats['sheet_status_only']} / "
        f"시트번호 {stats['sheet_rowno_only']} / "
        f"시트번호+상태 {stats['sheet_rowno_and_status']} / "
        f"시트동일 {stats['sheet_same']} / "
        f"시트스킵 {stats['sheet_skipped']} / "
        f"시트실패 {stats['sheet_failed']}"
    )
    print(
        "🧾 대조 리포트 저장: "
        f"{audit_paths.get('json', '')}, {audit_paths.get('md', '')}, {audit_paths.get('csv', '')}"
    )
    _leave_reconcile_guard(guard_ctx)


def run_reconcile_rollback(snapshot_path="", dry_run=False, limit=0):
    raw_snapshot = str(snapshot_path or "").strip()
    if raw_snapshot.lower() in {"latest", "auto"}:
        raw_snapshot = ""
    snapshot = _resolve_latest_reconcile_snapshot(raw_snapshot)
    if not snapshot or not os.path.exists(snapshot):
        print(f"❌ 롤백 스냅샷을 찾을 수 없습니다: {snapshot_path or '(latest)'}")
        return

    try:
        with open(snapshot, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 롤백 스냅샷 로드 실패: {e}")
        return

    entries = list(data.get("entries", []))
    rollback_entries = [e for e in entries if isinstance(e, dict) and e.get("rollback")]
    rollback_entries = list(reversed(rollback_entries))
    limit = max(0, int(limit or 0))
    if limit > 0:
        rollback_entries = rollback_entries[:limit]

    if not rollback_entries:
        print("✅ 롤백 대상 변경 내역이 없습니다.")
        return

    need_site = any(e.get("rollback", {}).get("site") for e in rollback_entries)
    need_sheet = any(e.get("rollback", {}).get("sheet") for e in rollback_entries)

    publisher = None
    if need_site:
        admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
        admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
        if not admin_id or not admin_pw:
            print("❌ 롤백 실패: ADMIN_ID/ADMIN_PW 미설정")
            return
        publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, admin_id, admin_pw)
        try:
            publisher.login()
        except Exception as e:
            print(f"❌ 롤백용 사이트 로그인 실패: {e}")
            return
        limit_info = publisher.daily_limit_summary()
        print(
            f"🧮 일일 상한: 요청 {limit_info['requests']}/{limit_info['request_cap']} / "
            f"수정 {limit_info['writes']}/{limit_info['write_cap']} "
            f"(state={limit_info['state_file']})"
        )

    worksheet = None
    if need_sheet:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
            client = gspread.authorize(creds)
            worksheet = client.open(SHEET_NAME).sheet1
        except Exception as e:
            print(f"❌ 롤백용 시트 연결 실패: {e}")
            return

    stats = {
        "site_restored": 0,
        "sheet_restored": 0,
        "skipped": 0,
        "failed": 0,
    }
    print(f"↩️ 롤백 시작: 대상 {len(rollback_entries)}건 / dry_run={dry_run} / snapshot={snapshot}")

    for idx, row in enumerate(rollback_entries, start=1):
        wr_id = int(row.get("wr_id", 0) or 0)
        uid = str(row.get("uid", "")).strip()
        rb = dict(row.get("rollback", {}) or {})
        site_rb = dict(rb.get("site", {}) or {})
        sheet_rb = dict(rb.get("sheet", {}) or {})

        try:
            if site_rb and publisher is not None:
                updates = dict(site_rb.get("updates", {}) or {})
                if updates and wr_id > 0:
                    if dry_run:
                        print(f"   🧪 [{idx}/{len(rollback_entries)}] WR {wr_id}/UID {uid}: 사이트 롤백 예정 ({','.join(updates.keys())})")
                    else:
                        action_url, payload, form, form_html = publisher.get_edit_payload(wr_id)
                        publisher.submit_edit_updates(action_url, payload, updates)
                        stats["site_restored"] += 1
                        print(f"   ✅ [{idx}/{len(rollback_entries)}] WR {wr_id}/UID {uid}: 사이트 롤백 완료")
                else:
                    stats["skipped"] += 1

            if sheet_rb and worksheet is not None:
                row_idx = int(sheet_rb.get("row_idx", 0) or 0)
                before_exists = bool(sheet_rb.get("before_exists", True))
                before_row = list(sheet_rb.get("before_row", []) or [])
                if row_idx <= 1:
                    stats["skipped"] += 1
                else:
                    if dry_run:
                        print(f"   🧪 [{idx}/{len(rollback_entries)}] WR {wr_id}/UID {uid}: 시트 롤백 예정 (row={row_idx})")
                    else:
                        if before_exists and before_row:
                            cell = f"A{row_idx}"
                            try:
                                worksheet.update(values=[before_row], range_name=cell)
                            except TypeError:
                                worksheet.update(cell, [before_row])
                        else:
                            clear_cols = max(42, len(before_row) or 42)
                            cell = f"A{row_idx}"
                            blanks = [[""] * clear_cols]
                            try:
                                worksheet.update(values=blanks, range_name=cell)
                            except TypeError:
                                worksheet.update(cell, blanks)
                        stats["sheet_restored"] += 1
                        print(f"   ✅ [{idx}/{len(rollback_entries)}] WR {wr_id}/UID {uid}: 시트 롤백 완료 (row={row_idx})")
        except Exception as e:
            stats["failed"] += 1
            print(f"   ❌ [{idx}/{len(rollback_entries)}] WR {wr_id}/UID {uid}: 롤백 실패 ({e})")

    print(
        f"✅ 롤백 요약 ({'dry-run' if dry_run else 'apply'}) -> "
        f"site {stats['site_restored']} / sheet {stats['sheet_restored']} / "
        f"skip {stats['skipped']} / fail {stats['failed']}"
    )


def run_price_trace_backfill(dry_run=False):
    print("🧪 [Backfill] 가격 추적 백필 시작...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        worksheet = client.open(SHEET_NAME).sheet1
        all_values = worksheet.get_all_values()
        _ensure_price_trace_headers(worksheet, all_values)
        all_values = worksheet.get_all_values()
    except Exception as e:
        print(f"❌ 백필용 시트 연결 실패: {e}")
        return

    payload = _build_price_trace_updates(all_values)
    total_rows = payload["total_rows"]
    changed_rows = payload["changed_rows"]
    recovered_rows = payload["recovered_rows"]

    print(f"   대상 행: {total_rows}건")
    print(f"   변경 예정: {changed_rows}건")
    print(f"   협의/빈값 복구: {recovered_rows}건")

    for ex in payload["changed_examples"][:10]:
        print(
            "   - "
            f"R{ex['row']} '{ex['old_price']}' -> '{ex['new_price']}' "
            f"(source={ex['source']}, conf={ex['confidence']}, fb={ex['fallback']})"
        )

    if dry_run:
        print("ℹ️ dry-run 모드: 실제 시트 업데이트는 수행하지 않았습니다.")
        return

    if total_rows <= 0:
        print("✅ 백필 대상 데이터가 없습니다.")
        return

    end_row = total_rows + 1
    price_range = f"S2:S{end_row}"
    trace_range = f"AL2:AP{end_row}"

    try:
        worksheet.update(range_name=price_range, values=payload["price_values"])
        worksheet.update(range_name=trace_range, values=payload["trace_values"])
    except TypeError:
        worksheet.update(price_range, payload["price_values"])
        worksheet.update(trace_range, payload["trace_values"])

    print(f"✅ 백필 완료: {price_range}, {trace_range}")


CHAT_MESSAGE_LINE_RE = re.compile(r"^\[(?P<sender>[^\]]+)\]\s+\[[^\]]+\]\s*(?P<content>.*)$")
CHAT_UID_RE = re.compile(r"(?<!\d)(\d{4,5})(?!\d)")
CHAT_PRICE_RANGE_RE = re.compile(r"(\d+(?:[.,;]\d+)?)\s*(억|만|에)?\s*[-~]\s*(\d+(?:[.,;]\d+)?)\s*(억|만|에)?")
CHAT_PRICE_SINGLE_RE = re.compile(r"(\d+(?:[.,;]\d+)?)\s*(억|만)")
CHAT_PRICE_CONCAT_RE = re.compile(r"^\s*(\d+(?:[.,;]\d+)?)\s*(억|만|에)\s*(\d+(?:[.,;]\d+)?)\s*(억|만|에)\s*$")


def _chat_uid_candidates(text):
    out = []
    for m in CHAT_UID_RE.finditer(str(text or "")):
        try:
            num = int(m.group(1))
        except Exception:
            continue
        if 9000 <= num <= 19999:
            out.append(str(num))
    return out


def _normalize_chat_price_num(token):
    t = str(token or "").strip()
    t = t.replace(";", ".").replace(",", ".").replace("..", ".")
    t = re.sub(r"[^0-9.]", "", t)
    if "." not in t and len(t) >= 3 and t.startswith("0"):
        t = f"{t[0]}.{t[1:]}"
    if t.count(".") > 1:
        first = t.find(".")
        t = t[: first + 1] + t[first + 1 :].replace(".", "")
    return t.strip(".")


def _extract_chat_claim_value(line_text):
    src = str(line_text or "").strip()
    if not src:
        return "", ""
    src = src.replace("－", "-").replace("–", "-").replace("—", "-")

    m = CHAT_PRICE_RANGE_RE.search(src)
    if m:
        left, unit_l, right, unit_r = m.groups()
        unit = (unit_r if unit_r and unit_r != "에" else unit_l) or "억"
        left_n = _normalize_chat_price_num(left)
        right_n = _normalize_chat_price_num(right)
        if left_n and right_n:
            return f"{left_n}{unit}~{right_n}{unit}", "range"

    m_concat = CHAT_PRICE_CONCAT_RE.match(src)
    if m_concat:
        left, unit_l, right, unit_r = m_concat.groups()
        unit_left = "억" if unit_l == "에" else unit_l
        unit_right = "억" if unit_r == "에" else unit_r
        left_n = _normalize_chat_price_num(left)
        right_n = _normalize_chat_price_num(right)
        if left_n and right_n:
            return f"{left_n}{unit_left}~{right_n}{unit_right}", "range"

    m2 = CHAT_PRICE_SINGLE_RE.search(src)
    if m2:
        val, unit = m2.groups()
        val_n = _normalize_chat_price_num(val)
        if val_n:
            return f"{val_n}{unit}", "single"

    if "계약완료" in src:
        return "완료", "status"
    for token in ("협의중", "협의", "보류", "완료", "삭제"):
        if token in src:
            return token, "status"
    return "", ""


def _repair_chat_uid_typo_by_context(assignments):
    fixed = []
    total = len(assignments or [])
    for i, row in enumerate(assignments or []):
        item = dict(row or {})
        uid_txt = str(item.get("uid", "")).strip()
        if not uid_txt.isdigit():
            fixed.append(item)
            continue

        uid_num = int(uid_txt)
        # Typo patch: 1179x 구간에서 1479x로 오입력된 패턴(예: 14794)을
        # 앞뒤 UID 문맥(11793, 11795)으로 보정한다.
        if not (14000 <= uid_num <= 14999):
            fixed.append(item)
            continue

        prev_uid = None
        next_uid = None
        for j in range(i - 1, -1, -1):
            cand = str((assignments[j] or {}).get("uid", "")).strip()
            if cand.isdigit():
                prev_uid = int(cand)
                break
        for j in range(i + 1, total):
            cand = str((assignments[j] or {}).get("uid", "")).strip()
            if cand.isdigit():
                next_uid = int(cand)
                break

        if (
            prev_uid is not None
            and next_uid is not None
            and 11000 <= prev_uid <= 12999
            and 11000 <= next_uid <= 12999
            and next_uid - prev_uid == 2
        ):
            expected = prev_uid + 1
            if expected != uid_num and (expected % 1000) == (uid_num % 1000):
                item["uid_original"] = uid_txt
                item["uid"] = str(expected)
                item["uid_inferred"] = True

        fixed.append(item)
    return fixed


def _parse_kakao_claim_updates(chat_file, sender_contains="이우진"):
    path = str(chat_file or "").strip()
    if not path or not os.path.exists(path):
        raise FileNotFoundError(path or "(empty)")

    last_err = None
    text = ""
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            with open(path, "r", encoding=enc) as f:
                text = f.read()
            break
        except Exception as e:
            last_err = e
            text = ""
    if not text:
        raise RuntimeError(f"채팅 파일 인코딩 판독 실패: {last_err}")

    updates = {}
    assignments = []
    pending_uids = []
    current_sender = ""
    sender_filter = str(sender_contains or "").strip()

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = str(raw_line or "").rstrip()
        if not line:
            continue
        if line.startswith("---------------"):
            pending_uids = []
            continue

        m = CHAT_MESSAGE_LINE_RE.match(line)
        if m:
            pending_uids = []
            current_sender = str(m.group("sender") or "").strip()
            content = str(m.group("content") or "").strip()
        else:
            content = line.strip()

        if not content:
            continue
        if sender_filter and sender_filter not in current_sender:
            continue

        uids = _chat_uid_candidates(content)
        claim, claim_kind = _extract_chat_claim_value(content)

        if len(uids) > 1:
            # "11743 ... 10441 당김"처럼 참조 번호가 같이 붙는 라인이 많아
            # 기본적으로 첫 번호만 실제 대상 UID로 사용한다.
            uids = [uids[0]]

        if uids:
            pending_uids.extend(uids)
            if claim:
                target_uid = str(uids[-1]).strip()
                assignments.append(
                    {
                        "uid": target_uid,
                        "claim": claim,
                        "claim_kind": claim_kind,
                        "line_no": line_no,
                        "sender": current_sender,
                        "raw_line": content,
                    }
                )
                if target_uid in pending_uids:
                    pending_uids.remove(target_uid)
                continue

        # UID가 없는 줄은 범위/상태만 이어받고, 단일숫자는 오탐이 많아 제외
        if claim and pending_uids and claim_kind in {"range", "status"}:
            target_uid = str(pending_uids.pop(0)).strip()
            assignments.append(
                {
                    "uid": target_uid,
                    "claim": claim,
                    "claim_kind": claim_kind,
                    "line_no": line_no,
                    "sender": current_sender,
                    "raw_line": content,
                }
            )

    for row in _repair_chat_uid_typo_by_context(assignments):
        uid = str((row or {}).get("uid", "")).strip()
        if not uid:
            continue
        updates[uid] = {
            "uid": uid,
            "claim": str((row or {}).get("claim", "")).strip(),
            "claim_kind": str((row or {}).get("claim_kind", "")).strip(),
            "line_no": int((row or {}).get("line_no", 0) or 0),
            "sender": str((row or {}).get("sender", "")),
            "raw_line": str((row or {}).get("raw_line", "")),
            "uid_original": str((row or {}).get("uid_original", "")).strip(),
            "uid_inferred": bool((row or {}).get("uid_inferred", False)),
        }

    return updates


def _claim_to_primary_price(claim_value):
    claim = str(claim_value or "").strip()
    if not claim:
        return ""

    m = CHAT_PRICE_RANGE_RE.search(claim.replace("~", "-"))
    if m:
        _left, _unit_l, right, unit_r = m.groups()
        unit = (unit_r if unit_r and unit_r != "에" else _unit_l) or "억"
        right_n = _normalize_chat_price_num(right)
        if right_n:
            return f"{right_n}{unit}"

    m2 = CHAT_PRICE_SINGLE_RE.search(claim)
    if m2:
        val, unit = m2.groups()
        val_n = _normalize_chat_price_num(val)
        if val_n:
            return f"{val_n}{unit}"

    if any(x in claim for x in ("협의", "보류", "완료", "삭제")):
        return "협의"
    return ""


def _claim_to_status_label(claim_value):
    claim = _compact_text(claim_value)
    if not claim:
        return ""
    if any(x in claim for x in ("삭제", "계약완료", "완료")):
        return "완료"
    if "보류" in claim:
        return "보류"
    if "계약가능" in claim or "가능" in claim:
        return "가능"
    return ""


def _claim_to_subject_value(claim_value):
    claim = _compact_text(claim_value)
    if not claim:
        return ""
    if any(x in claim for x in ("삭제", "계약완료", "완료", "보류")):
        return ""
    if "협의" in claim and not re.search(r"\d", claim):
        return "협의"
    return _claim_to_primary_price(claim)


def _extract_site_wr_id(text):
    src = str(text or "").strip()
    if not src:
        return 0
    m = re.search(r"/mna/(\d+)", src)
    if not m:
        m = re.search(r"[?&]wr_id=(\d+)", src)
    if not m:
        return 0
    try:
        wr_id = int(m.group(1))
    except Exception:
        return 0
    return wr_id if wr_id > 0 else 0


def _build_site_public_listing_url(site_url, board_slug, wr_id):
    wr_id_num = int(wr_id or 0)
    if wr_id_num <= 0:
        return ""
    base = str(site_url or "").rstrip("/")
    slug = str(board_slug or "").strip().strip("/")
    if not base or not slug:
        return ""
    return f"{base}/{slug}/{wr_id_num}"


def _resolve_publish_listing_result(publisher, item, publish_result, max_pages=0):
    out = dict(publish_result or {})
    uid = str((item or {}).get("uid", "")).strip()
    wr_id = _extract_site_wr_id(out.get("url", ""))
    if wr_id <= 0 and uid:
        discovered, diag = _discover_site_wr_map_from_board(
            publisher,
            [uid],
            max_pages=max_pages,
        )
        wr_id = int(discovered.get(uid, 0) or 0)
        out["wr_resolution"] = {
            "uid": uid,
            "wr_id": wr_id,
            "scanned_pages": int(diag.get("scanned_pages", 0)),
            "scanned_wr_ids": int(diag.get("scanned_wr_ids", 0)),
        }
    if wr_id > 0:
        out["wr_id"] = wr_id
        out["url"] = _build_site_public_listing_url(
            getattr(publisher, "site_url", SITE_URL),
            getattr(publisher, "board_slug", MNA_BOARD_SLUG),
            wr_id,
        )
    else:
        out["wr_id"] = 0
    return out


def _seed_site_wr_map_from_upload_state():
    out = {}
    state = _load_upload_state(UPLOAD_STATE_FILE)
    uploaded = state.get("uploaded_uids", {}) if isinstance(state, dict) else {}
    if not isinstance(uploaded, dict):
        return out
    for raw_uid, data in uploaded.items():
        uid = str(raw_uid or "").strip()
        if not uid:
            continue
        row = data if isinstance(data, dict) else {}
        wr_id = _extract_site_wr_id(row.get("url", ""))
        if wr_id > 0:
            out[uid] = wr_id
    return out


def _discover_site_wr_map_from_board(publisher, target_uids, max_pages=0):
    targets = {str(uid or "").strip() for uid in (target_uids or []) if str(uid or "").strip()}
    out = {}
    if not targets:
        return out, {"scanned_pages": 0, "scanned_wr_ids": 0}

    scan_pages = int(max_pages or 0)
    if scan_pages <= 0:
        scan_pages = 80

    try:
        wr_ids, scanned_pages = _collect_seoul_wr_ids(publisher, max_pages=scan_pages, delay_sec=0.0)
    except Exception as e:
        print(f"   ⚠️ UID→WR 탐색 실패(목록 수집): {e}")
        return out, {"scanned_pages": 0, "scanned_wr_ids": 0}

    scanned_wr_ids = 0
    for wr_id in sorted(set(wr_ids), reverse=True):
        if len(out) >= len(targets):
            break
        scanned_wr_ids += 1
        try:
            _action_url, payload, _form, _form_html = publisher.get_edit_payload(wr_id)
        except Exception:
            continue

        uid = _extract_uid_from_admin_memo(payload.get("wr_20", ""))
        if not uid:
            for key in ("wr_link1", "wr_link2"):
                uid = extract_id_strict(payload.get(key, ""))
                if uid:
                    break
        if uid and uid in targets and uid not in out:
            out[uid] = int(wr_id)

    return out, {"scanned_pages": int(scanned_pages), "scanned_wr_ids": int(scanned_wr_ids)}


def run_restore_claim_from_kakao(
    chat_file="",
    sender_contains="이우진",
    dry_run=False,
    max_updates=0,
    update_price=False,
    apply_site=False,
    site_delay_sec=0.0,
    uid_min=0,
    uid_max=0,
):
    path = str(chat_file or "").strip()
    site_delay_sec = max(0.0, float(site_delay_sec or 0.0))
    if not path:
        print("❌ 복구 실패: --restore-claim-file 경로가 비어 있습니다.")
        return
    if not os.path.exists(path):
        print(f"❌ 복구 실패: 파일을 찾을 수 없습니다: {path}")
        return

    try:
        parsed = _parse_kakao_claim_updates(path, sender_contains=sender_contains)
    except Exception as e:
        print(f"❌ 복구 실패: 채팅 파싱 오류 ({e})")
        return

    uid_min = max(0, int(uid_min or 0))
    uid_max = max(0, int(uid_max or 0))
    if uid_min or uid_max:
        filtered = {}
        for uid_key, data in dict(parsed or {}).items():
            try:
                uid_num = int(str(uid_key).strip())
            except Exception:
                continue
            if uid_min and uid_num < uid_min:
                continue
            if uid_max and uid_num > uid_max:
                continue
            filtered[str(uid_num)] = data
        parsed = filtered

    if not parsed:
        print("ℹ️ 복구 대상이 없습니다. (UID/가격 추출 0건)")
        return

    print(
        f"🧩 카카오 파싱 완료: UID {len(parsed)}건 "
        f"(sender contains='{sender_contains or '-'}'"
        f"{f', uid>={uid_min}' if uid_min else ''}"
        f"{f', uid<={uid_max}' if uid_max else ''})"
    )

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        worksheet = client.open(SHEET_NAME).sheet1
        all_values = worksheet.get_all_values()
    except Exception as e:
        print(f"❌ 복구 실패: 시트 연결 오류 ({e})")
        return

    rows = all_values[1:] if len(all_values) > 1 else []
    changes = []
    seen_uids = set()
    site_wr_seed = _seed_site_wr_map_from_upload_state() if apply_site else {}

    for idx, row in enumerate(rows, start=2):
        uid = ""
        for col_idx in (34, 33, 32):
            cand = extract_id_strict(_row_text(row, col_idx))
            if cand:
                uid = cand
                break
        if not uid:
            continue
        if uid not in parsed:
            continue

        seen_uids.add(uid)
        claim_data = parsed.get(uid, {}) or {}
        claim_val = _compact_text(claim_data.get("claim", ""))
        claim_kind = _compact_text(claim_data.get("claim_kind", ""))
        if not claim_val:
            continue

        license_text = _compact_text(_row_text(row, 2))
        if license_text:
            target_claim = f"{uid} {license_text}\n{claim_val}"
        else:
            target_claim = f"{uid}\n{claim_val}"

        current_claim = _row_text(row, 33)
        need_claim = _normalize_compare_text(current_claim) != _normalize_compare_text(target_claim)

        target_price = ""
        current_price = _row_text(row, 18)
        need_price = False
        if update_price:
            target_price = _claim_to_primary_price(claim_val)
            if target_price:
                need_price = _normalize_compare_text(current_price) != _normalize_compare_text(target_price)

        site_target_status = _claim_to_status_label(claim_val) if apply_site else ""
        site_target_subject = ""
        if apply_site:
            # 서울건설정보 공개 양도가는 항상 "협의"로 유지한다.
            # (삭제/완료 상태 전환 건은 제목 강제 변경을 하지 않는다.)
            if site_target_status != "완료":
                site_target_subject = "협의"
        site_wr_id = int(site_wr_seed.get(uid, 0) or 0)
        need_site = bool(apply_site and (site_target_status or site_target_subject or need_claim))

        if not need_claim and not need_price and not need_site:
            continue

        changes.append(
            {
                "row_idx": idx,
                "uid": uid,
                "claim_kind": claim_kind,
                "line_no": int(claim_data.get("line_no", 0) or 0),
                "raw_line": str(claim_data.get("raw_line", "")),
                "current_claim": current_claim,
                "target_claim": target_claim,
                "current_price": current_price,
                "target_price": target_price,
                "need_claim": bool(need_claim),
                "need_price": bool(need_price),
                "site_wr_id": site_wr_id,
                "site_target_status": site_target_status,
                "site_target_subject": site_target_subject,
                "need_site": bool(need_site),
            }
        )

    changes = sorted(
        changes,
        key=lambda row: (
            int((row or {}).get("line_no", 0) or 0),
            int(re.sub(r"\D+", "", str((row or {}).get("uid", "") or "0")) or 0),
            int((row or {}).get("row_idx", 0) or 0),
        ),
    )

    missing_uids = sorted([uid for uid in parsed.keys() if uid not in seen_uids], key=lambda x: int(x))
    max_updates = max(0, int(max_updates or 0))
    if max_updates > 0:
        changes = changes[:max_updates]

    print(
        f"🧾 복구 대상: {len(changes)}건 "
        f"(시트 미존재 UID {len(missing_uids)}건)"
        f"{' / 양도가 동시복구 ON' if update_price else ''}"
        f"{' / 사이트반영 ON(수동)' if apply_site else ''}"
    )
    for row in changes[:20]:
        extra = ""
        if row.get("need_price"):
            extra = f" / S: '{row['current_price']}' -> '{row['target_price']}'"
        if row.get("need_site"):
            parts = []
            if row.get("site_target_status"):
                parts.append(f"상태->{row['site_target_status']}")
            if row.get("site_target_subject"):
                parts.append(f"양도가->{row['site_target_subject']}")
            if parts:
                extra += f" / SITE[{row.get('site_wr_id')}] " + ", ".join(parts)
        print(
            f"   - L{row['line_no']} / R{row['row_idx']} UID {row['uid']} "
            f"AH: '{_compact_text(row['current_claim'])}' -> '{_compact_text(row['target_claim'])}'"
            f"{extra}"
        )
    if missing_uids:
        preview = ", ".join(missing_uids[:20])
        print(f"   - 시트 미존재 UID 샘플: {preview}{' ...' if len(missing_uids) > 20 else ''}")

    os.makedirs("logs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = os.path.join("logs", f"claim_restore_{ts}.json")
    report_csv = os.path.join("logs", f"claim_restore_{ts}.csv")
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "chat_file": path,
                "sender_contains": sender_contains,
                "dry_run": bool(dry_run),
                "update_price": bool(update_price),
                "apply_site": bool(apply_site),
                "site_delay_sec": site_delay_sec,
                "parsed_uids": len(parsed),
                "changes": changes,
                "missing_uids": missing_uids,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    with open(report_csv, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "line_no",
            "row_idx",
            "uid",
            "claim_kind",
            "need_claim",
            "need_price",
            "need_site",
            "site_wr_id",
            "site_target_status",
            "site_target_subject",
            "current_claim",
            "target_claim",
            "current_price",
            "target_price",
            "raw_line",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in changes:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"🧾 리포트 저장: {report_json}")
    print(f"🧾 리포트 저장: {report_csv}")

    if dry_run:
        print("ℹ️ dry-run 모드: 실제 시트/사이트 업데이트는 수행하지 않았습니다.")
        return

    if not changes:
        print("✅ 적용할 변경이 없습니다.")
        return

    batch_payload = []
    for row in changes:
        row_idx = int(row["row_idx"])
        if row.get("need_claim"):
            batch_payload.append({"range": f"AH{row_idx}", "values": [[row["target_claim"]]]})
        if row.get("need_price"):
            batch_payload.append({"range": f"S{row_idx}", "values": [[row["target_price"]]]})

    applied = 0
    chunk_size = 200
    for i in range(0, len(batch_payload), chunk_size):
        chunk = batch_payload[i : i + chunk_size]
        worksheet.batch_update(chunk)
        applied += len(chunk)

    print(f"✅ 청구 양도가 원상 복구 완료: {len(changes)}행 (셀 갱신 {applied}건)")

    if not apply_site:
        return

    site_target_rows = [
        row
        for row in changes
        if (
            str(row.get("site_target_status", "")).strip()
            or str(row.get("site_target_subject", "")).strip()
            or bool(row.get("need_claim"))
        )
    ]
    if not site_target_rows:
        print("ℹ️ 사이트 상세 반영 대상이 없습니다.")
        return

    # 반드시 시트(AH/S) 반영 이후의 최신 기준으로 관리자메모를 생성한다.
    sheet_basis_map = {}
    try:
        target_uids = [str(row.get("uid", "")).strip() for row in site_target_rows if str(row.get("uid", "")).strip()]
        if target_uids:
            sheet_basis_map = _load_sheet_basis_map(target_uids)
    except Exception as e:
        print(f"   ⚠️ 사이트반영용 시트 기준값 로드 실패(메모 fallback 사용): {e}")
        sheet_basis_map = {}

    admin_id = str(CONFIG.get("ADMIN_ID", "")).strip()
    admin_pw = str(CONFIG.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        print("❌ 사이트 반영 실패: ADMIN_ID/ADMIN_PW 미설정")
        return

    publisher = MnaBoardPublisher(SITE_URL, MNA_BOARD_SLUG, admin_id, admin_pw)
    try:
        publisher.login()
    except Exception as e:
        print(f"❌ 사이트 반영 실패: 로그인 오류 ({e})")
        return

    unresolved_uids = sorted(
        {
            str(row.get("uid", "")).strip()
            for row in site_target_rows
            if str(row.get("uid", "")).strip() and int(row.get("site_wr_id", 0) or 0) <= 0
        },
        key=lambda x: int(x) if str(x).isdigit() else 0,
    )
    if unresolved_uids:
        discovered, diag = _discover_site_wr_map_from_board(
            publisher,
            unresolved_uids,
            max_pages=RECONCILE_SEOUL_MAX_PAGES,
        )
        for row in site_target_rows:
            uid = str(row.get("uid", "")).strip()
            if uid and int(row.get("site_wr_id", 0) or 0) <= 0:
                row["site_wr_id"] = int(discovered.get(uid, 0) or 0)
        mapped = len([uid for uid in unresolved_uids if int(discovered.get(uid, 0) or 0) > 0])
        print(
            f"🔎 UID→WR 탐색: 대상 {len(unresolved_uids)}건 / 매핑 {mapped}건 "
            f"(pages={diag.get('scanned_pages', 0)}, wr_scan={diag.get('scanned_wr_ids', 0)})"
        )
        still_unresolved = [uid for uid in unresolved_uids if int(discovered.get(uid, 0) or 0) <= 0]
        if still_unresolved:
            preview = ", ".join(still_unresolved[:20])
            print(
                "   ⚠️ WR 미확인 UID: "
                f"{preview}{' ...' if len(still_unresolved) > 20 else ''}"
            )

    site_candidates = [
        row
        for row in site_target_rows
        if int(row.get("site_wr_id", 0) or 0) > 0
    ]
    if not site_candidates:
        print("ℹ️ 사이트 상세 반영 대상이 없습니다. (UID→WR 매핑 실패)")
        return

    limit_info = publisher.daily_limit_summary()
    print(
        f"🧮 일일 상한: 요청 {limit_info['requests']}/{limit_info['request_cap']} / "
        f"수정 {limit_info['writes']}/{limit_info['write_cap']} "
        f"(state={limit_info['state_file']})"
    )

    site_stats = {"updated": 0, "same": 0, "failed": 0}
    for idx, row in enumerate(site_candidates, start=1):
        uid = str(row.get("uid", "")).strip()
        wr_id = int(row.get("site_wr_id", 0) or 0)
        target_status = str(row.get("site_target_status", "")).strip()
        target_subject = str(row.get("site_target_subject", "")).strip()
        try:
            action_url, payload, form, _ = publisher.get_edit_payload(wr_id)
            updates = {}

            if target_status:
                status_map = _select_label_value_map(form, "wr_17")
                status_val = _select_value_from_text(status_map, target_status)
                current_status = str(payload.get("wr_17", "")).strip()
                if status_val and current_status != status_val:
                    updates["wr_17"] = status_val

            if target_subject:
                current_subject = _compact_text(payload.get("wr_subject", ""))
                if _normalize_compare_text(current_subject) != _normalize_compare_text(target_subject):
                    updates["wr_subject"] = target_subject

            basis = dict(sheet_basis_map.get(uid, {}) or {})
            if not basis:
                basis = {
                    "sheet_price": str(row.get("target_price", "")).strip() or str(row.get("current_price", "")).strip(),
                    "sheet_claim_price": str(row.get("target_claim", "")).strip(),
                }
            target_memo = _build_admin_memo_from_sheet_basis(
                uid,
                payload.get("wr_20", ""),
                payload,
                basis,
            )
            current_memo = str(payload.get("wr_20", "") or "")
            if _normalize_compare_text(current_memo) != _normalize_compare_text(target_memo):
                updates["wr_20"] = target_memo

            if not updates:
                site_stats["same"] += 1
                print(f"   - [SITE {idx}/{len(site_candidates)}] WR {wr_id}/UID {uid}: 동일 -> 스킵")
                continue

            publisher.submit_edit_updates(action_url, payload, updates)
            site_stats["updated"] += 1
            changed = ",".join(sorted(updates.keys()))
            print(f"   ✅ [SITE {idx}/{len(site_candidates)}] WR {wr_id}/UID {uid}: 반영 ({changed})")
            if site_delay_sec > 0:
                time.sleep(site_delay_sec)
        except Exception as e:
            site_stats["failed"] += 1
            print(f"   ❌ [SITE {idx}/{len(site_candidates)}] WR {wr_id}/UID {uid}: 반영 실패 ({e})")

    print(
        f"✅ 사이트 상세 반영 완료: 대상 {len(site_candidates)}건 / "
        f"반영 {site_stats['updated']} / 동일 {site_stats['same']} / 실패 {site_stats['failed']}"
    )


def run_yangdo_estimation(uid="", limit=0, only_missing=False, sync_sheet=True, top_k=12, min_score=26.0):
    print("📈 [Estimate] 양도가 산정 실행...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        book = client.open(SHEET_NAME)
        source_ws = book.sheet1
        all_values = source_ws.get_all_values()
    except Exception as e:
        print(f"❌ 산정용 시트 연결 실패: {e}")
        return

    rows, meta = _build_yangdo_estimate_rows(
        all_values,
        uid_filter=uid,
        limit=max(0, int(limit or 0)),
        only_missing=bool(only_missing),
        top_k=max(3, int(top_k or 12)),
        min_score=float(min_score or 26.0),
    )
    print(
        f"   학습대상 {meta.get('train_count', 0)}건 / "
        f"평가대상 {meta.get('record_count', 0)}건 / "
        f"산정결과 {len(rows)}건"
    )
    if not rows:
        print("✅ 산정 가능한 행이 없습니다.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("logs", f"yangdo_estimate_{ts}.csv")
    json_path = os.path.join("logs", f"yangdo_estimate_{ts}.json")
    _ensure_parent_dir(csv_path)

    fieldnames = [
        "row",
        "number",
        "uid",
        "license",
        "current_price",
        "claim_price",
        "estimate_center_eok",
        "estimate_low_eok",
        "estimate_high_eok",
        "recommend_range_text",
        "confidence",
        "confidence_score",
        "neighbor_count",
        "avg_similarity",
        "neighbor_uids",
        "judgement",
        "claim_minus_estimate_eok",
        "current_minus_estimate_eok",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = dict(row)
            payload["neighbor_uids"] = ",".join(payload.get("neighbor_uids", []))
            writer.writerow(payload)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    for ex in rows[:10]:
        print(
            "   - "
            f"UID={ex.get('uid','-')} 번호={ex.get('number','-')} "
            f"추정={_fmt_eok_value(ex.get('estimate_center_eok'))} "
            f"범위={ex.get('recommend_range_text','')} "
            f"(conf={ex.get('confidence','')}, n={ex.get('neighbor_count','')})"
        )

    print(f"✅ 산정 리포트 저장: {csv_path}")
    print(f"✅ 산정 리포트 저장: {json_path}")

    if not sync_sheet:
        return

    try:
        try:
            estimate_ws = book.worksheet(TAB_YANGDO_ESTIMATE)
        except Exception:
            estimate_ws = book.add_worksheet(
                title=TAB_YANGDO_ESTIMATE,
                rows=max(1500, len(rows) + 50),
                cols=max(24, len(YANGDO_ESTIMATE_SHEET_HEADERS) + 2),
            )
    except Exception as e:
        print(f"❌ 산정 탭 준비 실패: {e}")
        return

    values = _build_yangdo_estimate_sheet_values(rows)
    end_row = len(values)
    end_col = _col_to_a1(len(YANGDO_ESTIMATE_SHEET_HEADERS))
    range_name = f"A1:{end_col}{end_row}"
    try:
        estimate_ws.clear()
        estimate_ws.update(range_name=range_name, values=values)
    except TypeError:
        estimate_ws.clear()
        estimate_ws.update(range_name, values)
    print(f"✅ 산정 탭 동기화 완료: {TAB_YANGDO_ESTIMATE} ({len(rows)}건)")


def run_low_confidence_report(limit=0, recent_rows=0, recent_numbers=0, skip_reviewed=False):
    print("📊 [Report] low confidence 리포트 생성...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        book = client.open(SHEET_NAME)
        worksheet = book.sheet1
        all_values = worksheet.get_all_values()
        _ensure_price_trace_headers(worksheet, all_values)
        all_values = worksheet.get_all_values()
    except Exception as e:
        print(f"❌ 리포트용 시트 연결 실패: {e}")
        return

    raw_rows = _collect_low_confidence_rows(
        all_values,
        limit=0,
        recent_rows=max(0, int(recent_rows or 0)),
        recent_numbers=max(0, int(recent_numbers or 0)),
    )
    print(f"   원본 low confidence 건수: {len(raw_rows)}건")

    existing_values = []
    if skip_reviewed:
        try:
            review_ws = book.worksheet(TAB_PRICE_REVIEW)
            existing_values = review_ws.get_all_values()
        except Exception as e:
            print(f"   ⚠️ 검수 탭 조회 실패(검수완료 제외 기준 없음): {e}")

    rows, stats = _finalize_low_confidence_rows(
        raw_rows,
        existing_values=existing_values,
        limit=max(0, int(limit or 0)),
        skip_reviewed=skip_reviewed,
    )
    if stats["skipped_reviewed"] > 0:
        print(f"   검수완료 제외: {stats['skipped_reviewed']}건")
    if stats["limited_out"] > 0:
        print(f"   limit 제외: {stats['limited_out']}건")
    if stats["preserved_count"] > 0:
        print(f"   보존된 검수 입력(최종): {stats['preserved_count']}건")
    print(f"   low confidence 건수: {len(rows)}건")
    if not rows:
        print("✅ low confidence 대상이 없습니다.")
        return

    os.makedirs("logs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("logs", f"price_low_confidence_{ts}.csv")
    json_path = os.path.join("logs", f"price_low_confidence_{ts}.json")

    fieldnames = [
        "row",
        "검수우선순위",
        "리스크점수",
        "리스크사유",
        "번호",
        "양도가",
        "가격비식별요약",
        "가격추출소스",
        "가격추출근거요약",
        "가격신뢰도",
        "가격fallback",
        "청구양도가",
        "비고",
        *LOW_CONF_MANUAL_HEADERS,
    ]

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    for ex in rows[:10]:
        print(
            "   - "
            f"R{ex['row']} 번호={ex['번호']} 양도가={ex['양도가']} "
            f"(priority={ex.get('검수우선순위','')}, risk={ex.get('리스크점수','')}, "
            f"source={ex['가격추출소스']}, fallback={ex['가격fallback']})"
        )

    print(f"✅ 리포트 저장: {csv_path}")
    print(f"✅ 리포트 저장: {json_path}")


def run_low_confidence_sheet_sync(limit=0, recent_rows=0, recent_numbers=0, skip_reviewed=False):
    print("📋 [Sync] low confidence 시트 동기화...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        book = client.open(SHEET_NAME)
        source_ws = book.sheet1
        all_values = source_ws.get_all_values()
        _ensure_price_trace_headers(source_ws, all_values)
        all_values = source_ws.get_all_values()
    except Exception as e:
        print(f"❌ 동기화용 시트 연결 실패: {e}")
        return

    raw_rows = _collect_low_confidence_rows(
        all_values,
        limit=0,
        recent_rows=max(0, int(recent_rows or 0)),
        recent_numbers=max(0, int(recent_numbers or 0)),
    )
    print(f"   원본 low confidence 건수: {len(raw_rows)}건")

    try:
        try:
            review_ws = book.worksheet(TAB_PRICE_REVIEW)
        except Exception:
            review_ws = book.add_worksheet(
                title=TAB_PRICE_REVIEW,
                rows=2000,
                cols=max(16, len(LOW_CONF_SHEET_HEADERS) + 2),
            )
    except Exception as e:
        print(f"❌ 검수 탭 준비 실패: {e}")
        return

    try:
        existing_values = review_ws.get_all_values()
    except Exception as e:
        print(f"   ⚠️ 기존 검수 탭 읽기 실패(보존 비활성): {e}")
        existing_values = []

    rows, stats = _finalize_low_confidence_rows(
        raw_rows,
        existing_values=existing_values,
        limit=max(0, int(limit or 0)),
        skip_reviewed=skip_reviewed,
    )
    if stats["preserved_count"] > 0:
        print(f"   보존된 검수 입력(최종): {stats['preserved_count']}건")
    if stats["skipped_reviewed"] > 0:
        print(f"   검수완료 제외: {stats['skipped_reviewed']}건")
    if stats["limited_out"] > 0:
        print(f"   limit 제외: {stats['limited_out']}건")
    rows, autofilled_ts = _autofill_reviewed_timestamp(rows)
    if autofilled_ts > 0:
        print(f"   검수시각 자동기록: {autofilled_ts}건")
    print(f"   최종 low confidence 건수: {len(rows)}건")

    values = _build_low_confidence_sheet_values(rows)
    end_row = len(values)
    end_col = _col_to_a1(len(LOW_CONF_SHEET_HEADERS))
    range_name = f"A1:{end_col}{end_row}"

    try:
        review_ws.clear()
        review_ws.update(range_name=range_name, values=values)
    except TypeError:
        review_ws.clear()
        review_ws.update(range_name, values)

    for ex in rows[:10]:
        print(
            "   - "
            f"R{ex['row']} 번호={ex['번호']} 양도가={ex['양도가']} "
            f"(priority={ex.get('검수우선순위','')}, risk={ex.get('리스크점수','')}, "
            f"source={ex['가격추출소스']}, fallback={ex['가격fallback']})"
        )

    print(f"✅ 검수 탭 동기화 완료: {TAB_PRICE_REVIEW} ({len(rows)}건)")


def _load_json_file(path, default=None):
    if not path or not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json_file(path, data):
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_daily_dashboard(days=7, include_live_counts=False):
    days = max(1, int(days or 7))
    now = datetime.now()
    cutoff = now - timedelta(days=days)

    os.makedirs(RECONCILE_DASHBOARD_DIR, exist_ok=True)
    audit_dir = RECONCILE_AUDIT_DIR
    if not os.path.isdir(audit_dir):
        print(f"⚠️ 대조 리포트 폴더가 없습니다: {audit_dir}")
        return

    audits = []
    for name in sorted(os.listdir(audit_dir), reverse=True):
        if not (name.startswith("reconcile_") and name.endswith(".json")):
            continue
        full = os.path.join(audit_dir, name)
        data = _load_json_file(full, default=None)
        if not isinstance(data, dict):
            continue
        ts = str(data.get("finished_at") or data.get("started_at") or "").strip()
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        audits.append({"path": full, "data": data, "dt": dt})

    audits = sorted(audits, key=lambda x: x.get("dt") or datetime.min, reverse=True)
    agg = {
        "runs": len(audits),
        "same": 0,
        "updated": 0,
        "completed": 0,
        "failed": 0,
        "sheet_updated": 0,
        "sheet_status": 0,
    }
    for row in audits:
        st = dict(row.get("data", {}).get("stats", {}) or {})
        agg["same"] += int(st.get("same", 0) or 0)
        agg["updated"] += int(st.get("updated", 0) or 0)
        agg["completed"] += int(st.get("completed", 0) or 0)
        agg["failed"] += int(st.get("failed", 0) or 0)
        agg["sheet_updated"] += int(st.get("sheet_updated", 0) or 0)
        agg["sheet_status"] += int(st.get("sheet_status_only", 0) or 0)

    failed_uid_map = {}
    for row in audits:
        report = dict(row.get("data", {}) or {})
        for entry in list(report.get("entries", []) or []):
            if not isinstance(entry, dict):
                continue
            uid = _compact_text(entry.get("uid", ""))
            if not uid:
                continue
            result_txt = _compact_text(entry.get("result", "")).lower()
            site_txt = _compact_text(entry.get("site_action", "")).lower()
            sheet_txt = _compact_text(entry.get("sheet_action", "")).lower()
            err_txt = _compact_text(entry.get("error", ""))
            is_failed = (
                ("fail" in result_txt)
                or ("fail" in site_txt)
                or ("fail" in sheet_txt)
                or bool(err_txt)
            )
            if not is_failed:
                continue
            row_uid = failed_uid_map.setdefault(
                uid,
                {
                    "count": 0,
                    "last_wr_id": 0,
                    "last_error": "",
                },
            )
            row_uid["count"] += 1
            wr_id = int(entry.get("wr_id", 0) or 0)
            if wr_id > int(row_uid.get("last_wr_id", 0) or 0):
                row_uid["last_wr_id"] = wr_id
            if err_txt:
                row_uid["last_error"] = err_txt[:160]
    failed_uid_top = sorted(
        (
            {"uid": uid, **vals}
            for uid, vals in failed_uid_map.items()
        ),
        key=lambda x: (-int(x.get("count", 0) or 0), -int(x.get("last_wr_id", 0) or 0), str(x.get("uid", ""))),
    )[:20]

    live = {}
    if include_live_counts:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
            client = gspread.authorize(creds)
            ws = client.open(SHEET_NAME).sheet1
            all_values = ws.get_all_values()
            ctx = _analyze_sheet_rows(all_values)
            low_rows = _collect_low_confidence_rows(all_values, limit=0, recent_rows=0, recent_numbers=0)
            live["sheet_rows"] = int(ctx.get("real_last_row", 1)) - 1
            live["low_confidence"] = len(low_rows)
        except Exception as e:
            live["sheet_error"] = str(e)

        try:
            state = _load_upload_state(UPLOAD_STATE_FILE)
            live["uploaded_state_count"] = len(dict(state.get("uploaded_uids", {}) or {}))
        except Exception as e:
            live["state_error"] = str(e)

    today_name = now.strftime("%Y%m%d")
    dash_path = os.path.join(RECONCILE_DASHBOARD_DIR, f"daily_dashboard_{today_name}.md")
    latest_path = os.path.join(RECONCILE_DASHBOARD_DIR, "latest_daily_dashboard.md")

    lines = [
        f"# 운영 대시보드 ({now.strftime('%Y-%m-%d %H:%M:%S')})",
        "",
        f"- 조회구간: 최근 `{days}`일",
        f"- 대조 실행수: `{agg['runs']}`",
        f"- 콘텐츠/상태 갱신: `{agg['updated']}`",
        f"- 완료처리: `{agg['completed']}`",
        f"- 동일스킵: `{agg['same']}`",
        f"- 실패: `{agg['failed']}`",
        f"- 시트 갱신: `{agg['sheet_updated']}`",
        f"- 시트 상태반영: `{agg['sheet_status']}`",
        "",
    ]
    if live:
        lines.append("## 실시간 지표")
        lines.append("")
        for k, v in live.items():
            lines.append(f"- {k}: `{v}`")
        lines.append("")

    lines.append("## 최근 실행")
    lines.append("")
    for row in audits[:20]:
        d = row.get("data", {})
        st = dict(d.get("stats", {}) or {})
        lines.append(
            f"- `{d.get('finished_at') or d.get('started_at')}` / "
            f"mode={d.get('mode','')} / updated={st.get('updated',0)} / "
            f"completed={st.get('completed',0)} / failed={st.get('failed',0)} / "
            f"path={row.get('path','')}"
        )

    lines.append("")
    lines.append("## 실패 UID Top")
    lines.append("")
    if failed_uid_top:
        for row in failed_uid_top[:10]:
            uid = row.get("uid", "")
            retry_cmd = f"py -3 all.py --uid {uid} --no-upload"
            lines.append(
                f"- UID `{uid}` / 실패 `{row.get('count',0)}`회 / "
                f"last_wr `{row.get('last_wr_id',0)}` / "
                f"retry `{retry_cmd}`"
            )
            if _compact_text(row.get("last_error", "")):
                lines.append(f"  last_error: `{_compact_text(row.get('last_error',''))}`")
    else:
        lines.append("- 실패 UID 없음")

    lines.append("")
    lines.append("## 재시도 명령")
    lines.append("")
    lines.append("- 전체 대조(강제): `py -3 all.py --reconcile-published --reconcile-force`")
    lines.append("- 관리자메모 단건: `py -3 all.py --fix-admin-memo --fix-admin-memo-uid <UID>`")
    lines.append("- 시트 행점프 압축: `py -3 scripts/compact_listing_sheet_rows.py --apply`")

    body = "\n".join(lines).rstrip() + "\n"
    with open(dash_path, "w", encoding="utf-8") as f:
        f.write(body)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(body)

    print(f"📊 대시보드 생성: {dash_path}")
    print(f"📊 최신 링크: {latest_path}")


def run_scheduled_catchup(no_upload=False, reconcile_status_only=True):
    today = datetime.now()
    slot_date = today.date() if today.hour >= SCHEDULE_TARGET_HOUR else (today.date() - timedelta(days=1))
    state = _load_json_file(SCHEDULER_STATE_FILE, default={}) or {}
    last_slot_text = str(state.get("last_slot_date", "")).strip()
    last_slot_date = None
    if last_slot_text:
        try:
            last_slot_date = datetime.strptime(last_slot_text, "%Y-%m-%d").date()
        except Exception:
            last_slot_date = None

    if last_slot_date is not None and last_slot_date >= slot_date:
        print(f"✅ 누락 없음: 마지막 처리 슬롯 {last_slot_date} / 현재 슬롯 {slot_date}")
        return

    missed_days = 1
    if last_slot_date is not None:
        missed_days = max(1, (slot_date - last_slot_date).days)
    missed_days = min(missed_days, SCHEDULE_LOOKBACK_DAYS)

    print(
        f"⏰ 누락 보정 실행: 슬롯 {slot_date} / "
        f"추정 누락 {missed_days}일 / no_upload={no_upload}"
    )
    run_scraper(upload_enabled=not no_upload)
    run_reconcile_published(
        dry_run=False,
        status_only=bool(reconcile_status_only),
        nowmna_max_pages=0,
        seoul_max_pages=0,
        max_updates=0,
        delay_sec=0.0,
        audit_tag="scheduler_catchup",
        allow_sheet_jump=False,
    )

    state["last_slot_date"] = slot_date.strftime("%Y-%m-%d")
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _save_json_file(SCHEDULER_STATE_FILE, state)
    print(f"✅ 누락 보정 완료: state={SCHEDULER_STATE_FILE}")


def main():
    parser = argparse.ArgumentParser(description="양도 매물 수집 + 구글시트 저장 + seoulmna.co.kr 업로드")
    parser.add_argument("--uid", type=str, default="", help="특정 등록번호(uid) 1건만 수집/시트반영/업로드")
    parser.add_argument("--reconcile-published", action="store_true", help="seoul 발행글 vs nowmna 전체 대조(불일치 갱신/삭제건 완료처리)")
    parser.add_argument("--reconcile-nowmna-pages", type=int, default=0, help="nowmna 전체 스캔 페이지 수(0=환경설정값)")
    parser.add_argument("--reconcile-seoul-pages", type=int, default=0, help="seoul 게시글 스캔 페이지 수(0=자동 최대)")
    parser.add_argument("--reconcile-max-updates", type=int, default=0, help="대조 실행 중 실제 변경 상한(0=무제한)")
    parser.add_argument("--reconcile-delay-sec", type=float, default=0.0, help="대조 중 게시글 처리 간 지연초(0=환경설정값)")
    parser.add_argument("--reconcile-dry-run", action="store_true", help="대조 결과만 확인하고 실제 수정/완료처리는 하지 않음")
    parser.add_argument("--reconcile-status-only", action="store_true", help="본문/실적 갱신 없이 상태(가능/보류/완료)만 동기화")
    parser.add_argument("--reconcile-sheet-only", action="store_true", help="seoul 로그인/수정 없이 nowmna↔시트 대조 후 시트만 반영")
    parser.add_argument("--reconcile-force", action="store_true", help="reconcile 실행 잠금/쿨다운 가드를 무시하고 강제 실행")
    parser.add_argument("--reconcile-audit-tag", type=str, default="", help="대조 리포트에 태그 기록")
    parser.add_argument("--reconcile-rollback", type=str, default="", help="대조 스냅샷 JSON 경로(미입력 시 latest) 롤백 실행")
    parser.add_argument("--rollback-dry-run", action="store_true", help="롤백 예정만 출력")
    parser.add_argument("--rollback-limit", type=int, default=0, help="롤백 최대 건수(0=전체)")
    parser.add_argument("--daily-dashboard", action="store_true", help="운영 대시보드(1페이지 MD) 생성")
    parser.add_argument("--dashboard-days", type=int, default=7, help="대시보드 집계 기간(일)")
    parser.add_argument("--dashboard-live", action="store_true", help="대시보드 생성 시 시트 실시간 지표 포함")
    parser.add_argument("--scheduled-catchup", action="store_true", help="예약 누락 보정 실행(수집 + 상태대조)")
    parser.add_argument("--catchup-no-upload", action="store_true", help="누락 보정 시 업로드 생략")
    parser.add_argument("--catchup-full-reconcile", action="store_true", help="누락 보정 시 상태전용이 아닌 전체 대조")
    parser.add_argument("--fix-admin-memo", action="store_true", help="관리자메모(wr_20)를 시트 기준 입금가/양도가로 일괄 교정")
    parser.add_argument("--fix-admin-memo-pages", type=int, default=0, help="관리자메모 교정 대상 게시글 스캔 페이지(0=전체)")
    parser.add_argument("--fix-admin-memo-limit", type=int, default=0, help="관리자메모 교정 최대 건수(0=전체)")
    parser.add_argument("--fix-admin-memo-uid", type=str, default="", help="관리자메모 교정 대상 UID 1건 강제 지정")
    parser.add_argument("--fix-admin-memo-dry-run", action="store_true", help="관리자메모 교정 예정만 출력")
    parser.add_argument("--fix-admin-memo-all", action="store_true", help="원문양도가 문구가 없어도 전체 메모 포맷을 시트 기준으로 교정")
    parser.add_argument("--fix-admin-memo-delay-sec", type=float, default=0.0, help="관리자메모 교정 시 건별 지연초")
    parser.add_argument("--fix-admin-memo-plan-only", action="store_true", help="관리자메모 교정 트래픽 계획만 출력")
    parser.add_argument("--fix-admin-memo-request-buffer", type=int, default=80, help="관리자메모 교정 시 요청 상한 안전버퍼")
    parser.add_argument("--fix-admin-memo-write-buffer", type=int, default=8, help="관리자메모 교정 시 수정 상한 안전버퍼")
    parser.add_argument("--fix-admin-memo-state-file", type=str, default="logs/admin_memo_sync_state.json", help="관리자메모 교정 재개 상태 파일 경로")
    parser.add_argument("--fix-admin-memo-reset-state", action="store_true", help="관리자메모 교정 재개 상태 초기화")
    parser.add_argument("--fix-admin-memo-togun-only", action="store_true", help="관리자메모 교정을 토건/토목건축 대상만 수행")
    parser.add_argument("--fix-admin-memo-license-filter", type=str, default="", help="관리자메모 교정 대상 면허 필터(부분문자열)")
    parser.add_argument("--no-memo-typo-check", action="store_true", help="비고 오타 의심 점검 비활성화")
    parser.add_argument("--memo-typo-fix", action="store_true", help="비고 오타 의심 항목을 동의 기반으로 시트 반영 시 수정")
    parser.add_argument("--memo-typo-approve-all", action="store_true", help="비고 오타 의심 수정 동의 자동 승인")
    parser.add_argument("--memo-typo-approved-uids", type=str, default="", help="오타 수정 사전 동의 UID 목록(콤마/공백 구분)")
    parser.add_argument("--restore-claim-from-kakao", action="store_true", help="카카오톡 대화 원문에서 UID별 최신 청구 양도가를 파싱해 시트(AH) 원복")
    parser.add_argument("--restore-claim-file", type=str, default="", help="카카오톡 대화 export txt 파일 경로")
    parser.add_argument("--restore-claim-sender", type=str, default="이우진", help="복구 기준 발신자 포함 문자열")
    parser.add_argument("--restore-claim-dry-run", action="store_true", help="청구 양도가 원복 예정만 출력")
    parser.add_argument("--restore-claim-max-updates", type=int, default=0, help="청구 양도가 원복 최대 행수(0=전체)")
    parser.add_argument("--restore-claim-update-price", action="store_true", help="청구 양도가 원복 시 양도가(S열)도 함께 복구")
    parser.add_argument("--restore-claim-apply-site", action="store_true", help="청구 양도가 원복 시 seoul 사이트 상세(상태/양도가)도 반영")
    parser.add_argument("--restore-claim-site-delay-sec", type=float, default=0.0, help="사이트 상세 반영 시 건별 지연초")
    parser.add_argument("--restore-claim-min-uid", type=int, default=0, help="청구 양도가 원복 UID 하한(포함, 0=미사용)")
    parser.add_argument("--restore-claim-max-uid", type=int, default=0, help="청구 양도가 원복 UID 상한(포함, 0=미사용)")
    parser.add_argument("--allow-sheet-jump", action="store_true", help="시트 행 점프 watchdog 경고를 무시하고 진행")
    parser.add_argument("--allow-low-quality-upload", action="store_true", help="저품질 콘텐츠 게이트를 무시하고 업로드")
    parser.add_argument("--no-upload", action="store_true", help="사이트 업로드 단계를 건너뜁니다.")
    parser.add_argument("--backfill-price-trace", action="store_true", help="기존 시트 가격/추적 컬럼(C19, AL~AP) 백필")
    parser.add_argument("--backfill-dry-run", action="store_true", help="백필 결과 미리보기만 수행")
    parser.add_argument("--export-low-confidence", action="store_true", help="가격신뢰도 low 리포트(CSV/JSON) 생성")
    parser.add_argument("--sync-low-confidence-sheet", action="store_true", help="가격신뢰도 low 행을 검수 탭에 동기화")
    parser.add_argument("--low-limit", type=int, default=0, help="low 리포트 최대 건수(0=전체)")
    parser.add_argument("--low-recent-rows", type=int, default=0, help="최근 N개 행만 low 대상에 포함(0=전체)")
    parser.add_argument("--low-recent-numbers", type=int, default=0, help="최신 등록번호 상위 N개만 low 대상에 포함(0=전체)")
    parser.add_argument("--low-skip-reviewed", action="store_true", help="검수완료(Y/완료/true 등) 행 제외")
    parser.add_argument("--estimate-yangdo", action="store_true", help="시트 기반 정밀 양도가 산정 리포트/탭 생성")
    parser.add_argument("--estimate-uid", type=str, default="", help="양도가 산정 대상 UID 1건")
    parser.add_argument("--estimate-limit", type=int, default=0, help="양도가 산정 최대 건수(0=전체)")
    parser.add_argument("--estimate-only-missing", action="store_true", help="현재 양도가 숫자가 없는 행만 산정")
    parser.add_argument("--estimate-no-sheet-sync", action="store_true", help="양도가 산정 결과를 시트 탭에 쓰지 않음")
    parser.add_argument("--estimate-top-k", type=int, default=12, help="양도가 산정 시 유사 매물 참조 건수")
    parser.add_argument("--estimate-min-score", type=float, default=26.0, help="양도가 산정 유사도 최소 점수")
    parser.add_argument("--build-yangdo-page", action="store_true", help="입력형 양도가 산정 페이지 HTML 생성")
    parser.add_argument("--publish-yangdo-page", action="store_true", help="입력형 양도가 산정 페이지를 seoulmna 게시판에 생성/수정")
    parser.add_argument("--yangdo-page-output", type=str, default="", help="양도가 산정 페이지 HTML 저장 경로")
    parser.add_argument("--yangdo-page-subject", type=str, default="", help="양도가 산정 페이지 게시 제목")
    parser.add_argument("--yangdo-page-wr-id", type=int, default=0, help="양도가 산정 페이지 기존 wr_id(입력 시 수정 모드)")
    parser.add_argument("--yangdo-page-board-slug", type=str, default="", help="양도가 산정 페이지 게시 보드 slug(미입력시 설정값/기본 mna)")
    parser.add_argument("--yangdo-page-mode", type=str, default=YANGDO_CALCULATOR_MODE, choices=["customer", "owner"], help="양도가 산정 페이지 뷰 모드(customer|owner)")
    parser.add_argument("--yangdo-page-max-train-rows", type=int, default=0, help="양도가 산정 페이지 학습데이터 상한(0=전체)")
    parser.add_argument(
        "--confirm-bulk",
        type=str,
        default="",
        help="대량 수정 실행 확인 토큰. 고위험 실행 시 `--confirm-bulk YES`가 필요합니다.",
    )
    args = parser.parse_args()
    approved_uid_raw = args.memo_typo_approved_uids or " ".join(sorted(MEMO_TYPO_APPROVED_UIDS))
    _configure_memo_typo_runtime(
        check=(bool(MEMO_TYPO_CHECK) and not args.no_memo_typo_check),
        fix=(bool(MEMO_TYPO_FIX) or args.memo_typo_fix),
        approve_all=(bool(MEMO_TYPO_APPROVE_ALL) or args.memo_typo_approve_all),
        approved_uids=approved_uid_raw,
    )

    def _bulk_warning_reasons() -> list:
        reasons = []
        # 게시글/시트 대조를 무제한으로 실제 반영하는 경우
        if bool(args.reconcile_published) and (not bool(args.reconcile_dry_run)):
            if int(args.reconcile_max_updates or 0) == 0:
                reasons.append("reconcile-published apply (무제한 변경 가능)")
        # 롤백 전체 적용
        if str(args.reconcile_rollback or "").strip() and (not bool(args.rollback_dry_run)):
            if int(args.rollback_limit or 0) == 0:
                reasons.append("reconcile-rollback apply (전체 롤백)")
        # 관리자 메모 일괄 교정
        if bool(args.fix_admin_memo) and (not bool(args.fix_admin_memo_dry_run)):
            is_single_uid = bool(str(args.fix_admin_memo_uid or "").strip())
            is_unbounded = bool(args.fix_admin_memo_all) or int(args.fix_admin_memo_limit or 0) == 0
            if (not bool(args.fix_admin_memo_plan_only)) and (not is_single_uid) and is_unbounded:
                reasons.append("fix-admin-memo apply (대량 메모 교정)")
        # 카카오 원문 기반 청구가 원복 대량 적용
        if bool(args.restore_claim_from_kakao) and (not bool(args.restore_claim_dry_run)):
            if int(args.restore_claim_max_updates or 0) == 0:
                reasons.append("restore-claim-from-kakao apply (무제한 원복)")
        # 가격/추적 컬럼 백필 대량 적용
        if bool(args.backfill_price_trace) and (not bool(args.backfill_dry_run)):
            reasons.append("backfill-price-trace apply (대량 시트 업데이트)")
        # 양도가 산정 결과를 시트에 무제한 동기화
        if bool(args.estimate_yangdo) and (not bool(args.estimate_no_sheet_sync)):
            no_uid_bound = not bool(str(args.estimate_uid or "").strip())
            unlimited = int(args.estimate_limit or 0) == 0
            if no_uid_bound and unlimited:
                reasons.append("estimate-yangdo apply (무제한 산정결과 동기화)")
        return reasons

    bulk_reasons = _bulk_warning_reasons()
    confirm_token = str(args.confirm_bulk or "").strip().upper()
    if bulk_reasons and confirm_token != "YES":
        print("⚠️ 대량 데이터 수정 경고")
        for idx, reason in enumerate(bulk_reasons, start=1):
            print(f"  {idx}. {reason}")
        print("실행을 계속하려면 `--confirm-bulk YES`를 추가하세요.")
        return

    if args.reconcile_rollback is not None and str(args.reconcile_rollback).strip():
        run_reconcile_rollback(
            snapshot_path=args.reconcile_rollback,
            dry_run=args.rollback_dry_run,
            limit=args.rollback_limit,
        )
    elif args.daily_dashboard:
        run_daily_dashboard(days=args.dashboard_days, include_live_counts=args.dashboard_live)
    elif args.scheduled_catchup:
        run_scheduled_catchup(
            no_upload=args.catchup_no_upload,
            reconcile_status_only=(not args.catchup_full_reconcile),
        )
    elif args.fix_admin_memo:
        if str(args.fix_admin_memo_uid or "").strip():
            run_fix_admin_memo_uid(
                uid=args.fix_admin_memo_uid,
                dry_run=args.fix_admin_memo_dry_run,
                include_non_raw=args.fix_admin_memo_all,
                max_pages=args.fix_admin_memo_pages,
                delay_sec=args.fix_admin_memo_delay_sec,
            )
        else:
            run_fix_admin_memo(
                max_pages=args.fix_admin_memo_pages,
                limit=args.fix_admin_memo_limit,
                dry_run=args.fix_admin_memo_dry_run,
                include_non_raw=args.fix_admin_memo_all,
                togun_only=args.fix_admin_memo_togun_only,
                license_filter=args.fix_admin_memo_license_filter,
                delay_sec=args.fix_admin_memo_delay_sec,
                request_buffer=args.fix_admin_memo_request_buffer,
                write_buffer=args.fix_admin_memo_write_buffer,
                plan_only=args.fix_admin_memo_plan_only,
                state_file=args.fix_admin_memo_state_file,
                reset_state=args.fix_admin_memo_reset_state,
            )
    elif args.restore_claim_from_kakao:
        run_restore_claim_from_kakao(
            chat_file=args.restore_claim_file,
            sender_contains=args.restore_claim_sender,
            dry_run=args.restore_claim_dry_run,
            max_updates=args.restore_claim_max_updates,
            update_price=args.restore_claim_update_price,
            apply_site=args.restore_claim_apply_site,
            site_delay_sec=args.restore_claim_site_delay_sec,
            uid_min=args.restore_claim_min_uid,
            uid_max=args.restore_claim_max_uid,
        )
    elif args.estimate_yangdo:
        run_yangdo_estimation(
            uid=args.estimate_uid,
            limit=args.estimate_limit,
            only_missing=args.estimate_only_missing,
            sync_sheet=(not args.estimate_no_sheet_sync),
            top_k=args.estimate_top_k,
            min_score=args.estimate_min_score,
        )
    elif args.build_yangdo_page or args.publish_yangdo_page:
        run_build_yangdo_calculator_page(
            output_path=args.yangdo_page_output,
            publish=bool(args.publish_yangdo_page),
            wr_id=args.yangdo_page_wr_id,
            subject=args.yangdo_page_subject,
            view_mode=args.yangdo_page_mode,
            board_slug=args.yangdo_page_board_slug,
            max_train_rows=args.yangdo_page_max_train_rows,
        )
    elif args.uid:
        run_single_uid(
            uid=args.uid,
            upload_enabled=not args.no_upload,
            allow_sheet_jump=bool(args.allow_sheet_jump),
            allow_low_quality_upload=bool(args.allow_low_quality_upload),
        )
    elif args.reconcile_published:
        run_reconcile_published(
            nowmna_max_pages=args.reconcile_nowmna_pages,
            seoul_max_pages=args.reconcile_seoul_pages,
            max_updates=args.reconcile_max_updates,
            delay_sec=args.reconcile_delay_sec,
            dry_run=args.reconcile_dry_run,
            status_only=args.reconcile_status_only,
            sheet_only=args.reconcile_sheet_only,
            audit_tag=args.reconcile_audit_tag,
            force_run=args.reconcile_force,
            allow_sheet_jump=bool(args.allow_sheet_jump),
        )
    elif args.backfill_price_trace:
        run_price_trace_backfill(dry_run=args.backfill_dry_run)
    elif args.sync_low_confidence_sheet:
        run_low_confidence_sheet_sync(
            limit=args.low_limit,
            recent_rows=args.low_recent_rows,
            recent_numbers=args.low_recent_numbers,
            skip_reviewed=args.low_skip_reviewed,
        )
    elif args.export_low_confidence:
        run_low_confidence_report(
            limit=args.low_limit,
            recent_rows=args.low_recent_rows,
            recent_numbers=args.low_recent_numbers,
            skip_reviewed=args.low_skip_reviewed,
        )
    else:
        run_scraper(
            upload_enabled=not args.no_upload,
            allow_sheet_jump=bool(args.allow_sheet_jump),
            allow_low_quality_upload=bool(args.allow_low_quality_upload),
        )


if __name__ == "__main__":
    main()




