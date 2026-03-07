# =================================================================
# Construction Blog Auto Generator v3.0
# GUI + scheduler + stronger error handling
# =================================================================

from google import genai
from google.genai import types
import requests
import json
import base64
import os
import pathlib
import time
import random
import re
import sys
import threading
import csv
import math
import hashlib
import atexit
import logging
import subprocess
from html import escape, unescape
from collections import Counter
from difflib import SequenceMatcher
from urllib.parse import urljoin, urlparse, unquote, quote
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# GUI
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Local modules
from kb import CONSTRUCTION_STANDARDS, get_fact_prompt_injection, validate_fact
from utils import setup_logger, retry_request, Notifier, load_config, ProgressCallback, require_config
from internal_linker import InternalLinker, generate_faq_schema, extract_faqs_from_content

# =================================================================
# [Config Load]
# =================================================================
CONFIG = load_config({
    "WP_URL": "https://seoulmna.kr/wp-json/wp/v2",
    "WP_POST_STATUS": "publish",
    "WP_COMMENT_STATUS": "closed",
    "WP_PING_STATUS": "closed",
    "MAIN_SITE": "https://seoulmna.kr",
    "GUIDE_LINK": "https://seoulmna.kr/construction-license-guide/",
    "BRAND_NAME": "서울건설정보",
    "CONSULTANT_NAME": "강지현 행정사",
    "PHONE": "010-9926-8661",
    "KAKAO_OPENCHAT_URL": "https://open.kakao.com/o/syWr1hIe",
    "KAKAO_CHANNEL_NAME": "행정사사무소하랑",
    "KAKAO_CTA_IMAGE_PATH": "kakao_cta.png",
    "KAKAO_CTA_IMAGE_URL": "",
    "BLOG_INLINE_IMAGE_DYNAMIC": True,
    "BLOG_INLINE_IMAGE_MIN": 2,
    "BLOG_INLINE_IMAGE_MAX": 3,
    "RANKMATH_RETEST_ATTEMPTS": 2,
    "RANKMATH_RETEST_TIMEOUT_SEC": 35,
    "RANKMATH_RETEST_FORCE": False,
    "RANKMATH_RETEST_FAIL_DELETE_AND_QUEUE": True,
    "OPENAI_API_KEY": "",
    "OPENAI_SCAN_ENABLED": False,
    "OPENAI_MODEL": "gpt-5-mini",
    "OPENAI_CONTENT_FALLBACK_ENABLED": True,
    "OPENAI_CONTENT_FALLBACK_MODEL": "",
    "OPENAI_EMBED_MODEL": "text-embedding-3-small",
    "LOCAL_LLM_FALLBACK_ENABLED": False,
    "LOCAL_LLM_FALLBACK_ON_ANY_ERROR": False,
    "LOCAL_LLM_MODEL": "qwen2.5:7b-instruct",
    "LOCAL_LLM_ENDPOINT": "http://127.0.0.1:11434/api/generate",
    "LOCAL_LLM_TIMEOUT_SEC": 360,
    "LOCAL_LLM_NUM_PREDICT": 2600,
    "LOCAL_LLM_TEMPERATURE": 0.25,
    "LOCAL_LLM_KEEP_ALIVE": "20m",
    "GENAI_RATE_LIMIT_STATE_FILE": "logs/genai_rate_limit_state.json",
    "GENAI_RATE_LIMIT_DEFAULT_COOLDOWN_SEC": 1800,
    "GENAI_RATE_LIMIT_MIN_COOLDOWN_SEC": 30,
    "GENAI_RATE_LIMIT_MAX_COOLDOWN_SEC": 7200,
    "GENAI_RATE_LIMIT_DAILY_EXHAUST_COOLDOWN_SEC": 43200,
    "SEMANTIC_GUARD_ENABLED": False,
    "SEMANTIC_DUP_THRESHOLD": 0.92,
    "SEARCH_DATA_ENABLED": True,
    "SEARCH_PERFORMANCE_WINDOW_DAYS": 30,
    "SEARCH_CONSOLE_CSV_PATH": "search_console_queries.csv",
    "NAVER_QUERY_CSV_PATH": "naver_queries.csv",
    "GSC_PROPERTY_URL": "",
    "GSC_SERVICE_ACCOUNT_FILE": "service_account.json",
    "HIGH_IMPRESSIONS_THRESHOLD": 60,
    "LOW_CTR_THRESHOLD": 0.012,
    "LIFECYCLE_ENABLED": True,
    "LIFECYCLE_FILE": "content_lifecycle.json",
    "LIFECYCLE_BOOTSTRAP_LIMIT": 40,
    "LIFECYCLE_DAILY_TIME": "00:20",
    "LIFECYCLE_DAILY_LIMIT": 10,
    "PORTFOLIO_CLEANUP_ENABLED": True,
    "PORTFOLIO_CLEANUP_TIME": "00:35",
    "PORTFOLIO_MAX_ACTIONS_PER_DAY": 2,
    "PORTFOLIO_MIN_AGE_DAYS": 30,
    "PORTFOLIO_REWRITE_THRESHOLD": 72.0,
    "PORTFOLIO_DELETE_THRESHOLD": 50.0,
    "PORTFOLIO_LOW_IMPRESSIONS": 40,
    "PORTFOLIO_LOW_CTR": 0.008,
    "PORTFOLIO_LOG_FILE": "content_portfolio_actions.json",
    "PORTFOLIO_DELETE_REPUBLISH_MODE": "deferred",
    "QUERY_REWRITE_ENABLED": True,
    "QUERY_REWRITE_TIME": "00:45",
    "QUERY_REWRITE_QUEUE_FILE": "query_rewrite_queue.json",
    "QUERY_REWRITE_MIN_IMPRESSIONS": 80,
    "QUERY_REWRITE_LOW_CTR": 0.012,
    "QUERY_REWRITE_MIN_SIMILARITY": 0.42,
    "QUERY_REWRITE_MAX_ACTIONS_PER_DAY": 2,
    "QUERY_REWRITE_COOLDOWN_DAYS": 14,
    "SERP_AUDIT_TIME": "01:10",
    "SERP_AUDIT_SCAN_LIMIT": 120,
    "SERP_AUDIT_FILE": "serp_audit.json",
    "SERP_REPAIR_LOG_FILE": "serp_repair_actions.json",
    "SERP_REPAIR_MAX_ACTIONS": 1,
    "TAXONOMY_SYNC_LIMIT": 60,
    "SCHEDULER_LOCK_FILE": "mnakr_scheduler.lock",
    "SCHEDULER_STATE_FILE": "scheduler_state.json",
    "STARTUP_ONCE_STATE_FILE": "logs/startup_blog_once_state.json",
    "STARTUP_ONCE_MAX_ATTEMPTS_PER_DAY": 3,
    "RUN_MISSED_ON_STARTUP": True,
    "MAX_STARTUP_CATCHUP_JOBS": 2,
    "STARTUP_CATCHUP_ALLOW_MAINTENANCE": False,
    "STARTUP_CATCHUP_MIN_LOCAL_HOUR": 9,
    "STARTUP_CATCHUP_MAX_LOCAL_HOUR": 22,
    "PORTFOLIO_REPUBLISH_STATUS": "draft",
    "PORTFOLIO_REPUBLISH_QUEUE_ENABLED": True,
    "PORTFOLIO_REPUBLISH_QUEUE_FILE": "logs/portfolio_republish_queue.json",
    "PORTFOLIO_REPUBLISH_QUEUE_TIME": "22:10",
    "PORTFOLIO_REPUBLISH_WEEKDAY_WINDOW": "09:00-23:00",
    "PORTFOLIO_REPUBLISH_WEEKEND_WINDOW": "14:00-23:00",
    "PORTFOLIO_REPUBLISH_WEEKDAY_LIMIT": 1,
    "PORTFOLIO_REPUBLISH_WEEKEND_LIMIT": 2,
    "PORTFOLIO_REPUBLISH_MAX_RETRIES": 5,
    "AUTO_SCHEDULE_ENABLED": True,
    "AUTO_SCHEDULE_TOP_SLOTS": 3,
    "AUTO_SCHEDULE_RECALC_TIME": "00:10",
    "PUBLISH_PREV_DAY_ENABLED": True,
    "PUBLISH_PREV_DAY_TIME": "21:00",
    "SCHEDULE_ENABLED": False,
    "SCHEDULE_TIME": "09:00",
})

# Logger setup
logger = setup_logger()

BLOG_ALLOWED_HOSTS = {"seoulmna.kr", "www.seoulmna.kr"}
LISTING_HOSTS = {"seoulmna.co.kr", "www.seoulmna.co.kr"}


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


def _validate_wp_domain():
    host = _host_of(CONFIG.get("WP_URL", ""))
    if not host:
        raise ValueError("[domain-guard] WP_URL host is empty.")
    if host in LISTING_HOSTS:
        raise ValueError(
            "[domain-guard] WP_URL points to seoulmna.co.kr(listing). "
            "mnakr.py must target seoulmna.kr WordPress only."
        )
    if host not in BLOG_ALLOWED_HOSTS:
        raise ValueError(
            f"[domain-guard] WP_URL host '{host}' is not allowed. "
            "Use seoulmna.kr for blog automation."
        )
    return host


def _sanitize_runtime_text(text):
    msg = str(text or "")
    msg = msg.encode("utf-8", "ignore").decode("utf-8", "ignore")

    # If mojibake-like question marks dominate, fall back to ASCII-safe output.
    if msg.count("?") >= 2:
        msg = re.sub(r"[^0-9A-Za-z\s\-_.:,;!?()\[\]{}\/\|=+%#@<>]", "", msg)
        msg = re.sub(r"\?{2,}", " ", msg)
        msg = re.sub(r"\s{2,}", " ", msg).strip()
        return msg or "log message"

    # Otherwise keep Hangul + ASCII and drop broken symbols.
    msg = re.sub(r"[^0-9A-Za-z가-힣\s\-_.:,;!?()\[\]{}\/\|=+%#@<>]", "", msg)
    msg = re.sub(r"\s{2,}", " ", msg).strip()
    return msg or "log message"


class _LogSanitizeFilter(logging.Filter):
    def filter(self, record):
        try:
            record.msg = _sanitize_runtime_text(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return True


def _attach_log_sanitize_filter():
    try:
        filt = _LogSanitizeFilter()
        logger.addFilter(filt)
        for handler in logger.handlers:
            handler.addFilter(filt)
    except Exception:
        pass


_attach_log_sanitize_filter()

# 윈도우 콘솔 인코딩
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def ensure_config(required_keys, context):
    """Fail fast with a clear config error."""
    return require_config(CONFIG, required_keys, context=context)


def _normalize_topic(text):
    if not text:
        return ""
    return re.sub(r"[^0-9a-z가-힣]+", "", str(text).lower())


def _normalize_slug_token(text):
    if not text:
        return ""
    try:
        decoded = unquote(str(text))
    except Exception:
        decoded = str(text)
    return _normalize_topic(decoded)


def _strip_markup_tokens(text):
    if not text:
        return ""
    stripped = re.sub(
        r"\[\s*/?\s*(?:PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]",
        " ",
        str(text),
        flags=re.IGNORECASE,
    )
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


def _mojibake_metrics(text):
    plain = _strip_markup_tokens(text)
    if not plain:
        return {
            "double_q": 0,
            "replacement": 0,
            "cjk_count": 0,
            "mixed_token": 0,
            "flagged": False,
        }

    double_q = plain.count("??")
    replacement = plain.count("�")
    cjk_count = sum(1 for c in plain if "一" <= c <= "鿿")
    mixed_token = len(re.findall(r"(?:[?-?][一-鿿]|[一-鿿][?-?])", plain))

    flagged = (
        replacement > 0
        or double_q >= 1
        or mixed_token >= 2
        or cjk_count >= 8
    )
    return {
        "double_q": double_q,
        "replacement": replacement,
        "cjk_count": cjk_count,
        "mixed_token": mixed_token,
        "flagged": flagged,
    }


def _extract_head_snippet(html):
    source = str(html or "")
    title_match = re.search(r"<title>(.*?)</title>", source, flags=re.IGNORECASE | re.DOTALL)
    desc_match = re.search(
        r"<meta\s+name=[\"\']description[\"\']\s+content=[\"\'](.*?)[\"\']",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    title = re.sub(r"\s+", " ", (title_match.group(1) if title_match else "")).strip()
    description = re.sub(r"\s+", " ", (desc_match.group(1) if desc_match else "")).strip()
    return title, description


def _strip_html_text(value):
    source = str(value or "")
    source = re.sub(r"<[^>]+>", " ", source)
    source = re.sub(r"\s+", " ", source).strip()
    return source


def _is_serp_snippet_garbled(title, description):
    title_text = str(title or "").strip()
    desc_text = str(description or "").strip()
    marker_hit = ("???" in title_text) or ("???" in desc_text)
    metrics = _mojibake_metrics(f"{title_text} {desc_text}")
    return {
        "marker_hit": marker_hit,
        "metrics": metrics,
        "flagged": marker_hit or metrics.get("flagged", False),
    }


def _safe_error_text(error):
    if error is None:
        return "원인 미상의 오류. 상세 로그를 확인하세요."
    if isinstance(error, str):
        msg = error.strip()
        if not msg or msg.lower() == "none":
            return "원인 미상의 오류. 상세 로그를 확인하세요."
        return msg
    msg = str(error).strip()
    if not msg or msg.lower() == "none":
        return f"{type(error).__name__} (메시지 없음)"
    return f"{type(error).__name__}: {msg}"


def _raise_for_status_with_context(response, context):
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        body = ""
        try:
            body = str(getattr(response, "text", "") or "").strip().replace("\n", " ")
        except Exception:
            body = ""
        if len(body) > 300:
            body = body[:300].rstrip() + "..."
        detail = f"{context}: status={getattr(response, 'status_code', '?')}"
        if body:
            detail += f", body={body}"
        raise requests.HTTPError(detail) from e


def _sanitize_url(url, allow_schemes=("http", "https"), default=""):
    raw = str(url or "").strip().replace("\r", "").replace("\n", "")
    if not raw:
        return default
    parsed = urlparse(raw)
    scheme = str(parsed.scheme or "").lower()
    if scheme not in set(allow_schemes):
        return default
    if not parsed.netloc:
        return default
    return raw[:700]


def _cfg_bool(name, default=False):
    val = CONFIG.get(name, default)
    if isinstance(val, bool):
        return val
    text = str(val).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _cfg_int(name, default=0):
    val = CONFIG.get(name, default)
    try:
        return int(str(val).strip())
    except Exception:
        return int(default)


def _cfg_float(name, default=0.0):
    val = CONFIG.get(name, default)
    try:
        return float(str(val).strip())
    except Exception:
        return float(default)


class RetryBypassError(RuntimeError):
    """Signals retry decorators to stop immediate retries."""

    def __init__(self, message):
        super().__init__(message)
        self.no_retry = True


def _genai_rate_limit_state_file():
    path = str(CONFIG.get("GENAI_RATE_LIMIT_STATE_FILE", "logs/genai_rate_limit_state.json")).strip()
    return path or "logs/genai_rate_limit_state.json"


def _load_genai_rate_limit_state():
    path = _genai_rate_limit_state_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_genai_rate_limit_state(state):
    path = _genai_rate_limit_state_file()
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state or {}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"genai cooldown state 저장 실패: {_safe_error_text(e)}")


def _parse_iso_utc(ts_text):
    src = str(ts_text or "").strip()
    if not src:
        return None
    try:
        dt = datetime.fromisoformat(src.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_retry_after_seconds(error_text):
    text = str(error_text or "")
    if not text:
        return 0

    patterns = [
        (r"retryDelay\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*s", 1),
        (r"Please retry in\s*([0-9]+(?:\.[0-9]+)?)\s*s", 1),
        (r"retry\s+in\s*([0-9]+(?:\.[0-9]+)?)\s*(minutes?|mins?|m)", 60),
        (r"retry\s+in\s*([0-9]+(?:\.[0-9]+)?)\s*(seconds?|secs?|s)", 1),
        (r"retry\s+after\s*([0-9]+(?:\.[0-9]+)?)\s*(minutes?|mins?|m)", 60),
        (r"retry\s+after\s*([0-9]+(?:\.[0-9]+)?)\s*(seconds?|secs?|s)", 1),
    ]
    for pattern, unit in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue
        try:
            raw = float(m.group(1))
        except Exception:
            continue
        if raw <= 0:
            continue
        return int(math.ceil(raw * unit))
    return 0


def _is_genai_daily_quota_exhausted(error_text):
    text = str(error_text or "")
    if not text:
        return False
    lower = text.lower()
    has_limit_zero = bool(re.search(r"limit\s*[:=]\s*0(\D|$)", lower))
    has_daily_quota_token = any(
        token in lower
        for token in (
            "perday",
            "per-day",
            "requestsperday",
            "inputtokenspermodelperday",
            "freе_tier_requests, limit: 0",
            "free_tier_input_token_count, limit: 0",
        )
    )
    return has_limit_zero and has_daily_quota_token


def _set_genai_rate_limit_cooldown(error, context=""):
    safe = _safe_error_text(error)
    hint_sec = _extract_retry_after_seconds(safe)
    is_daily_exhaust = _is_genai_daily_quota_exhausted(safe)

    min_sec = max(10, _cfg_int("GENAI_RATE_LIMIT_MIN_COOLDOWN_SEC", 30))
    max_sec = max(min_sec, _cfg_int("GENAI_RATE_LIMIT_MAX_COOLDOWN_SEC", 7200))
    default_sec = _cfg_int("GENAI_RATE_LIMIT_DEFAULT_COOLDOWN_SEC", 1800)
    default_sec = max(min_sec, min(max_sec, default_sec))
    daily_exhaust_sec = max(
        min_sec,
        _cfg_int("GENAI_RATE_LIMIT_DAILY_EXHAUST_COOLDOWN_SEC", 43200),
    )

    if is_daily_exhaust:
        cooldown_sec = max(daily_exhaust_sec, hint_sec if hint_sec > 0 else 0)
    else:
        cooldown_sec = hint_sec if hint_sec > 0 else default_sec
        cooldown_sec = max(min_sec, min(max_sec, cooldown_sec))
    until_utc = datetime.now(timezone.utc) + timedelta(seconds=cooldown_sec)

    state = _load_genai_rate_limit_state()
    state.update(
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "context": str(context or "").strip(),
            "reason": safe[:600],
            "retry_delay_hint_sec": int(hint_sec or 0),
            "daily_quota_exhausted": bool(is_daily_exhaust),
            "cooldown_sec": int(cooldown_sec),
            "cooldown_until_utc": until_utc.isoformat(),
        }
    )
    _save_genai_rate_limit_state(state)

    until_local = until_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    mode = "daily-exhaust" if is_daily_exhaust else "retry-hint/default"
    logger.warning(
        f"Gemini cooldown set: {cooldown_sec}s (until {until_local}, context={context or 'unknown'}, mode={mode})"
    )
    return int(cooldown_sec), until_utc


def _get_genai_cooldown_remaining_sec():
    state = _load_genai_rate_limit_state()
    until_utc = _parse_iso_utc(state.get("cooldown_until_utc", ""))
    if until_utc is None:
        return 0, None

    remain = int(math.ceil((until_utc - datetime.now(timezone.utc)).total_seconds()))
    if remain > 0:
        return remain, until_utc

    state["cooldown_until_utc"] = ""
    state["cooldown_sec"] = 0
    state["cooldown_elapsed_at"] = datetime.now(timezone.utc).isoformat()
    _save_genai_rate_limit_state(state)
    return 0, None


def _is_genai_cooldown_active(context=""):
    remain, until_utc = _get_genai_cooldown_remaining_sec()
    if remain <= 0:
        return False
    until_local = until_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z") if until_utc else "-"
    logger.warning(
        f"Gemini cooldown active ({remain}s remaining, until {until_local}). "
        f"Skip {context or 'run'}."
    )
    return True


def _normalize_image_label(value, fallback):
    clean = re.sub(r"\s+", " ", _strip_markup_tokens(value)).strip()
    if not clean:
        return str(fallback)
    return clean[:90]


def _inline_image_plan(content):
    content = dict(content or {})
    section_titles = [
        _normalize_image_label(content.get("body1_title", ""), "Core points"),
        _normalize_image_label(content.get("body2_title", ""), "Checklist"),
        _normalize_image_label(content.get("body3_title", ""), "Action plan"),
    ]
    max_sections = len(section_titles)
    # Policy: body inline images should be 2~3 by default.
    min_cfg = min(max_sections, max(2, _cfg_int("BLOG_INLINE_IMAGE_MIN", 2)))
    max_cfg = min(max_sections, max(min_cfg, _cfg_int("BLOG_INLINE_IMAGE_MAX", 3)))
    dynamic = _cfg_bool("BLOG_INLINE_IMAGE_DYNAMIC", True)

    text_blob = " ".join(
        [
            str(content.get("intro", "")),
            str(content.get("body1_text", "")),
            str(content.get("body2_text", "")),
            str(content.get("body3_text", "")),
            str(content.get("conclusion", "")),
        ]
    )
    plain_chars = len(_strip_markup_tokens(text_blob))
    faq_count = str(text_blob).count("[FAQ]")

    target = min_cfg
    if dynamic:
        target = max(min_cfg, 2)
        if plain_chars >= 4200:
            target += 1
        if faq_count >= 3:
            target += 1
    target = min(max_cfg, max(min_cfg, int(target)))
    titles = section_titles[:target]
    if len(titles) < min_cfg:
        backup = ["핵심 체크포인트", "재무·리스크 점검", "실행 로드맵"]
        for name in backup:
            if len(titles) >= min_cfg:
                break
            titles.append(name)
    return {
        "count": len(titles),
        "titles": titles,
        "plain_chars": plain_chars,
        "faq_count": faq_count,
    }


def _local_inline_media_placeholders(count):
    total = max(0, int(count or 0))
    return [{"source_url": f"https://example.com/inline-{i + 1}.png"} for i in range(total)]


_LAST_PREPUBLISH_GATE = {
    "checked_at": 0.0,
    "ok": False,
    "summary": "",
}


def _decode_subprocess_output(data):
    raw = data or b""
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace")


def _run_mnakr_prepublish_quality_gate(force=False, cache_sec=300):
    now_ts = time.time()
    if (
        (not force)
        and _LAST_PREPUBLISH_GATE.get("ok")
        and (now_ts - float(_LAST_PREPUBLISH_GATE.get("checked_at", 0.0))) <= max(0, int(cache_sec))
    ):
        return True, str(_LAST_PREPUBLISH_GATE.get("summary", "cached pass"))

    runner_path = pathlib.Path(__file__).resolve().parent / "scripts" / "quality_gate_runner.py"
    if not runner_path.exists():
        return False, f"quality gate runner missing: {runner_path}"

    cmd = [
        sys.executable,
        str(runner_path),
        "--contracts",
        "mnakr",
        "--fail-on-warn",
        "--quiet",
    ]
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(runner_path.parent.parent),
            capture_output=True,
            timeout=300,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, "quality gate timeout (>300s)"
    except Exception as e:
        return False, _safe_error_text(e)

    out = _decode_subprocess_output(proc.stdout).strip()
    err = _decode_subprocess_output(proc.stderr).strip()
    summary = out.splitlines()[-1] if out else ""
    if not summary and err:
        summary = err.splitlines()[-1]

    passed = proc.returncode == 0
    _LAST_PREPUBLISH_GATE["checked_at"] = now_ts
    _LAST_PREPUBLISH_GATE["ok"] = passed
    _LAST_PREPUBLISH_GATE["summary"] = summary

    if passed:
        return True, summary or "quality gate passed"
    detail = summary or err or out or f"quality gate failed (rc={proc.returncode})"
    return False, detail[:400]


def _ensure_env_defaults():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        return

    defaults = {
        "KAKAO_OPENCHAT_URL": str(CONFIG.get("KAKAO_OPENCHAT_URL", "")),
        "KAKAO_CHANNEL_NAME": str(CONFIG.get("KAKAO_CHANNEL_NAME", "")),
        "KAKAO_CTA_IMAGE_PATH": str(CONFIG.get("KAKAO_CTA_IMAGE_PATH", "")),
        "KAKAO_CTA_IMAGE_URL": str(CONFIG.get("KAKAO_CTA_IMAGE_URL", "")),
        "BLOG_INLINE_IMAGE_DYNAMIC": str(CONFIG.get("BLOG_INLINE_IMAGE_DYNAMIC", True)).lower(),
        "BLOG_INLINE_IMAGE_MIN": str(CONFIG.get("BLOG_INLINE_IMAGE_MIN", 2)),
        "BLOG_INLINE_IMAGE_MAX": str(CONFIG.get("BLOG_INLINE_IMAGE_MAX", 3)),
        "RANKMATH_RETEST_ATTEMPTS": str(CONFIG.get("RANKMATH_RETEST_ATTEMPTS", 2)),
        "RANKMATH_RETEST_TIMEOUT_SEC": str(CONFIG.get("RANKMATH_RETEST_TIMEOUT_SEC", 35)),
        "RANKMATH_RETEST_FORCE": str(CONFIG.get("RANKMATH_RETEST_FORCE", False)).lower(),
        "RANKMATH_RETEST_FAIL_DELETE_AND_QUEUE": str(CONFIG.get("RANKMATH_RETEST_FAIL_DELETE_AND_QUEUE", True)).lower(),
        "WP_POST_STATUS": str(CONFIG.get("WP_POST_STATUS", "publish")),
        "WP_COMMENT_STATUS": str(CONFIG.get("WP_COMMENT_STATUS", "closed")),
        "WP_PING_STATUS": str(CONFIG.get("WP_PING_STATUS", "closed")),
        "OPENAI_API_KEY": str(CONFIG.get("OPENAI_API_KEY", "")),
        "OPENAI_SCAN_ENABLED": "false",
        "OPENAI_MODEL": str(CONFIG.get("OPENAI_MODEL", "gpt-5-mini")),
        "OPENAI_EMBED_MODEL": str(CONFIG.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")),
        "LOCAL_LLM_FALLBACK_ENABLED": str(CONFIG.get("LOCAL_LLM_FALLBACK_ENABLED", False)).lower(),
        "LOCAL_LLM_FALLBACK_ON_ANY_ERROR": str(CONFIG.get("LOCAL_LLM_FALLBACK_ON_ANY_ERROR", False)).lower(),
        "LOCAL_LLM_MODEL": str(CONFIG.get("LOCAL_LLM_MODEL", "qwen2.5:7b-instruct")),
        "LOCAL_LLM_ENDPOINT": str(CONFIG.get("LOCAL_LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")),
        "LOCAL_LLM_TIMEOUT_SEC": str(CONFIG.get("LOCAL_LLM_TIMEOUT_SEC", 360)),
        "LOCAL_LLM_NUM_PREDICT": str(CONFIG.get("LOCAL_LLM_NUM_PREDICT", 2600)),
        "LOCAL_LLM_TEMPERATURE": str(CONFIG.get("LOCAL_LLM_TEMPERATURE", 0.25)),
        "LOCAL_LLM_KEEP_ALIVE": str(CONFIG.get("LOCAL_LLM_KEEP_ALIVE", "20m")),
        "GENAI_RATE_LIMIT_STATE_FILE": str(CONFIG.get("GENAI_RATE_LIMIT_STATE_FILE", "logs/genai_rate_limit_state.json")),
        "GENAI_RATE_LIMIT_DEFAULT_COOLDOWN_SEC": str(CONFIG.get("GENAI_RATE_LIMIT_DEFAULT_COOLDOWN_SEC", 1800)),
        "GENAI_RATE_LIMIT_MIN_COOLDOWN_SEC": str(CONFIG.get("GENAI_RATE_LIMIT_MIN_COOLDOWN_SEC", 30)),
        "GENAI_RATE_LIMIT_MAX_COOLDOWN_SEC": str(CONFIG.get("GENAI_RATE_LIMIT_MAX_COOLDOWN_SEC", 7200)),
        "GENAI_RATE_LIMIT_DAILY_EXHAUST_COOLDOWN_SEC": str(CONFIG.get("GENAI_RATE_LIMIT_DAILY_EXHAUST_COOLDOWN_SEC", 43200)),
        "SEMANTIC_GUARD_ENABLED": "false",
        "SEMANTIC_DUP_THRESHOLD": str(CONFIG.get("SEMANTIC_DUP_THRESHOLD", 0.92)),
        "SEARCH_DATA_ENABLED": "true",
        "SEARCH_PERFORMANCE_WINDOW_DAYS": str(CONFIG.get("SEARCH_PERFORMANCE_WINDOW_DAYS", 30)),
        "SEARCH_CONSOLE_CSV_PATH": str(CONFIG.get("SEARCH_CONSOLE_CSV_PATH", "search_console_queries.csv")),
        "NAVER_QUERY_CSV_PATH": str(CONFIG.get("NAVER_QUERY_CSV_PATH", "naver_queries.csv")),
        "GSC_PROPERTY_URL": str(CONFIG.get("GSC_PROPERTY_URL", "")),
        "GSC_SERVICE_ACCOUNT_FILE": str(CONFIG.get("GSC_SERVICE_ACCOUNT_FILE", "service_account.json")),
        "HIGH_IMPRESSIONS_THRESHOLD": str(CONFIG.get("HIGH_IMPRESSIONS_THRESHOLD", 60)),
        "LOW_CTR_THRESHOLD": str(CONFIG.get("LOW_CTR_THRESHOLD", 0.012)),
        "LIFECYCLE_ENABLED": "true",
        "LIFECYCLE_FILE": str(CONFIG.get("LIFECYCLE_FILE", "content_lifecycle.json")),
        "LIFECYCLE_BOOTSTRAP_LIMIT": str(CONFIG.get("LIFECYCLE_BOOTSTRAP_LIMIT", 40)),
        "LIFECYCLE_DAILY_TIME": str(CONFIG.get("LIFECYCLE_DAILY_TIME", "00:20")),
        "LIFECYCLE_DAILY_LIMIT": str(CONFIG.get("LIFECYCLE_DAILY_LIMIT", 10)),
        "PORTFOLIO_CLEANUP_ENABLED": "true",
        "PORTFOLIO_CLEANUP_TIME": str(CONFIG.get("PORTFOLIO_CLEANUP_TIME", "00:35")),
        "PORTFOLIO_MAX_ACTIONS_PER_DAY": str(CONFIG.get("PORTFOLIO_MAX_ACTIONS_PER_DAY", 2)),
        "PORTFOLIO_MIN_AGE_DAYS": str(CONFIG.get("PORTFOLIO_MIN_AGE_DAYS", 30)),
        "PORTFOLIO_REWRITE_THRESHOLD": str(CONFIG.get("PORTFOLIO_REWRITE_THRESHOLD", 72.0)),
        "PORTFOLIO_DELETE_THRESHOLD": str(CONFIG.get("PORTFOLIO_DELETE_THRESHOLD", 50.0)),
        "PORTFOLIO_LOW_IMPRESSIONS": str(CONFIG.get("PORTFOLIO_LOW_IMPRESSIONS", 40)),
        "PORTFOLIO_LOW_CTR": str(CONFIG.get("PORTFOLIO_LOW_CTR", 0.008)),
        "PORTFOLIO_LOG_FILE": str(CONFIG.get("PORTFOLIO_LOG_FILE", "content_portfolio_actions.json")),
        "PORTFOLIO_DELETE_REPUBLISH_MODE": str(CONFIG.get("PORTFOLIO_DELETE_REPUBLISH_MODE", "deferred")),
        "QUERY_REWRITE_ENABLED": "true",
        "QUERY_REWRITE_TIME": str(CONFIG.get("QUERY_REWRITE_TIME", "00:45")),
        "QUERY_REWRITE_QUEUE_FILE": str(CONFIG.get("QUERY_REWRITE_QUEUE_FILE", "query_rewrite_queue.json")),
        "QUERY_REWRITE_MIN_IMPRESSIONS": str(CONFIG.get("QUERY_REWRITE_MIN_IMPRESSIONS", 80)),
        "QUERY_REWRITE_LOW_CTR": str(CONFIG.get("QUERY_REWRITE_LOW_CTR", 0.012)),
        "QUERY_REWRITE_MIN_SIMILARITY": str(CONFIG.get("QUERY_REWRITE_MIN_SIMILARITY", 0.42)),
        "QUERY_REWRITE_MAX_ACTIONS_PER_DAY": str(CONFIG.get("QUERY_REWRITE_MAX_ACTIONS_PER_DAY", 2)),
        "QUERY_REWRITE_COOLDOWN_DAYS": str(CONFIG.get("QUERY_REWRITE_COOLDOWN_DAYS", 14)),
        "SERP_AUDIT_TIME": str(CONFIG.get("SERP_AUDIT_TIME", "01:10")),
        "SERP_AUDIT_SCAN_LIMIT": str(CONFIG.get("SERP_AUDIT_SCAN_LIMIT", 120)),
        "SERP_AUDIT_FILE": str(CONFIG.get("SERP_AUDIT_FILE", "serp_audit.json")),
        "SERP_REPAIR_LOG_FILE": str(CONFIG.get("SERP_REPAIR_LOG_FILE", "serp_repair_actions.json")),
        "SERP_REPAIR_MAX_ACTIONS": str(CONFIG.get("SERP_REPAIR_MAX_ACTIONS", 1)),
        "SCHEDULER_LOCK_FILE": str(CONFIG.get("SCHEDULER_LOCK_FILE", "mnakr_scheduler.lock")),
        "SCHEDULER_STATE_FILE": str(CONFIG.get("SCHEDULER_STATE_FILE", "scheduler_state.json")),
        "STARTUP_ONCE_MAX_ATTEMPTS_PER_DAY": str(CONFIG.get("STARTUP_ONCE_MAX_ATTEMPTS_PER_DAY", 3)),
        "RUN_MISSED_ON_STARTUP": "true",
        "MAX_STARTUP_CATCHUP_JOBS": str(CONFIG.get("MAX_STARTUP_CATCHUP_JOBS", 2)),
        "STARTUP_CATCHUP_ALLOW_MAINTENANCE": str(CONFIG.get("STARTUP_CATCHUP_ALLOW_MAINTENANCE", False)).lower(),
        "STARTUP_CATCHUP_MIN_LOCAL_HOUR": str(CONFIG.get("STARTUP_CATCHUP_MIN_LOCAL_HOUR", 9)),
        "STARTUP_CATCHUP_MAX_LOCAL_HOUR": str(CONFIG.get("STARTUP_CATCHUP_MAX_LOCAL_HOUR", 22)),
        "PORTFOLIO_REPUBLISH_STATUS": str(CONFIG.get("PORTFOLIO_REPUBLISH_STATUS", "draft")),
        "PORTFOLIO_REPUBLISH_QUEUE_ENABLED": str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_ENABLED", True)).lower(),
        "PORTFOLIO_REPUBLISH_QUEUE_FILE": str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_FILE", "logs/portfolio_republish_queue.json")),
        "PORTFOLIO_REPUBLISH_QUEUE_TIME": str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_TIME", "22:10")),
        "PORTFOLIO_REPUBLISH_WEEKDAY_WINDOW": str(CONFIG.get("PORTFOLIO_REPUBLISH_WEEKDAY_WINDOW", "09:00-23:00")),
        "PORTFOLIO_REPUBLISH_WEEKEND_WINDOW": str(CONFIG.get("PORTFOLIO_REPUBLISH_WEEKEND_WINDOW", "14:00-23:00")),
        "PORTFOLIO_REPUBLISH_WEEKDAY_LIMIT": str(CONFIG.get("PORTFOLIO_REPUBLISH_WEEKDAY_LIMIT", 1)),
        "PORTFOLIO_REPUBLISH_WEEKEND_LIMIT": str(CONFIG.get("PORTFOLIO_REPUBLISH_WEEKEND_LIMIT", 2)),
        "PORTFOLIO_REPUBLISH_MAX_RETRIES": str(CONFIG.get("PORTFOLIO_REPUBLISH_MAX_RETRIES", 5)),
        "AUTO_SCHEDULE_ENABLED": "true",
        "AUTO_SCHEDULE_TOP_SLOTS": str(CONFIG.get("AUTO_SCHEDULE_TOP_SLOTS", 3)),
        "AUTO_SCHEDULE_RECALC_TIME": str(CONFIG.get("AUTO_SCHEDULE_RECALC_TIME", "00:10")),
        "PUBLISH_PREV_DAY_ENABLED": str(CONFIG.get("PUBLISH_PREV_DAY_ENABLED", True)).lower(),
        "PUBLISH_PREV_DAY_TIME": str(CONFIG.get("PUBLISH_PREV_DAY_TIME", "21:00")),
    }

    missing = []
    for key, value in defaults.items():
        if re.search(rf"^\s*{re.escape(key)}\s*=", raw, flags=re.MULTILINE):
            continue
        missing.append((key, value))

    if not missing:
        return

    try:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write("\n# === Auto-added by mnakr.py ===\n")
            for key, value in missing:
                f.write(f"{key}={value}\n")
        logger.info(f".env defaults auto-added for {len(missing)} keys")
    except Exception as e:
        logger.warning(f".env auto-fill failed: {e}")


_ensure_env_defaults()


def is_conversion_keyword(keyword):
    if not keyword:
        return False
    normalized = _normalize_topic(keyword)
    required_intents = [
        "신규등록",
        "양도양수",
        "기업진단",
        "실질자본금",
        "공제조합",
        "출자좌수",
        "기술인력",
        "등록기준",
        "행정처분",
        "법인설립",
        "면허",
        "입찰",
        "시공능력평가",
    ]
    return any(token in normalized for token in required_intents)


def build_slug_from_keyword(keyword):
    token_map = [
        ("건설업", "construction-business"),
        ("전문건설업", "specialty-construction"),
        ("종합건설업", "general-construction"),
        ("신규등록", "new-license"),
        ("신규 등록", "new-license"),
        ("양도양수", "license-transfer"),
        ("양도 양수", "license-transfer"),
        ("면허", "license"),
        ("절차", "process"),
        ("요건", "requirements"),
        ("서류", "documents"),
        ("비용", "cost"),
        ("기간", "timeline"),
        ("기업진단", "corporate-diagnosis"),
        ("실질자본금", "substantial-capital"),
        ("공제조합", "guarantee-association"),
        ("출자좌수", "share-amount"),
        ("기술인력", "technical-staff"),
        ("행정처분", "administrative-action"),
        ("입찰", "bidding"),
        ("시공능력평가", "construction-capability"),
        ("상담", "consulting"),
    ]

    source = str(keyword or "").strip()
    picked = []
    for ko, en in token_map:
        if ko in source and en not in picked:
            picked.append(en)
    if not picked:
        picked = ["construction-business", "license-guide"]
    return "-".join(picked[:6])


def _sanitize_wp_slug(slug_text, decode=True):
    src = str(slug_text or "").strip().replace("_", "-")
    if decode:
        src = unquote(src)
    src = src.lower()
    src = re.sub(r"[^0-9a-z가-힣%\-\s]", "-", src)
    src = src.replace(" ", "-")
    src = re.sub(r"-{2,}", "-", src).strip("-")
    return src


def _slug_tokens(slug_text):
    return [tok for tok in _sanitize_wp_slug(slug_text).split("-") if tok]


def _is_valid_wp_slug(slug_text, min_tokens=2, max_tokens=12, min_len=8, max_len=140):
    slug = _sanitize_wp_slug(slug_text)
    if not slug:
        return False
    if len(slug) < int(min_len) or len(slug) > int(max_len):
        return False
    if not re.match(r"^[0-9a-z가-힣%\-]+$", slug):
        return False
    tokens = _slug_tokens(slug)
    return int(min_tokens) <= len(tokens) <= int(max_tokens)


def _korean_slug_hint(keyword):
    src = str(keyword or "").strip()
    if not src:
        return ""
    hint = re.sub(r"[^0-9가-힣\s-]", " ", src)
    hint = re.sub(r"\s+", "-", hint).strip("-")
    hint = re.sub(r"-{2,}", "-", hint)
    return hint


def _compose_publish_slug(base_slug, keyword):
    base = _sanitize_wp_slug(base_slug)
    if not base:
        base = _sanitize_wp_slug(build_slug_from_keyword(keyword))

    hint_ko = _korean_slug_hint(keyword)
    hint = _sanitize_wp_slug(quote(hint_ko, safe="-").lower(), decode=False) if hint_ko else ""
    if not hint:
        return base

    base_norm = _normalize_slug_token(base)
    hint_norm = _normalize_slug_token(hint)
    if hint_norm and hint_norm in base_norm:
        return base

    combined = _sanitize_wp_slug(f"{base}-{hint}", decode=False) if base else hint
    if len(combined) <= 140 and _is_valid_wp_slug(combined):
        return combined

    # Keep canonical base slug when the combined form is too long.
    return base


def _normalize_focus_keyword(keyword):
    kw = str(keyword or "")
    kw = kw.replace("\xa0", " ")
    kw = re.sub(r"[\u200b-\u200d\ufeff]", "", kw)
    kw = re.sub(r"\s+", " ", kw).strip()
    return kw


def _normalize_text_spaces(text):
    return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()


def _final_sound_info(text):
    src = re.sub(r"[\s\"'’`)\]}>]+$", "", str(text or ""))
    if not src:
        return {"has_batchim": False, "jong": 0}
    ch = src[-1]
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        jong = (code - 0xAC00) % 28
        return {"has_batchim": jong != 0, "jong": jong}
    if ch.isdigit():
        # Korean reading based approximation for final consonant.
        return {"has_batchim": ch in {"0", "1", "3", "6", "7", "8"}, "jong": 0}
    return {"has_batchim": False, "jong": 0}


def _with_particle(text, pair):
    src = _normalize_text_spaces(text)
    parts = str(pair or "").split("/")
    if len(parts) != 2:
        return src
    first, second = parts[0], parts[1]
    info = _final_sound_info(src)
    if pair == "으로/로":
        # ㄹ 받침(종성 8)은 '로'를 사용.
        pick = second if (not info["has_batchim"] or info["jong"] == 8) else first
    else:
        pick = first if info["has_batchim"] else second
    return f"{src}{pick}"


def _normalize_keyword_josa(text, keyword):
    src = str(text or "")
    key = _normalize_focus_keyword(keyword)
    if not src or not key:
        return src

    for pair in ("은/는", "이/가", "을/를", "과/와", "으로/로"):
        first, second = pair.split("/")
        chosen = _with_particle(key, pair)[len(key):]
        other = second if chosen == first else first
        # 1) wrong particle after keyword
        src = re.sub(
            rf"({re.escape(key)})\s*['’`\"]?\s*{re.escape(other)}(?=[\s,.;:!?]|$)",
            rf"\1{chosen}",
            src,
        )
        # 2) remove stray quote before correct particle (e.g., 절차'은)
        src = re.sub(
            rf"({re.escape(key)})\s*['’`\"]\s*{re.escape(chosen)}(?=[\s,.;:!?]|$)",
            rf"\1{chosen}",
            src,
        )
    return src


def _collapse_repeated_polite_endings(text):
    src = str(text or "")
    if not src:
        return src
    src = re.sub(r"(확인하세요\.)\s*\1+", r"\1", src)
    src = re.sub(r"(진행하세요\.)\s*\1+", r"\1", src)
    src = re.sub(r"(문의하세요\.)\s*\1+", r"\1", src)
    src = re.sub(r"하세요\.\s*하세요\.", "하세요.", src)
    # Remove consecutive duplicate sentences.
    parts = re.split(r"(?<=[.!?])\s+", src)
    cleaned = []
    prev_norm = ""
    for part in parts:
        token = part.strip()
        if not token:
            continue
        norm = re.sub(r"[\s\"'’`]+", "", token)
        if norm and norm == prev_norm:
            continue
        cleaned.append(token)
        prev_norm = norm
    if cleaned:
        src = " ".join(cleaned)
    return src


def _naturalize_korean_text(text, keyword=""):
    src = str(text or "")
    if not src:
        return ""

    token_re = re.compile(
        r"(\[(?:PARA|POINT|/POINT|FAQ|/FAQ|LIST|/LIST|NUM|/NUM|EXTLINK|/EXTLINK)\])",
        flags=re.IGNORECASE,
    )
    out = []
    for chunk in token_re.split(src):
        if not chunk:
            continue
        if token_re.fullmatch(chunk):
            out.append(chunk)
            continue
        c = _normalize_text_spaces(chunk)
        c = _normalize_keyword_josa(c, keyword)
        c = _collapse_repeated_polite_endings(c)
        c = re.sub(r"(했습니다|합니다|입니다|됩니다|하세요)\s+(?=[가-힣A-Za-z0-9])", r"\1. ", c)
        c = re.sub(r"\s+([,.;:!?])", r"\1", c)
        out.append(c)

    merged = "".join(out)
    merged = re.sub(r"(?:\[PARA\]){2,}", "[PARA]", merged)
    merged = re.sub(r"\s{2,}", " ", merged).strip()
    return merged


def _contains_focus_keyword(text, keyword):
    source = _normalize_text_spaces(text)
    focus = _normalize_focus_keyword(keyword)
    return bool(focus and focus in source)


def _trim_text_naturally(text, max_len=160):
    src = _normalize_text_spaces(text)
    if len(src) <= int(max_len):
        return src

    hard_cut = src[: int(max_len)].rstrip(" ,.;:")
    for token in ("다.", "요.", ".", "!", "?"):
        idx = hard_cut.rfind(token)
        if idx >= 24:
            return hard_cut[: idx + len(token)].strip()

    tail = " 자세한 내용은 본문에서 확인하세요."
    if int(max_len) - len(tail) >= 24:
        lead = src[: int(max_len) - len(tail)].rstrip(" ,.;:")
        return f"{lead}{tail}".strip()
    return hard_cut


def _build_seo_description(keyword, summary, min_len=110, max_len=160):
    focus = _normalize_focus_keyword(keyword)
    desc = _naturalize_korean_text(summary, keyword=focus)
    desc = re.sub(r"(?:\.{3}|…|&hellip;)\s*$", "", desc, flags=re.IGNORECASE).rstrip(" ,.;:")
    fillers = [
        "핵심 요건과 절차, 일정과 비용, 리스크 관리 포인트를 함께 확인하세요.",
        "실무 체크리스트를 기준으로 우선순위를 정리하면 재작업을 줄일 수 있습니다.",
    ]
    filler_idx = 0

    def _append_sentence(base, sentence):
        b = _normalize_text_spaces(base).rstrip(" ,")
        s = _normalize_text_spaces(sentence)
        if not b:
            return s
        if re.search(r"[.!?]$", b):
            return f"{b} {s}"
        if re.search(r"(?:합니다|했습니다|입니다|됩니다|하세요)$", b):
            return f"{b}. {s}"
        return f"{b}. {s}"

    if not desc:
        desc = f"{focus} 핵심 요건, 절차, 일정, 비용, 리스크를 실무 기준으로 정리했습니다.".strip()
    if focus and focus not in desc:
        desc = f"{focus} {desc}".strip()

    while len(desc) < int(min_len):
        desc = _append_sentence(desc, fillers[filler_idx % len(fillers)])
        filler_idx += 1
        desc = _naturalize_korean_text(desc, keyword=focus)

    if len(desc) <= int(max_len) and not re.search(r"(?:다\.|요\.|니다\.|[!?])$", desc):
        closed = False
        for token in ("다.", "요.", ".", "!", "?"):
            idx = desc.rfind(token)
            if idx >= 24:
                desc = desc[: idx + len(token)].strip()
                closed = True
                break
        if not closed:
            desc = _trim_text_naturally(desc + " 내용을 본문에서 확인하세요.", max_len=max_len)

    while len(desc) < int(min_len):
        desc = _append_sentence(desc, fillers[filler_idx % len(fillers)])
        filler_idx += 1
        desc = _naturalize_korean_text(desc, keyword=focus)

    desc = _trim_text_naturally(desc, max_len=max_len)

    # Keep focus keyword in meta description after trimming.
    if focus and focus not in desc:
        fallback = f"{focus} 핵심 요건, 절차, 일정, 비용, 리스크 관리 포인트를 정리했습니다."
        desc = _trim_text_naturally(fallback, max_len=max_len)
    return _naturalize_korean_text(desc, keyword=focus)


class OpenAIKeywordAdvisor:
    """
    Optional OpenAI keyword reranker.
    Enabled only when OPENAI_SCAN_ENABLED=true, OPENAI_API_KEY, and OPENAI_MODEL are set.
    """

    def __init__(self):
        self.enabled = _cfg_bool("OPENAI_SCAN_ENABLED", False)
        self.api_key = str(CONFIG.get("OPENAI_API_KEY", "")).strip()
        self.model = str(CONFIG.get("OPENAI_MODEL", "")).strip()

    def is_enabled(self):
        return bool(self.enabled and self.api_key and self.model)

    def rerank_keywords(self, candidates, existing_posts, site_topics):
        if not candidates or not self.is_enabled():
            return candidates

        try:
            recent_titles = []
            for post in existing_posts[:160]:
                title = str(post.get("title", "")).strip()
                excerpt_raw = str(post.get("excerpt", "")).strip()
                excerpt = ""
                if excerpt_raw:
                    excerpt = BeautifulSoup(excerpt_raw, "html.parser").get_text(" ", strip=True)
                    excerpt = re.sub(r"\s+", " ", excerpt)[:220]
                if title:
                    recent_titles.append(f"{title} || {excerpt}" if excerpt else title)

            payload_data = {
                "candidate_keywords": candidates[:30],
                "existing_titles": recent_titles,
                "site_topics": dict(site_topics),
                "goal": (
                    "Prioritize keywords with high construction-service conversion potential, "
                    "minimize overlap with existing posts, and keep overall topical balance."
                ),
            }

            system_prompt = (
                "You are a construction SEO assistant. Target keyword selection must stay within candidate_keywords. "
                "Return valid JSON only in this format: "
                "{\"ordered_keywords\":[\"...\"],\"reason\":\"...\"}. "
                "{\"ordered_keywords\":[\"...\"],\"reason\":\"...\"}. "
                "ordered_keywords must contain only items from candidate_keywords."
            )
            user_prompt = json.dumps(payload_data, ensure_ascii=False)

            res = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": [
                        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                        {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
                    ],
                    "max_output_tokens": 700,
                },
                timeout=45,
            )
            if res.status_code != 200:
                logger.warning(f"OpenAI keyword rerank failed: {res.status_code} {res.text[:200]}")
                return candidates

            data = res.json()
            raw_text = str(data.get("output_text", "")).strip()
            if not raw_text:
                chunks = []
                for item in data.get("output", []) or []:
                    for content in item.get("content", []) or []:
                        text = content.get("text")
                        if text:
                            chunks.append(str(text))
                raw_text = "\n".join(chunks).strip()

            if not raw_text:
                return candidates

            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start >= 0 and end > start:
                raw_text = raw_text[start : end + 1]
            parsed = json.loads(raw_text)
            ordered = parsed.get("ordered_keywords", [])
            if not isinstance(ordered, list):
                return candidates

            allowed = set(candidates)
            picked = []
            for kw in ordered:
                k = str(kw).strip()
                if k and k in allowed and k not in picked:
                    picked.append(k)
            for kw in candidates:
                if kw not in picked:
                    picked.append(kw)
            logger.info("OpenAI rerank applied")
            return picked
        except Exception as e:
            logger.warning(f"OpenAI keyword rerank exception: {e}")
            return candidates


class PerformanceDataHub:
    """Aggregates search performance signals and returns per-page metrics."""

    def __init__(self):
        self.enabled = _cfg_bool("SEARCH_DATA_ENABLED", True)
        self.window_days = max(7, _cfg_int("SEARCH_PERFORMANCE_WINDOW_DAYS", 30))
        self.sc_csv_path = str(CONFIG.get("SEARCH_CONSOLE_CSV_PATH", "search_console_queries.csv")).strip()
        self.naver_csv_path = str(CONFIG.get("NAVER_QUERY_CSV_PATH", "naver_queries.csv")).strip()
        self.gsc_property = str(CONFIG.get("GSC_PROPERTY_URL", "")).strip()
        self.gsc_sa_file = str(CONFIG.get("GSC_SERVICE_ACCOUNT_FILE", "service_account.json")).strip()
        self._query_cache = None
        self._gsc_disabled_reason = ""

    def _float_or_zero(self, value):
        if value is None:
            return 0.0
        text = str(value).strip().replace(",", "")
        if text.endswith("%"):
            text = text[:-1]
            try:
                return float(text) / 100.0
            except Exception:
                return 0.0
        try:
            num = float(text)
            if num > 1.0 and "ctr" in str(value).lower():
                return num / 100.0
            return num
        except Exception:
            return 0.0

    def _int_or_zero(self, value):
        try:
            return int(float(str(value).strip().replace(",", "")))
        except Exception:
            return 0

    def _resolve_gsc_property(self):
        return self.gsc_property

    def _gsc_service(self):
        property_url = self._resolve_gsc_property()
        if not self.enabled or not property_url:
            return None, ""
        if not os.path.exists(self.gsc_sa_file):
            return None, property_url
        try:
            from google.oauth2 import service_account  # type: ignore
            from googleapiclient.discovery import build  # type: ignore
        except Exception:
            return None, property_url

        try:
            creds = service_account.Credentials.from_service_account_file(
                self.gsc_sa_file,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
            )
            service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
            return service, property_url
        except Exception as e:
            logger.warning(f"GSC service init failed: {e}")
            return None, property_url

    def _query_gsc(self, body):
        if self._gsc_disabled_reason:
            return []
        service, property_url = self._gsc_service()
        if service is None or not property_url:
            return []
        try:
            res = service.searchanalytics().query(siteUrl=property_url, body=body).execute()
            return res.get("rows", []) or []
        except Exception as e:
            self._gsc_disabled_reason = str(e)
            logger.warning(f"GSC query failed (disabled for this run): {e}")
            return []

    def _read_csv_rows(self, path):
        if not path or not os.path.exists(path):
            return []
        rows = []
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({str(k).strip().lower(): v for k, v in row.items()})
        except Exception as e:
            logger.warning(f"CSV load failed ({path}): {e}")
        return rows

    def _pick(self, row, keys):
        for k in keys:
            key = k.lower()
            if key in row and str(row.get(key, "")).strip():
                return row.get(key)
        return ""

    def load_query_metrics(self):
        if self._query_cache is not None:
            return self._query_cache
        if not self.enabled:
            self._query_cache = []
            return self._query_cache

        start = (datetime.now() - timedelta(days=self.window_days)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")

        aggregated = {}
        # 1) GSC
        gsc_rows = self._query_gsc(
            {
                "startDate": start,
                "endDate": end,
                "dimensions": ["query"],
                "rowLimit": 250,
            }
        )
        for row in gsc_rows:
            keys = row.get("keys", [])
            query = str(keys[0]).strip() if keys else ""
            if not query:
                continue
            metrics = aggregated.setdefault(
                query,
                {"query": query, "impressions": 0, "clicks": 0, "ctr": 0.0, "position": 0.0, "sources": set()},
            )
            metrics["impressions"] += int(row.get("impressions", 0) or 0)
            metrics["clicks"] += int(row.get("clicks", 0) or 0)
            metrics["position"] += float(row.get("position", 0) or 0)
            metrics["sources"].add("gsc")

        # 2) CSV fallback (Search Console/Naver export)
        for source_name, path in (("gsc_csv", self.sc_csv_path), ("naver_csv", self.naver_csv_path)):
            for row in self._read_csv_rows(path):
                query = str(self._pick(row, ["query", "검색어", "keyword", "키워드"])).strip()
                if not query:
                    continue
                metrics = aggregated.setdefault(
                    query,
                    {"query": query, "impressions": 0, "clicks": 0, "ctr": 0.0, "position": 0.0, "sources": set()},
                )
                metrics["impressions"] += self._int_or_zero(self._pick(row, ["impressions", "노출", "impr"]))
                metrics["clicks"] += self._int_or_zero(self._pick(row, ["clicks", "클릭"]))
                pos = self._float_or_zero(self._pick(row, ["position", "평균순위", "rank"]))
                if pos:
                    metrics["position"] += pos
                metrics["sources"].add(source_name)

        items = []
        for query, v in aggregated.items():
            impressions = max(0, int(v["impressions"]))
            clicks = max(0, int(v["clicks"]))
            ctr = (clicks / impressions) if impressions > 0 else 0.0
            items.append(
                {
                    "query": query,
                    "impressions": impressions,
                    "clicks": clicks,
                    "ctr": ctr,
                    "position": float(v["position"] or 0.0),
                    "sources": sorted(v["sources"]),
                }
            )

        items.sort(key=lambda x: (x["impressions"], -x["ctr"]), reverse=True)
        self._query_cache = items
        return self._query_cache

    def get_low_ctr_opportunities(self, count=8):
        if not self.enabled:
            return []
        high_impr = _cfg_int("HIGH_IMPRESSIONS_THRESHOLD", 60)
        low_ctr = _cfg_float("LOW_CTR_THRESHOLD", 0.012)
        queries = self.load_query_metrics()
        picks = []
        for row in queries:
            q = str(row.get("query", "")).strip()
            impr = int(row.get("impressions", 0) or 0)
            ctr = float(row.get("ctr", 0.0) or 0.0)
            if not q or impr < high_impr or ctr > low_ctr:
                continue
            if is_conversion_keyword(q):
                if q not in picks:
                    picks.append(q)
                continue
            q_norm = _normalize_topic(q)
            if "건설" in q_norm and any(
                t in q_norm for t in ["등록", "면허", "양도", "진단", "자본금", "공제", "입찰", "행정처분", "시공능력"]
            ):
                if q not in picks:
                    picks.append(q)
            if len(picks) >= count:
                break
        return picks

    def get_page_metrics(self, page_url, days=None):
        if not page_url:
            return {"impressions": 0, "clicks": 0, "ctr": 0.0, "position": 0.0, "sources": []}
        days = int(days or self.window_days)
        start = (datetime.now() - timedelta(days=max(3, days))).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        target = str(page_url).strip()
        target_path = urlparse(target).path or target

        impressions = 0
        clicks = 0
        position_sum = 0.0
        source_set = set()

        # 1) GSC
        rows = self._query_gsc(
            {
                "startDate": start,
                "endDate": end,
                "dimensions": ["page"],
                "dimensionFilterGroups": [
                    {"filters": [{"dimension": "page", "operator": "contains", "expression": target_path}]}
                ],
                "rowLimit": 50,
            }
        )
        for row in rows:
            impressions += int(row.get("impressions", 0) or 0)
            clicks += int(row.get("clicks", 0) or 0)
            position_sum += float(row.get("position", 0.0) or 0.0)
            source_set.add("gsc")

        # 2) CSV fallback
        for source_name, path in (("gsc_csv", self.sc_csv_path), ("naver_csv", self.naver_csv_path)):
            for row in self._read_csv_rows(path):
                page = str(self._pick(row, ["page", "url", "페이지"])).strip()
                if not page:
                    continue
                if target_path not in page and target not in page:
                    continue
                impressions += self._int_or_zero(self._pick(row, ["impressions", "노출", "impr"]))
                clicks += self._int_or_zero(self._pick(row, ["clicks", "클릭"]))
                position_sum += self._float_or_zero(self._pick(row, ["position", "평균순위", "rank"]))
                source_set.add(source_name)

        ctr = (clicks / impressions) if impressions > 0 else 0.0
        return {
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "position": position_sum,
            "sources": sorted(source_set),
        }


class SemanticCannibalizationGuard:
    """OpenAI embedding-based semantic duplicate/cannibalization guard."""

    CACHE_FILE = "semantic_embeddings_cache.json"

    def __init__(self):
        self.enabled = _cfg_bool("SEMANTIC_GUARD_ENABLED", True)
        self.api_key = str(CONFIG.get("OPENAI_API_KEY", "")).strip()
        self.model = str(CONFIG.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")).strip()
        self.threshold = _cfg_float("SEMANTIC_DUP_THRESHOLD", 0.92)
        self.corpus = []
        self.cache = self._load_cache()
        if not self.api_key:
            self.enabled = False

    def _load_cache(self):
        if not os.path.exists(self.CACHE_FILE):
            return {}
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_cache(self):
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _key(self, text):
        return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()

    def _embed_batch(self, texts):
        if not texts or not self.enabled:
            return []
        try:
            res = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
                timeout=45,
            )
            if res.status_code != 200:
                logger.warning(f"Embedding create failed: {res.status_code} {res.text[:200]}")
                return []
            data = res.json().get("data", [])
            return [d.get("embedding", []) for d in data]
        except Exception as e:
            logger.warning(f"Embedding create exception: {e}")
            return []

    def _cosine(self, a, b):
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def update_corpus(self, posts):
        self.corpus = []
        if not self.enabled:
            return

        samples = []
        for post in posts[:220]:
            title = str(post.get("title", "")).strip()
            excerpt = str(post.get("excerpt", "")).strip()
            body = str(post.get("content", "")).strip()
            if excerpt:
                excerpt = BeautifulSoup(excerpt, "html.parser").get_text(" ", strip=True)
            if body:
                body = BeautifulSoup(body, "html.parser").get_text(" ", strip=True)
                body = re.sub(r"\s+", " ", body)[:800]
            text = (title + " " + excerpt + " " + body).strip()
            if len(text) >= 8:
                samples.append(text[:700])

        missing_texts = []
        missing_keys = []
        for text in samples:
            k = self._key(text)
            vec = self.cache.get(k)
            if isinstance(vec, list) and vec:
                self.corpus.append((text, vec))
            else:
                missing_texts.append(text)
                missing_keys.append(k)

        if missing_texts:
            batch_size = 30
            for i in range(0, len(missing_texts), batch_size):
                batch = missing_texts[i : i + batch_size]
                vectors = self._embed_batch(batch)
                for text, vec in zip(batch, vectors):
                    if isinstance(vec, list) and vec:
                        key = self._key(text)
                        self.cache[key] = vec
                        self.corpus.append((text, vec))
            self._save_cache()

    def is_semantic_duplicate(self, keyword):
        if not self.enabled or not self.corpus:
            return False, 0.0, ""

        key = self._key(keyword)
        vec = self.cache.get(key)
        if not (isinstance(vec, list) and vec):
            embeds = self._embed_batch([keyword])
            vec = embeds[0] if embeds else []
            if vec:
                self.cache[key] = vec
                self._save_cache()
        if not vec:
            return False, 0.0, ""

        best_score = 0.0
        best_text = ""
        for text, ref_vec in self.corpus:
            sim = self._cosine(vec, ref_vec)
            if sim > best_score:
                best_score = sim
                best_text = text
        return best_score >= self.threshold, best_score, best_text


class LifecycleOptimizer:
    """Automatically improves title/summary on 7/14/30 day checkpoints."""

    CHECKPOINTS = (7, 14, 30)

    def __init__(self):
        self.enabled = _cfg_bool("LIFECYCLE_ENABLED", True)
        self.file_path = str(CONFIG.get("LIFECYCLE_FILE", "content_lifecycle.json")).strip() or "content_lifecycle.json"
        self.perf = PerformanceDataHub()

    def _load(self):
        if not os.path.exists(self.file_path):
            return {"posts": {}}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("posts", {})
                return data
        except Exception:
            pass
        return {"posts": {}}

    def _save(self, data):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Lifecycle file save failed: {e}")

    def register_post(self, post_data, keyword, content):
        if not self.enabled or not isinstance(post_data, dict):
            return
        post_id = str(post_data.get("id") or "").strip()
        if not post_id:
            return
        data = self._load()
        posts = data.setdefault("posts", {})
        if post_id in posts:
            return

        created_at = datetime.now(timezone.utc)
        checkpoints = []
        for day in self.CHECKPOINTS:
            checkpoints.append(
                {
                    "day": day,
                    "due_at": (created_at + timedelta(days=day)).isoformat(),
                    "status": "pending",
                    "checked_at": "",
                    "metrics": {},
                    "action": "",
                    "reason": "",
                }
            )

        posts[post_id] = {
            "id": int(post_id),
            "url": str(post_data.get("link", "")),
            "keyword": keyword,
            "headline": str(content.get("headline", "")),
            "summary": str(content.get("summary", "")),
            "created_at": created_at.isoformat(),
            "checkpoints": checkpoints,
        }
        self._save(data)

    def bootstrap_from_wordpress(self, max_posts=40):
        if not self.enabled:
            return 0
        max_posts = max(1, int(max_posts or 40))
        data = self._load()
        posts = data.setdefault("posts", {})
        if posts:
            return 0

        wp_url = str(CONFIG.get("WP_URL", "")).rstrip("/")
        if not wp_url:
            return 0

        fetched = []
        page = 1
        while len(fetched) < max_posts:
            per_page = min(100, max_posts - len(fetched))
            try:
                res = requests.get(
                    f"{wp_url}/posts",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "status": "publish",
                        "_fields": "id,link,title,excerpt,date",
                    },
                    timeout=15,
                )
            except requests.RequestException:
                break
            if res.status_code != 200:
                break
            rows = res.json()
            if not rows:
                break
            fetched.extend(rows)
            if page >= int(res.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1

        if not fetched:
            return 0

        added = 0
        for row in fetched:
            post_id = str(row.get("id") or "").strip()
            if not post_id or post_id in posts:
                continue
            headline = str(row.get("title", {}).get("rendered", "")).strip()
            excerpt_html = str(row.get("excerpt", {}).get("rendered", "")).strip()
            summary = BeautifulSoup(excerpt_html, "html.parser").get_text(" ", strip=True) if excerpt_html else ""
            post_url = str(row.get("link", "")).strip()
            keyword = headline if is_conversion_keyword(headline) else (headline[:40] or "건설업 실무 가이드")
            created_raw = str(row.get("date", "")).strip()
            try:
                created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
            except Exception:
                created_at = datetime.now(timezone.utc)

            checkpoints = []
            for day in self.CHECKPOINTS:
                checkpoints.append(
                    {
                        "day": day,
                        "due_at": (created_at + timedelta(days=day)).isoformat(),
                        "status": "pending",
                        "checked_at": "",
                        "metrics": {},
                        "action": "",
                        "reason": "",
                    }
                )

            posts[post_id] = {
                "id": int(post_id),
                "url": post_url,
                "keyword": keyword,
                "headline": headline,
                "summary": summary,
                "created_at": created_at.isoformat(),
                "checkpoints": checkpoints,
            }
            added += 1

        if added:
            self._save(data)
            logger.info(f"ℹ️ 라이프사이클 초기 백필 완료: {added}건")
        return added

    def _should_rewrite(self, day, metrics):
        impressions = int(metrics.get("impressions", 0) or 0)
        ctr = float(metrics.get("ctr", 0.0) or 0.0)
        if impressions < 25 and day <= 14:
            return False, "데이터 부족"
        if impressions < 40 and day == 30:
            return False, "데이터 부족"

        threshold = {7: 0.010, 14: 0.013, 30: 0.016}.get(day, 0.012)
        if ctr < threshold:
            return True, f"CTR below threshold ({ctr:.3%} < {threshold:.3%})"
        return False, "performance acceptable"

    def _rewrite_headline_summary(self, keyword, headline, summary, metrics):
        # OpenAI first
        advisor = OpenAIKeywordAdvisor()
        if advisor.is_enabled():
            try:
                payload = {
                    "keyword": keyword,
                    "headline": headline,
                    "summary": summary,
                    "metrics": metrics,
                    "rule": "headline <= 55 chars, summary 110~160 chars, include keyword early",
                }
                res = requests.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {advisor.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": advisor.model,
                        "input": [
                            {
                                "role": "system",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": (
                                            "You are an SEO metadata optimizer. Return JSON only. "
                                            "{\"headline\":\"...\",\"summary\":\"...\"}"
                                        ),
                                    }
                                ],
                            },
                            {"role": "user", "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}]},
                        ],
                        "max_output_tokens": 250,
                    },
                    timeout=35,
                )
                if res.status_code == 200:
                    data = res.json()
                    text = str(data.get("output_text", "")).strip()
                    if not text:
                        chunks = []
                        for item in data.get("output", []) or []:
                            for c in item.get("content", []) or []:
                                if c.get("text"):
                                    chunks.append(c.get("text"))
                        text = "\n".join(chunks).strip()
                    if text:
                        s = text.find("{")
                        e = text.rfind("}")
                        if s >= 0 and e > s:
                            text = text[s : e + 1]
                        parsed = json.loads(text)
                        new_h = str(parsed.get("headline", "")).strip() or headline
                        new_s = str(parsed.get("summary", "")).strip() or summary
                        return new_h[:58], new_s[:160]
            except Exception:
                pass

        # fallback: rule-based lightweight correction
        keyword = _normalize_focus_keyword(keyword)
        new_headline = headline
        if keyword not in new_headline:
            new_headline = f"{keyword} | {headline}".strip()
        if len(new_headline) > 58:
            new_headline = new_headline[:58].rstrip()
        new_summary = _normalize_text_spaces(summary)
        if len(new_summary) < 110:
            new_summary = (
                new_summary
                + f" {keyword} 핵심 요건과 절차, 일정, 비용, 리스크 대응 포인트를 실무 기준으로 정리했습니다."
            ).strip()
        new_summary = _build_seo_description(keyword, new_summary, min_len=110, max_len=160)
        return new_headline, new_summary

    def _apply_wp_update(self, post_id, keyword, headline, summary):
        keyword = _normalize_focus_keyword(keyword)
        wp = WPEngine()
        seo_desc = _build_seo_description(keyword, summary, min_len=110, max_len=160)
        payload = {"title": headline, "excerpt": seo_desc}
        res = requests.post(f"{wp.wp_url}/posts/{post_id}", headers=wp.headers, json=payload, timeout=20)
        _raise_for_status_with_context(res, f"post update failed(post_id={post_id})")
        seo_title = f"{headline} | {CONFIG.get('BRAND_NAME', '')}".strip()
        if len(seo_title) > 60:
            seo_title = seo_title[:60].rstrip()
        wp._update_rankmath_meta(post_id=post_id, keyword=keyword, seo_title=seo_title, seo_desc=seo_desc)
        return True

    def process_due_tasks(self, limit=3):
        if not self.enabled:
            return
        data = self._load()
        posts = data.get("posts", {})
        if not posts:
            return

        now = datetime.now(timezone.utc)
        due = []
        for post_id, row in posts.items():
            for cp in row.get("checkpoints", []):
                if cp.get("status") != "pending":
                    continue
                due_at = str(cp.get("due_at", ""))
                try:
                    due_dt = datetime.fromisoformat(due_at)
                except Exception:
                    continue
                if due_dt <= now:
                    due.append((due_dt, post_id, cp))
        due.sort(key=lambda x: x[0])
        if not due:
            return

        handled = 0
        for _due_dt, post_id, cp in due:
            if handled >= limit:
                break
            row = posts.get(post_id, {})
            page_url = str(row.get("url", "")).strip()
            keyword = str(row.get("keyword", "")).strip()
            day = int(cp.get("day", 0) or 0)
            metrics = self.perf.get_page_metrics(page_url, days=max(day, 7))
            rewrite, reason = self._should_rewrite(day, metrics)
            cp["checked_at"] = datetime.now(timezone.utc).isoformat()
            cp["metrics"] = metrics
            cp["reason"] = reason

            if rewrite:
                try:
                    new_h, new_s = self._rewrite_headline_summary(
                        keyword=keyword,
                        headline=str(row.get("headline", "")),
                        summary=str(row.get("summary", "")),
                        metrics=metrics,
                    )
                    self._apply_wp_update(int(post_id), keyword, new_h, new_s)
                    cp["status"] = "done"
                    cp["action"] = "rewrite_applied"
                    row["headline"] = new_h
                    row["summary"] = new_s
                    logger.info(f"Lifecycle rewrite applied: post_id={post_id}, day={day}")
                except Exception as e:
                    cp["status"] = "error"
                    cp["action"] = "rewrite_failed"
                    cp["reason"] = f"apply failed: {e}"
                    logger.warning(f"Lifecycle rewrite failed(post_id={post_id}): {e}")
            else:
                cp["status"] = "done"
                cp["action"] = "skip"
            handled += 1

        self._save(data)




class QueryCTRRewriteOptimizer:
    """Low-CTR high-impression query loop for title/summary refinement."""

    def __init__(self):
        self.enabled = _cfg_bool("QUERY_REWRITE_ENABLED", True)
        self.queue_file = str(CONFIG.get("QUERY_REWRITE_QUEUE_FILE", "query_rewrite_queue.json")).strip() or "query_rewrite_queue.json"
        self.min_impressions = max(20, _cfg_int("QUERY_REWRITE_MIN_IMPRESSIONS", 80))
        self.low_ctr = _cfg_float("QUERY_REWRITE_LOW_CTR", _cfg_float("LOW_CTR_THRESHOLD", 0.012))
        self.min_similarity = _cfg_float("QUERY_REWRITE_MIN_SIMILARITY", 0.42)
        self.max_actions = max(1, _cfg_int("QUERY_REWRITE_MAX_ACTIONS_PER_DAY", 2))
        self.cooldown_days = max(1, _cfg_int("QUERY_REWRITE_COOLDOWN_DAYS", 14))
        self.perf = PerformanceDataHub()

    def _load_state(self):
        if not os.path.exists(self.queue_file):
            return {"updated_at": "", "items": [], "history": []}
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("updated_at", "")
                data.setdefault("items", [])
                data.setdefault("history", [])
                return data
        except Exception:
            pass
        return {"updated_at": "", "items": [], "history": []}

    def _save_state(self, state):
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"query rewrite queue 저장 실패: {e}")

    def _tokenize(self, text):
        return {
            w
            for w in re.findall(r"[0-9a-zA-Z가-힣]{2,}", str(text or "").lower())
            if len(w) >= 2
        }

    def _title_similarity(self, query, title, slug):
        q_norm = _normalize_topic(query)
        t_norm = _normalize_topic(title)
        s_norm = _normalize_slug_token(slug)
        if not q_norm or not (t_norm or s_norm):
            return 0.0

        title_seq = SequenceMatcher(None, q_norm, t_norm).ratio() if t_norm else 0.0
        slug_seq = SequenceMatcher(None, q_norm, s_norm).ratio() if s_norm else 0.0

        q_tokens = self._tokenize(query)
        t_tokens = self._tokenize(f"{title} {slug}")
        jaccard = (len(q_tokens & t_tokens) / len(q_tokens | t_tokens)) if (q_tokens and t_tokens) else 0.0

        score = max(title_seq, slug_seq) * 0.6 + jaccard * 0.4
        if (q_norm in t_norm) or (t_norm and t_norm in q_norm):
            score = max(score, 0.92)
        return min(1.0, max(0.0, score))

    def _fetch_posts(self, wp, limit=140):
        rows = []
        page = 1
        while len(rows) < limit:
            try:
                res = requests.get(
                    f"{wp.wp_url}/posts",
                    params={
                        "per_page": min(100, limit - len(rows)),
                        "page": page,
                        "status": "publish",
                        "_fields": "id,title,slug,link,excerpt,date",
                    },
                    headers=wp.auth_headers,
                    timeout=15,
                )
            except requests.RequestException:
                break
            if res.status_code != 200:
                break
            data = res.json()
            if not data:
                break
            rows.extend(data)
            if page >= int(res.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1
        return rows

    def _recently_applied(self, post_id, history, now_utc):
        for entry in reversed(history):
            if int(entry.get("post_id", 0) or 0) != int(post_id):
                continue
            at_raw = str(entry.get("at", "")).strip()
            try:
                at_dt = datetime.fromisoformat(at_raw)
                if at_dt.tzinfo is None:
                    at_dt = at_dt.replace(tzinfo=timezone.utc)
            except Exception:
                return False
            return (now_utc - at_dt).days < self.cooldown_days
        return False

    def _rewrite_title_summary(self, query, title, summary):
        query = _normalize_focus_keyword(query)
        title = str(title or "").strip()
        summary = _normalize_text_spaces(summary)

        lead = query[:36] if query else ""
        if lead and lead not in title:
            title = f"{lead} | {title}".strip(" |")
        if len(title) > 58:
            title = title[:58].rstrip()

        if lead and lead not in summary:
            summary = (summary + f" {lead} 핵심 포인트를 실무 기준으로 빠르게 확인할 수 있도록 정리했습니다.").strip()
        summary = _build_seo_description(
            lead or query,
            summary,
            min_len=110,
            max_len=160,
        )

        return title, summary

    def _build_candidates(self, posts, metrics_rows, history):
        by_post = {}
        now_utc = datetime.now(timezone.utc)

        for row in metrics_rows:
            query = str(row.get("query", "")).strip()
            impressions = int(row.get("impressions", 0) or 0)
            ctr = float(row.get("ctr", 0.0) or 0.0)
            if not query or impressions < self.min_impressions or ctr > self.low_ctr:
                continue

            best = None
            best_sim = 0.0
            for post in posts:
                post_id = int(post.get("id", 0) or 0)
                if not post_id or self._recently_applied(post_id, history, now_utc):
                    continue
                title = str(post.get("title", {}).get("rendered", ""))
                slug = str(post.get("slug", ""))
                sim = self._title_similarity(query, title, slug)
                if sim > best_sim:
                    best_sim = sim
                    best = post

            if not best or best_sim < self.min_similarity:
                continue

            post_id = int(best.get("id", 0) or 0)
            excerpt_html = str(best.get("excerpt", {}).get("rendered", ""))
            summary = BeautifulSoup(excerpt_html, "html.parser").get_text(" ", strip=True) if excerpt_html else ""

            current = by_post.get(post_id)
            candidate = {
                "post_id": post_id,
                "post_url": str(best.get("link", "")).strip(),
                "query": query,
                "impressions": impressions,
                "ctr": ctr,
                "similarity": round(best_sim, 4),
                "current_title": str(best.get("title", {}).get("rendered", "")).strip(),
                "current_summary": summary,
                "status": "pending",
                "reason": "high_impression_low_ctr_query",
            }
            if (not current) or (candidate["impressions"] > current["impressions"]) or (
                candidate["impressions"] == current["impressions"] and candidate["similarity"] > current["similarity"]
            ):
                by_post[post_id] = candidate

        items = list(by_post.values())
        items.sort(key=lambda x: (x["impressions"], -x["ctr"], x["similarity"]), reverse=True)
        return items

    def run_daily(self):
        if not self.enabled:
            return {"queued": 0, "applied": 0}

        state = self._load_state()
        history = state.get("history", [])

        wp = WPEngine()
        posts = self._fetch_posts(wp)
        metrics_rows = self.perf.load_query_metrics()

        candidates = self._build_candidates(posts, metrics_rows, history)
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["items"] = candidates

        applied = 0
        now_utc = datetime.now(timezone.utc)

        for item in state["items"]:
            if applied >= self.max_actions:
                break
            post_id = int(item.get("post_id", 0) or 0)
            if not post_id:
                item["status"] = "skip"
                item["reason"] = "invalid_post_id"
                continue
            if self._recently_applied(post_id, history, now_utc):
                item["status"] = "skip"
                item["reason"] = "cooldown"
                continue

            query = str(item.get("query", "")).strip()
            current_title = str(item.get("current_title", "")).strip()
            current_summary = str(item.get("current_summary", "")).strip()
            new_title, new_summary = self._rewrite_title_summary(query, current_title, current_summary)

            if new_title == current_title and new_summary == current_summary:
                item["status"] = "skip"
                item["reason"] = "no_change"
                continue

            try:
                seo_desc = _build_seo_description(query, new_summary, min_len=110, max_len=160)
                payload = {"title": new_title, "excerpt": seo_desc, "status": "publish"}
                res = requests.post(f"{wp.wp_url}/posts/{post_id}", headers=wp.headers, json=payload, timeout=20)
                _raise_for_status_with_context(res, f"query rewrite failed(post_id={post_id}, query={query})")

                seo_title = f"{new_title} | {CONFIG.get('BRAND_NAME', '')}".strip()
                if len(seo_title) > 60:
                    seo_title = seo_title[:60].rstrip()
                wp._update_rankmath_meta(post_id=post_id, keyword=query, seo_title=seo_title, seo_desc=seo_desc)

                item["status"] = "applied"
                item["applied_at"] = datetime.now(timezone.utc).isoformat()
                item["new_title"] = new_title
                item["new_summary"] = new_summary
                history.append({"post_id": post_id, "query": query, "at": item["applied_at"]})
                applied += 1
            except Exception as e:
                item["status"] = "error"
                item["reason"] = _safe_error_text(e)

        if len(history) > 1200:
            history = history[-1200:]
        state["history"] = history
        self._save_state(state)
        return {"queued": len(state.get("items", [])), "applied": applied}

class ContentPortfolioOptimizer:
    """
    Existing published posts are diagnosed by age/performance and auto-adjusted:
    - Mid score: rewrite/update on the same URL
    - Low score + old: delete and republish with a stronger target topic
    """
    ALLOWED_AUTH_DOMAINS = ("law.go.kr", "cgbo.co.kr", "kosca.or.kr", "cak.or.kr")

    def __init__(self):
        self.enabled = _cfg_bool("PORTFOLIO_CLEANUP_ENABLED", True)
        self.max_actions = max(1, _cfg_int("PORTFOLIO_MAX_ACTIONS_PER_DAY", 2))
        self.min_age_days = max(7, _cfg_int("PORTFOLIO_MIN_AGE_DAYS", 30))
        self.rewrite_threshold = _cfg_float("PORTFOLIO_REWRITE_THRESHOLD", 72.0)
        self.delete_threshold = _cfg_float("PORTFOLIO_DELETE_THRESHOLD", 50.0)
        self.low_impressions = max(0, _cfg_int("PORTFOLIO_LOW_IMPRESSIONS", 40))
        self.low_ctr = _cfg_float("PORTFOLIO_LOW_CTR", 0.008)
        self.log_file = str(CONFIG.get("PORTFOLIO_LOG_FILE", "content_portfolio_actions.json")).strip() or "content_portfolio_actions.json"
        republish_mode = str(CONFIG.get("PORTFOLIO_DELETE_REPUBLISH_MODE", "deferred")).strip().lower() or "deferred"
        if republish_mode not in {"immediate", "deferred"}:
            republish_mode = "deferred"
        self.republish_mode = republish_mode
        self.republish_queue_enabled = _cfg_bool("PORTFOLIO_REPUBLISH_QUEUE_ENABLED", True)
        self.republish_queue_file = (
            str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_FILE", "logs/portfolio_republish_queue.json")).strip()
            or "logs/portfolio_republish_queue.json"
        )
        self.republish_weekday_limit = max(0, _cfg_int("PORTFOLIO_REPUBLISH_WEEKDAY_LIMIT", 1))
        self.republish_weekend_limit = max(self.republish_weekday_limit, _cfg_int("PORTFOLIO_REPUBLISH_WEEKEND_LIMIT", 2))
        self.republish_max_retries = max(1, _cfg_int("PORTFOLIO_REPUBLISH_MAX_RETRIES", 5))
        self.perf = PerformanceDataHub()

    def _load_log(self):
        if not os.path.exists(self.log_file):
            return {"actions": [], "last_run": ""}
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("actions", [])
                data.setdefault("last_run", "")
                return data
        except Exception:
            pass
        return {"actions": [], "last_run": ""}

    def _save_log(self, data):
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Portfolio log save failed: {e}")

    def _append_log(self, action, post_id, title, detail):
        data = self._load_log()
        data["last_run"] = datetime.now(timezone.utc).isoformat()
        data["actions"].append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "post_id": int(post_id),
                "title": str(title),
                "detail": detail,
            }
        )
        if len(data["actions"]) > 500:
            data["actions"] = data["actions"][-500:]
        self._save_log(data)

    def _load_republish_queue(self):
        path = self.republish_queue_file
        if not os.path.exists(path):
            return {"items": [], "updated_at": ""}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                items = data.get("items", [])
                data["items"] = items if isinstance(items, list) else []
                data.setdefault("updated_at", "")
                return data
        except Exception:
            pass
        return {"items": [], "updated_at": ""}

    def _save_republish_queue(self, data):
        path = self.republish_queue_file
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Portfolio republish queue save failed: {e}")

    def _enqueue_republish_item(self, item):
        queue = self._load_republish_queue()
        items = list(queue.get("items", []))
        old_id = int(item.get("trashed_post_id", 0) or 0)
        old_link = str(item.get("old_link", "")).strip()
        duplicate = False
        for row in items:
            row_old_id = int(row.get("trashed_post_id", 0) or 0)
            row_old_link = str(row.get("old_link", "")).strip()
            if old_id and row_old_id == old_id:
                duplicate = True
                break
            if old_link and row_old_link and old_link == row_old_link:
                duplicate = True
                break
        if duplicate:
            return {"queued": False, "duplicate": True, "queue_size": len(items)}

        items.append(item)
        if len(items) > 1500:
            items = items[-1500:]
        queue["items"] = items
        queue["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_republish_queue(queue)
        return {"queued": True, "duplicate": False, "queue_size": len(items)}

    def _parse_hour_window(self, raw_value, fallback_start, fallback_end):
        text = str(raw_value or "").strip()
        match = re.match(r"^\s*(\d{1,2})(?::\d{2})?\s*-\s*(\d{1,2})(?::\d{2})?\s*$", text)
        if not match:
            return int(fallback_start), int(fallback_end)
        start_h = int(match.group(1))
        end_h = int(match.group(2))
        start_h = min(23, max(0, start_h))
        end_h = min(23, max(0, end_h))
        return start_h, end_h

    def _within_republish_window(self, now_local):
        is_weekend = now_local.weekday() >= 5
        if is_weekend:
            window = str(CONFIG.get("PORTFOLIO_REPUBLISH_WEEKEND_WINDOW", "14:00-23:00"))
            start_h, end_h = self._parse_hour_window(window, 14, 23)
        else:
            window = str(CONFIG.get("PORTFOLIO_REPUBLISH_WEEKDAY_WINDOW", "09:00-23:00"))
            start_h, end_h = self._parse_hour_window(window, 9, 23)
        hour = int(now_local.hour)
        return (start_h <= hour <= end_h), f"{start_h:02d}:00-{end_h:02d}:00", is_weekend

    def _republish_limit_for_today(self, is_weekend):
        return self.republish_weekend_limit if is_weekend else self.republish_weekday_limit

    def _fetch_published_posts(self, wp, limit=120):
        rows = []
        page = 1
        while len(rows) < limit:
            try:
                res = requests.get(
                    f"{wp.wp_url}/posts",
                    params={
                        "per_page": min(100, limit - len(rows)),
                        "page": page,
                        "status": "publish",
                        "_fields": "id,title,slug,link,date,modified,content,excerpt,featured_media",
                    },
                    headers=wp.auth_headers,
                    timeout=15,
                )
            except requests.RequestException:
                break
            if res.status_code != 200:
                break
            data = res.json()
            if not data:
                break
            rows.extend(data)
            if page >= int(res.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1
        return rows

    def _post_signals(self, row):
        title = str(row.get("title", {}).get("rendered", "")).strip()
        content_html = str(row.get("content", {}).get("rendered", "")).strip()
        excerpt_html = str(row.get("excerpt", {}).get("rendered", "")).strip()
        plain = BeautifulSoup(content_html or excerpt_html, "html.parser").get_text(" ", strip=True)
        plain = re.sub(r"\s+", " ", plain)
        words = plain.split()
        links = re.findall(r'href="([^"]+)"', content_html)
        auth_links = [u for u in links if any(d in u for d in self.ALLOWED_AUTH_DOMAINS)]
        wp_host = _host_of(CONFIG.get("WP_URL", "")) or "seoulmna.kr"
        internal_links = []
        for u in links:
            link_host = _host_of(u)
            if not link_host:
                continue
            if link_host == wp_host or link_host.endswith(f".{wp_host}"):
                internal_links.append(u)
        has_faq = (
            ("FAQPage" in content_html)
            or ("Q</span>" in content_html and "A</span>" in content_html)
            or ("질문</span>" in content_html and "답변</span>" in content_html)
        )
        has_cta = ("open.kakao.com" in content_html) or ("tel:" in content_html)
        has_h2 = content_html.count("<h2") >= 3
        figure_count = content_html.count("<figure")
        img_count = content_html.count("<img")
        has_featured_media = int(row.get("featured_media", 0) or 0) > 0
        is_listing_style = bool(re.search(r"(매물\s*\d+|listing\s*#?\d+)", title, flags=re.IGNORECASE))
        return {
            "title": title,
            "plain_words": len(words),
            "plain_chars": len(plain),
            "auth_link_count": len(set(auth_links)),
            "internal_link_count": len(set(internal_links)),
            "has_faq_schema": has_faq,
            "has_cta": has_cta,
            "has_h2_3plus": has_h2,
            "figure_count": figure_count,
            "img_count": img_count,
            "has_featured_media": has_featured_media,
            "is_listing_style": is_listing_style,
            "content_html": content_html,
        }

    def _score(self, signals, metrics):
        score = 0.0
        words = int(signals["plain_words"])
        if words >= 1700:
            score += 20
        elif words >= 1200:
            score += 15
        elif words >= 800:
            score += 10
        else:
            score += 3

        score += min(20, signals["auth_link_count"] * 10)
        score += min(12, signals["internal_link_count"] * 4)
        if signals["has_faq_schema"]:
            score += 10
        if signals["has_cta"]:
            score += 10
        if signals["has_h2_3plus"]:
            score += 8
        if signals.get("has_featured_media"):
            score += 6
        visual_blocks = max(int(signals.get("figure_count", 0) or 0), int(signals.get("img_count", 0) or 0))
        if visual_blocks >= 4:
            score += 8
        elif visual_blocks >= 3:
            score += 6
        elif visual_blocks >= 2:
            score += 3

        impressions = int(metrics.get("impressions", 0) or 0)
        ctr = float(metrics.get("ctr", 0.0) or 0.0)
        if impressions >= 120:
            score += 10 if ctr >= 0.015 else (6 if ctr >= 0.010 else 0)
        elif impressions >= 50:
            score += 6 if ctr >= 0.012 else 2
        else:
            score += 5  # neutral when data is missing

        return round(min(100.0, score), 1)

    def _keyword_from_title(self, title):
        t = str(title or "").strip()
        if is_conversion_keyword(t):
            return t
        compact = re.sub(r"\s+", " ", t)
        listing_match = re.search(
            r"([가-힣A-Za-z·\.\-\s]{2,40}?(?:업|공사업|건설업))\s*양도양수",
            compact,
            flags=re.IGNORECASE,
        )
        if listing_match:
            base = re.sub(r"\s+", " ", listing_match.group(1)).strip(" -|")
            if base:
                return f"{base} 양도양수"
        if re.search(r"(매물\s*\d+|listing\s*#?\d+)", compact, flags=re.IGNORECASE):
            return "건설업 양도양수 매물 체크리스트"
        candidates = [
            "건설업 신규등록 요건",
            "건설업 양도양수 절차",
            "건설업 기업진단 기준",
            "건설업 실질자본금 인정 항목",
            "건설업 면허 반납 절차",
        ]
        for kw in candidates:
            if any(token in t for token in kw.split()):
                return kw
        return ""

    def _decide(self, score, metrics, age_days):
        impressions = int(metrics.get("impressions", 0) or 0)
        ctr = float(metrics.get("ctr", 0.0) or 0.0)
        if age_days < self.min_age_days:
            return "skip", "too_young"
        if score <= self.delete_threshold and impressions <= self.low_impressions and ctr <= self.low_ctr and age_days >= 45:
            return "delete_republish", "severe_low_quality_low_performance"
        if score < self.rewrite_threshold:
            return "rewrite", "quality_below_threshold"
        if impressions >= max(80, self.low_impressions * 2) and ctr <= self.low_ctr:
            return "rewrite", "high_impressions_low_ctr"
        return "skip", "healthy"

    def _render_and_gate(self, keyword, content):
        preview_wp = WPEngine(verify_auth=False, allow_no_auth=True)
        preview_html = preview_wp._render_post_html(keyword, content, include_related=False)
        qa_report = PublicationQAAuditor().audit(keyword, content, rendered_html=preview_html)
        if not qa_report.get("pass_gate"):
            failures = PublicationQAAuditor().summarize_failures(qa_report)
            raise ValueError("QA gate failed: " + ", ".join(failures[:8]))
        return preview_html

    def _rewrite_existing_post(self, wp, row, keyword):
        writer = ColumnistEngine()
        content = writer.write(keyword)
        self._render_and_gate(keyword, content)
        temp_paths = []
        try:
            visual = VisualEngine()
            cover_path = visual.generate_cover(keyword, content.get("headline", keyword))
            temp_paths.append(cover_path)
            image_plan = _inline_image_plan(content)
            inline_titles = list(image_plan.get("titles", []))
            logger.info(
                "portfolio rewrite image plan: "
                f"inline={len(inline_titles)}, plain_chars={image_plan.get('plain_chars', 0)}, faq={image_plan.get('faq_count', 0)}"
            )

            inline_paths = []
            for idx, section_title in enumerate(inline_titles, start=1):
                p = visual.generate_inline(keyword, section_title, idx)
                inline_paths.append(p)
                temp_paths.append(p)

            featured_media = wp.upload_image(
                cover_path,
                alt_text=f"{keyword} 대표 썸네일 - {content.get('headline', '')}",
                title=f"{keyword} 대표 이미지",
            )
            inline_media = [
                wp.upload_image(
                    path,
                    alt_text=f"{keyword} 본문 이미지 {idx + 1} - {inline_titles[idx]}",
                    title=inline_titles[idx],
                )
                for idx, path in enumerate(inline_paths)
            ]
            kakao_media = wp._resolve_kakao_cta_media()
            html = wp._render_post_html(
                keyword,
                content,
                featured_media=featured_media,
                inline_media=inline_media,
                include_related=True,
                kakao_media=kakao_media,
            )
            qa_report = PublicationQAAuditor().audit(
                keyword,
                content,
                rendered_html=html,
                expect_images=True,
                min_figure_count=1 + len(inline_media),
            )
            if not qa_report.get("pass_gate"):
                failures = PublicationQAAuditor().summarize_failures(qa_report)
                raise ValueError("QA gate failed: " + ", ".join(failures[:8]))

            post_id = int(row.get("id"))
            payload = {
                "title": content.get("headline", row.get("title", {}).get("rendered", "")),
                "content": html,
                "excerpt": _build_seo_description(keyword, content.get("summary", ""), min_len=110, max_len=160),
                "status": "publish",
                "featured_media": int((featured_media or {}).get("id", 0) or row.get("featured_media", 0) or 0),
            }
            res = requests.post(f"{wp.wp_url}/posts/{post_id}", headers=wp.headers, json=payload, timeout=25)
            _raise_for_status_with_context(res, f"portfolio rewrite failed(post_id={post_id})")
            seo_title = f"{payload['title']} | {CONFIG.get('BRAND_NAME', '')}".strip()
            if len(seo_title) > 60:
                seo_title = seo_title[:60].rstrip()
            wp._update_rankmath_meta(post_id=post_id, keyword=keyword, seo_title=seo_title, seo_desc=str(payload["excerpt"]))
            return res.json()
        finally:
            for path in temp_paths:
                if os.path.exists(path):
                    os.remove(path)

    def _trash_post(self, wp, post_id):
        post_id = int(post_id or 0)
        if post_id <= 0:
            raise ValueError("portfolio trash failed: invalid post_id")
        trash_res = requests.delete(
            f"{wp.wp_url}/posts/{post_id}",
            headers=wp.auth_headers,
            params={"force": "false"},
            timeout=20,
        )
        _raise_for_status_with_context(trash_res, f"portfolio trash failed(post_id={post_id})")

    def _publish_new_post(self, wp, keyword):
        writer = ColumnistEngine()
        content = writer.write(keyword)
        self._render_and_gate(keyword, content)

        temp_paths = []
        try:
            visual = VisualEngine()
            cover_path = visual.generate_cover(keyword, content.get("headline", keyword))
            temp_paths.append(cover_path)
            image_plan = _inline_image_plan(content)
            inline_titles = list(image_plan.get("titles", []))
            logger.info(
                "portfolio republish image plan: "
                f"inline={len(inline_titles)}, plain_chars={image_plan.get('plain_chars', 0)}, faq={image_plan.get('faq_count', 0)}"
            )
            inline_paths = []
            for idx, t in enumerate(inline_titles):
                p = visual.generate_inline(keyword, t, idx + 1)
                inline_paths.append(p)
                temp_paths.append(p)

            featured_media = wp.upload_image(
                cover_path,
                alt_text=f"{keyword} 대표 썸네일 - {content.get('headline', '')}",
                title=f"{keyword} 대표 이미지",
            )
            inline_media = [
                wp.upload_image(
                    path,
                    alt_text=f"{keyword} 본문 이미지 {idx + 1} - {inline_titles[idx]}",
                    title=inline_titles[idx],
                )
                for idx, path in enumerate(inline_paths)
            ]
            kakao_media = wp._resolve_kakao_cta_media()
            republish_status = str(CONFIG.get("PORTFOLIO_REPUBLISH_STATUS", "draft")).strip().lower() or "draft"
            if republish_status not in {"publish", "draft", "pending", "private"}:
                republish_status = "draft"

            res = wp.publish(
                keyword,
                content,
                featured_media,
                inline_media=inline_media,
                kakao_media=kakao_media,
                post_status=republish_status,
            )
            if res.status_code not in (200, 201):
                raise ValueError(f"Republish failed: status={res.status_code}")
            new_data = res.json()
            return {"new_post_id": new_data.get("id"), "new_link": new_data.get("link", "")}
        finally:
            for p in temp_paths:
                if os.path.exists(p):
                    os.remove(p)

    def _delete_and_republish(self, wp, row, keyword, detail=None):
        old_id = int(row.get("id"))
        self._trash_post(wp, old_id)

        if self.republish_mode == "deferred":
            detail = detail if isinstance(detail, dict) else {}
            queue_item = {
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "trashed_post_id": old_id,
                "old_link": str(row.get("link", "")).strip(),
                "old_title": str(row.get("title", {}).get("rendered", "")).strip(),
                "keyword": str(keyword or "").strip(),
                "reason": str(detail.get("reason", "")).strip(),
                "score": float(detail.get("score", 0) or 0),
                "age_days": int(detail.get("age_days", 0) or 0),
                "attempts": 0,
                "last_error": "",
            }
            queue_state = self._enqueue_republish_item(queue_item)
            return {
                "trashed_post_id": old_id,
                "queued": bool(queue_state.get("queued", False)),
                "queue_duplicate": bool(queue_state.get("duplicate", False)),
                "queue_size": int(queue_state.get("queue_size", 0) or 0),
            }

        out = self._publish_new_post(wp, keyword)
        return {"trashed_post_id": old_id, **out}

    def run_daily_cleanup(self):
        if not self.enabled:
            return {"actions": 0, "reviewed": 0}

        wp = WPEngine()
        rows = self._fetch_published_posts(wp, limit=120)
        if not rows:
            return {"actions": 0, "reviewed": 0}

        candidates = []
        now = datetime.now(timezone.utc)
        for row in rows:
            post_id = int(row.get("id") or 0)
            title = str(row.get("title", {}).get("rendered", "")).strip()
            link = str(row.get("link", "")).strip()
            date_raw = str(row.get("date", "")).strip()
            try:
                created_at = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
            except Exception:
                created_at = now
            age_days = max(0, (now - created_at).days)
            metrics = self.perf.get_page_metrics(link, days=30)
            signals = self._post_signals(row)
            score = self._score(signals, metrics)
            action, reason = self._decide(score, metrics, age_days)
            if action == "delete_republish" and signals.get("is_listing_style"):
                action, reason = "rewrite", "listing_post_rewrite_preferred"
            if action == "skip":
                continue
            candidates.append(
                {
                    "row": row,
                    "post_id": post_id,
                    "title": title,
                    "score": score,
                    "age_days": age_days,
                    "metrics": metrics,
                    "signals": {
                        "plain_words": signals.get("plain_words", 0),
                        "figure_count": signals.get("figure_count", 0),
                        "img_count": signals.get("img_count", 0),
                        "has_featured_media": bool(signals.get("has_featured_media")),
                        "is_listing_style": bool(signals.get("is_listing_style")),
                    },
                    "action": action,
                    "reason": reason,
                }
            )

        # prioritize delete_republish over rewrite, then lower score first
        candidates.sort(key=lambda x: (0 if x["action"] == "delete_republish" else 1, x["score"]))
        action_count = 0
        reviewed = len(rows)

        for item in candidates:
            if action_count >= self.max_actions:
                break
            row = item["row"]
            post_id = item["post_id"]
            title = item["title"]
            keyword = self._keyword_from_title(title)
            if not keyword:
                self._append_log("skip", post_id, title, {"reason": "keyword_unresolved", **item})
                continue

            try:
                if item["action"] == "rewrite":
                    out = self._rewrite_existing_post(wp, row, keyword)
                    self._append_log("rewrite", post_id, title, {"reason": item["reason"], "result": out, **item})
                    logger.info(f"Existing post rewrite completed: {post_id}")
                    action_count += 1
                elif item["action"] == "delete_republish":
                    out = self._delete_and_republish(wp, row, keyword, detail=item)
                    if out.get("queued") or out.get("queue_duplicate"):
                        self._append_log("delete_republish_queued", post_id, title, {"reason": item["reason"], "result": out, **item})
                        logger.info(
                            "Delete-and-queue completed: "
                            f"old={post_id}, queue_size={out.get('queue_size', 0)}, duplicate={out.get('queue_duplicate', False)}"
                        )
                    else:
                        self._append_log("delete_republish", post_id, title, {"reason": item["reason"], "result": out, **item})
                        logger.info(f"Delete-and-republish completed: old={post_id}, new={out.get('new_post_id')}")
                    action_count += 1
            except Exception as e:
                self._append_log("error", post_id, title, {"reason": item["reason"], "error": str(e), **item})
                logger.warning(f"Portfolio cleanup failed(post_id={post_id}): {e}")

        return {"actions": action_count, "reviewed": reviewed}

    def run_deferred_republish_queue(self):
        queue = self._load_republish_queue()
        items = list(queue.get("items", []))
        if not items:
            return {"queued": 0, "processed": 0, "failed": 0, "skipped_window": False}
        if not self.republish_queue_enabled:
            return {"queued": len(items), "processed": 0, "failed": 0, "skipped_window": True, "reason": "queue_disabled"}

        now_local = datetime.now().astimezone()
        in_window, window_label, is_weekend = self._within_republish_window(now_local)
        if not in_window:
            return {
                "queued": len(items),
                "processed": 0,
                "failed": 0,
                "skipped_window": True,
                "window": window_label,
            }

        max_actions = self._republish_limit_for_today(is_weekend)
        if max_actions <= 0:
            return {"queued": len(items), "processed": 0, "failed": 0, "skipped_window": True, "reason": "daily_limit_zero"}

        wp = WPEngine()
        processed = 0
        failed = 0
        remaining = []

        for item in items:
            if processed >= max_actions:
                remaining.append(item)
                continue

            keyword = str(item.get("keyword", "")).strip()
            if not keyword:
                failed += 1
                item["attempts"] = int(item.get("attempts", 0) or 0) + 1
                item["last_error"] = "keyword_missing"
                item["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
                remaining.append(item)
                continue

            try:
                out = self._publish_new_post(wp, keyword)
                old_id = int(item.get("trashed_post_id", 0) or 0)
                old_title = str(item.get("old_title", "")).strip()
                self._append_log(
                    "deferred_republish",
                    old_id or 0,
                    old_title,
                    {"queue_item": item, "result": out},
                )
                logger.info(
                    "Deferred republish completed: "
                    f"old={old_id}, new={out.get('new_post_id')}, keyword={keyword}"
                )
                processed += 1
            except Exception as e:
                failed += 1
                attempts = int(item.get("attempts", 0) or 0) + 1
                item["attempts"] = attempts
                item["last_error"] = _safe_error_text(e)
                item["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
                if "deleted and queued for deferred republish" in str(item["last_error"]).lower():
                    self._append_log(
                        "deferred_republish_requeued",
                        int(item.get("trashed_post_id", 0) or 0),
                        str(item.get("old_title", "")).strip(),
                        {"queue_item": item, "reason": "rankmath_retest_failed_requeued"},
                    )
                    logger.warning(
                        "Deferred republish re-queued by Rank Math policy: "
                        f"old={item.get('trashed_post_id')}, keyword={keyword}"
                    )
                    continue
                logger.warning(
                    "Deferred republish failed: "
                    f"old={item.get('trashed_post_id')}, keyword={keyword}, attempt={attempts}, error={item['last_error']}"
                )
                if attempts >= self.republish_max_retries:
                    self._append_log(
                        "deferred_republish_drop",
                        int(item.get("trashed_post_id", 0) or 0),
                        str(item.get("old_title", "")).strip(),
                        {"queue_item": item, "reason": "max_retries_exceeded"},
                    )
                else:
                    remaining.append(item)

        queue["items"] = remaining
        queue["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_republish_queue(queue)
        return {
            "queued": len(remaining),
            "processed": processed,
            "failed": failed,
            "skipped_window": False,
            "window": window_label,
            "is_weekend": is_weekend,
            "daily_limit": max_actions,
        }


class AIScheduleOptimizer:
    """Recommend posting time using performance data plus behavioral-economics priors."""

    PRIORS = [
        ("tuesday", "08:30", 1.00),
        ("thursday", "08:30", 0.98),
        ("wednesday", "08:40", 0.95),
        ("monday", "08:45", 0.92),
        ("tuesday", "12:20", 0.90),
        ("thursday", "12:20", 0.89),
    ]

    def __init__(self):
        self.top_slots = max(1, _cfg_int("AUTO_SCHEDULE_TOP_SLOTS", 3))
        self.lifecycle_path = str(CONFIG.get("LIFECYCLE_FILE", "content_lifecycle.json")).strip() or "content_lifecycle.json"

    def _load_lifecycle(self):
        if not os.path.exists(self.lifecycle_path):
            return {}
        try:
            with open(self.lifecycle_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _weekday_ctr_boost(self):
        data = self._load_lifecycle()
        posts = data.get("posts", {}) if isinstance(data, dict) else {}
        bucket = {}
        for row in posts.values():
            created = str(row.get("created_at", ""))
            try:
                dt = datetime.fromisoformat(created)
            except Exception:
                continue
            day = dt.strftime("%A").lower()
            ctr_vals = []
            for cp in row.get("checkpoints", []):
                metrics = cp.get("metrics", {}) or {}
                ctr = float(metrics.get("ctr", 0.0) or 0.0)
                if ctr > 0:
                    ctr_vals.append(ctr)
            if not ctr_vals:
                continue
            entry = bucket.setdefault(day, {"sum": 0.0, "n": 0})
            entry["sum"] += sum(ctr_vals) / len(ctr_vals)
            entry["n"] += 1

        result = {}
        for day, v in bucket.items():
            if v["n"] > 0:
                avg = v["sum"] / v["n"]
                # 평균 CTR 1.5%를 기준으로 정규화
                result[day] = max(-0.12, min(0.18, (avg - 0.015) * 5.0))
        return result

    def recommend_slots(self):
        boosts = self._weekday_ctr_boost()
        scored = []
        for day, hhmm, prior in self.PRIORS:
            score = prior + boosts.get(day, 0.0)
            scored.append((day, hhmm, score))
        scored.sort(key=lambda x: x[2], reverse=True)

        advisor = OpenAIKeywordAdvisor()
        if advisor.is_enabled():
            try:
                payload = {
                    "candidate_slots": [{"day": d, "time": t, "score": s} for d, t, s in scored],
                    "weekday_boosts": boosts,
                    "goal": "Choose optimal posting time for construction B2B decision audiences",
                }
                res = requests.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {advisor.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": advisor.model,
                        "input": [
                            {
                                "role": "system",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": (
                                            "You are a blog posting-time optimizer. Return JSON only. "
                                            "{\"ordered_slots\":[{\"day\":\"tuesday\",\"time\":\"08:30\"}]}"
                                        ),
                                    }
                                ],
                            },
                            {"role": "user", "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}]},
                        ],
                        "max_output_tokens": 220,
                    },
                    timeout=35,
                )
                if res.status_code == 200:
                    data = res.json()
                    raw = str(data.get("output_text", "")).strip()
                    if raw:
                        s = raw.find("{")
                        e = raw.rfind("}")
                        if s >= 0 and e > s:
                            raw = raw[s : e + 1]
                        parsed = json.loads(raw)
                        ordered = parsed.get("ordered_slots", [])
                        if isinstance(ordered, list) and ordered:
                            rank = {}
                            for idx, slot in enumerate(ordered):
                                day = str(slot.get("day", "")).lower().strip()
                                hhmm = str(slot.get("time", "")).strip()
                                if day and hhmm:
                                    rank[(day, hhmm)] = idx
                            scored.sort(key=lambda x: rank.get((x[0], x[1]), 999))
                            logger.info("OpenAI weighted rerank applied")
            except Exception:
                pass

        selected = []
        used = set()
        for day, hhmm, _score in scored:
            key = (day, hhmm)
            if key in used:
                continue
            used.add(key)
            selected.append(key)
            if len(selected) >= self.top_slots:
                break
        return selected

class BusinessKeywordRadar:
    """
    seoulmna.kr crawling-based priority keyword planner.
    Uses only conversion-intent keywords without external suggest/trend APIs,
    and excludes already-covered topics by title/slug similarity checks.
    """

    CACHE_FILE = "wp_posts_cache_business.json"
    CACHE_EXPIRY_HOURS = 3
    TOPIC_CACHE_FILE = "site_topic_cache.json"
    TOPIC_CACHE_HOURS = 12
    MAX_SITE_PAGES = 8

    PRIORITY_KEYWORDS = [
        ("신규등록", "건설업 신규등록 절차"),
        ("신규등록", "건설업 신규등록 요건"),
        ("신규등록", "건설업 신규등록 준비서류"),
        ("신규등록", "건설업 신규등록 비용"),
        ("신규등록", "전문건설업 신규등록 요건"),
        ("신규등록", "종합건설업 신규등록 요건"),
        ("양도양수", "건설업 양도양수 절차"),
        ("양도양수", "건설업 양도양수 계약서 필수조항"),
        ("양도양수", "건설업 양도양수 실사 체크리스트"),
        ("양도양수", "건설업 양도양수 세무 이슈"),
        ("양도양수", "건설업 양도양수 비용"),
        ("기업진단", "건설업 기업진단 기준"),
        ("기업진단", "건설업 입찰용 기업진단 준비"),
        ("실질자본금", "건설업 실질자본금 인정 항목"),
        ("실질자본금", "건설업 실질자본금 미달 대응"),
        ("공제조합", "건설공제조합 출자좌수 계산"),
        ("공제조합", "건설공제조합 보증 가능금액 점검"),
        ("기술인력", "건설업 기술인력 등록기준"),
        ("기술인력", "건설업 기술인력 중복 등록 주의사항"),
        ("행정처분", "건설업 행정처분 이력 점검"),
        ("행정처분", "건설업 등록기준 미달 행정처분 대응"),
        ("면허", "건설업 면허 반납 절차"),
        ("면허", "건설업 면허 추가등록 전략"),
        ("시공능력평가", "건설업 시공능력평가 준비 체크포인트"),
    ]

    SITE_TOPIC_TOKENS = {
        "신규등록": "신규등록",
        "등록기준": "신규등록",
        "양도양수": "양도양수",
        "기업진단": "기업진단",
        "실질자본금": "실질자본금",
        "공제조합": "공제조합",
        "출자좌수": "공제조합",
        "기술인력": "기술인력",
        "행정처분": "행정처분",
        "면허": "면허",
        "시공능력평가": "시공능력평가",
        "입찰": "입찰",
    }

    TOPIC_TEMPLATES = {
        "신규등록": [
            "건설업 신규등록 절차",
            "건설업 신규등록 준비서류",
            "건설업 신규등록 비용",
        ],
        "양도양수": [
            "건설업 양도양수 실사 체크리스트",
            "건설업 양도양수 계약서 필수조항",
            "건설업 양도양수 세무 이슈",
        ],
        "기업진단": [
            "건설업 기업진단 기준",
            "건설업 기업진단 보완 전략",
        ],
        "실질자본금": [
            "건설업 실질자본금 인정 항목",
            "건설업 실질자본금 미달 대응",
        ],
        "공제조합": [
            "건설공제조합 출자좌수 계산",
            "건설공제조합 보증 가능금액 점검",
        ],
        "기술인력": [
            "건설업 기술인력 등록기준",
            "건설업 기술인력 중복 등록 주의사항",
        ],
        "행정처분": [
            "건설업 행정처분 이력 점검",
            "건설업 등록기준 미달 행정처분 대응",
        ],
        "시공능력평가": [
            "건설업 시공능력평가 준비 체크포인트",
        ],
    }
    def __init__(self):
        self.existing_posts = []
        self._existing_norm_titles = set()
        self._existing_norm_slugs = set()
        self._existing_title_list = []
        self.perf_hub = PerformanceDataHub()
        self.semantic_guard = SemanticCannibalizationGuard()

    def _site_base_url(self):
        wp_url = str(CONFIG.get("WP_URL", "")).strip()
        parsed = urlparse(wp_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return "https://seoulmna.kr"

    def _is_target_domain(self, url):
        host = urlparse(url).netloc.lower()
        return "seoulmna.kr" in host

    def _safe_get(self, url):
        try:
            res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                return ""
            return res.text
        except requests.RequestException:
            return ""

    def _extract_page_blob_and_links(self, url):
        html = self._safe_get(url)
        if not html:
            return "", []
        soup = BeautifulSoup(html, "html.parser")

        text_parts = []
        if soup.title:
            text_parts.append(soup.title.get_text(" ", strip=True))
        for el in soup.select("h1, h2, h3, h4, strong, a"):
            txt = el.get_text(" ", strip=True)
            if 2 <= len(txt) <= 120:
                text_parts.append(txt)
        blob = " ".join(text_parts)

        links = []
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            full = urljoin(url, href).split("#", 1)[0]
            if self._is_target_domain(full):
                links.append(full)
        return blob, links

    def _discover_site_topics(self):
        if os.path.exists(self.TOPIC_CACHE_FILE):
            try:
                with open(self.TOPIC_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                cache_time = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
                if (datetime.now() - cache_time).total_seconds() < self.TOPIC_CACHE_HOURS * 3600:
                    topics = Counter(cache.get("topics", {}))
                    if topics:
                        return topics
            except Exception:
                pass

        seed_urls = []
        for u in [self._site_base_url(), CONFIG.get("GUIDE_LINK", ""), "https://seoulmna.kr/"]:
            u = str(u or "").strip()
            if u and self._is_target_domain(u) and u not in seed_urls:
                seed_urls.append(u)

        queue = list(seed_urls)
        visited = set()
        texts = []

        while queue and len(visited) < self.MAX_SITE_PAGES:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            blob, links = self._extract_page_blob_and_links(url)
            if blob:
                texts.append(_normalize_topic(blob))

            # Follow only links likely related to conversion-intent topics.
            for link in links:
                if link in visited or link in queue:
                    continue
                link_norm = _normalize_topic(link)
                if any(
                    token in link_norm
                    for token in [
                        "등록", "양도", "면허", "진단", "자본금", "공제", "기술인력",
                        "행정처분", "입찰", "시공능력", "guide", "license",
                    ]
                ):
                    queue.append(link)
                if len(queue) + len(visited) >= self.MAX_SITE_PAGES * 3:
                    break

        topic_scores = Counter()
        for text in texts:
            for token, topic in self.SITE_TOPIC_TOKENS.items():
                hit = text.count(token)
                if hit:
                    topic_scores[topic] += hit

        if topic_scores:
            with open(self.TOPIC_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"timestamp": datetime.now().isoformat(), "topics": dict(topic_scores)}, f, ensure_ascii=False, indent=2)
        else:
            logger.warning("Site topic scan empty. Topic cache not updated.")
        return topic_scores

    def _keyword_topic(self, keyword):
        norm = _normalize_topic(keyword)
        for token, topic in self.SITE_TOPIC_TOKENS.items():
            if token in norm:
                return topic
        return "기타"

    def _build_candidates(self, site_topics):
        # Prioritize topics frequently covered on the site.
        priority_rows = []
        for idx, (topic, kw) in enumerate(self.PRIORITY_KEYWORDS):
            priority_rows.append((kw, topic, idx))
        priority_rows.sort(
            key=lambda row: (
                site_topics.get(row[1], 0),
                -row[2],  # preserve original priority order on ties
            ),
            reverse=True,
        )

        merged = [kw for kw, _topic, _idx in priority_rows]

        # Add template keywords from top detected site topics.
        for topic, _score in site_topics.most_common(6):
            merged.extend(self.TOPIC_TEMPLATES.get(topic, []))

        unique = []
        seen = set()
        for kw in merged:
            k = _normalize_topic(kw)
            if k and k not in seen:
                seen.add(k)
                unique.append(kw)
        return unique

    @retry_request(max_retries=2, delay=1, exceptions=(requests.RequestException,))
    def _fetch_existing_posts(self, force_refresh=False):
        if (not force_refresh) and os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                cache_time = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
                if (datetime.now() - cache_time).total_seconds() < self.CACHE_EXPIRY_HOURS * 3600:
                    posts = cache.get("posts", [])
                    # Do not trust empty cache; it may come from network/auth failures.
                    if posts:
                        self._index_existing_posts(posts)
                        return posts
            except Exception:
                pass

        all_posts = []
        page = 1
        while True:
            res = requests.get(
                f"{CONFIG['WP_URL']}/posts",
                params={
                    "per_page": 100,
                    "page": page,
                    # Non-auth requests may reject mixed statuses with 400.
                    "status": "publish",
                    "_fields": "id,title,slug,status,excerpt,content",
                },
                timeout=10,
            )
            if res.status_code != 200:
                break

            data = res.json()
            if not data:
                break

            for post in data:
                all_posts.append(
                    {
                        "id": post.get("id"),
                        "title": post.get("title", {}).get("rendered", ""),
                        "slug": post.get("slug", ""),
                        "status": post.get("status", ""),
                        "excerpt": post.get("excerpt", {}).get("rendered", ""),
                        "content": post.get("content", {}).get("rendered", ""),
                    }
                )

            if page >= int(res.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1

        if all_posts:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"timestamp": datetime.now().isoformat(), "posts": all_posts}, f, ensure_ascii=False, indent=2)
        else:
            logger.warning("Existing post fetch returned 0 rows. Cache not updated.")

        self._index_existing_posts(all_posts)
        return all_posts

    def _index_existing_posts(self, posts):
        self.existing_posts = posts
        self._existing_norm_titles = {_normalize_topic(p.get("title", "")) for p in posts if p.get("title")}
        self._existing_norm_slugs = {_normalize_slug_token(p.get("slug", "")) for p in posts if p.get("slug")}
        self._existing_title_list = [t for t in self._existing_norm_titles if t]
        self.semantic_guard.update_corpus(posts)

    def _is_similar_existing(self, keyword):
        kw_norm = _normalize_topic(keyword)
        if not kw_norm:
            return True

        for t_norm in self._existing_title_list:
            if kw_norm in t_norm or t_norm in kw_norm:
                return True
            if SequenceMatcher(None, kw_norm, t_norm).ratio() >= 0.84:
                return True

        kw_slug_norm = _normalize_slug_token(build_slug_from_keyword(keyword))
        for s_norm in self._existing_norm_slugs:
            if kw_slug_norm and (kw_slug_norm in s_norm or s_norm in kw_slug_norm):
                return True
        return False

    def is_new_keyword(self, keyword):
        if not self._existing_norm_titles and not self._existing_norm_slugs:
            self._fetch_existing_posts()
        if not is_conversion_keyword(keyword):
            return False
        if self._is_similar_existing(keyword):
            return False
        dup, sim, matched = self.semantic_guard.is_semantic_duplicate(keyword)
        if dup:
            logger.info(f"Semantic duplicate blocked: '{keyword}' ~ '{matched[:50]}' ({sim:.3f})")
            return False
        return True

    def get_top_keywords(self, count=10, force_refresh=False):
        if force_refresh:
            try:
                self._fetch_existing_posts(force_refresh=True)
            except TypeError:
                # Backward compatibility for tests/patches that monkeypatch without kwargs.
                self._fetch_existing_posts()
        else:
            self._fetch_existing_posts()
        site_topics = self._discover_site_topics()
        candidates = self._build_candidates(site_topics)
        opportunities = self.perf_hub.get_low_ctr_opportunities(count=8)
        if opportunities:
            merged = opportunities + candidates
            dedup = []
            seen = set()
            for kw in merged:
                key = _normalize_topic(kw)
                if key and key not in seen:
                    seen.add(key)
                    dedup.append(kw)
            candidates = dedup
            logger.info(f"Search-opportunity boost applied to {len(opportunities)} keywords")

        topic_rank = {}
        for rank, (topic, _score) in enumerate(site_topics.most_common(8), start=1):
            topic_rank[topic] = rank

        scored = []
        total = len(candidates)
        for idx, kw in enumerate(candidates):
            if not self.is_new_keyword(kw):
                continue
            topic = self._keyword_topic(kw)
            base = (total - idx) * 12
            site_boost = site_topics.get(topic, 0) * 220
            rank_boost = max(0, 9 - topic_rank.get(topic, 9)) * 160
            intent_boost = 30 if any(x in kw for x in ["절차", "요건", "체크리스트", "비용", "준비서류", "상담"]) else 0
            scored.append((kw, base + site_boost + rank_boost + intent_boost))

        scored.sort(key=lambda x: x[1], reverse=True)
        ordered = [kw for kw, _ in scored]
        advisor = OpenAIKeywordAdvisor()
        ordered = advisor.rerank_keywords(ordered, self.existing_posts, site_topics)
        return ordered[:count]

    def mine_hot_keyword(self, force_refresh=False):
        try:
            top = self.get_top_keywords(count=1, force_refresh=force_refresh)
        except TypeError:
            # Backward compatibility for monkeypatched get_top_keywords in tests.
            top = self.get_top_keywords(count=1)
        return top[0] if top else None

# =================================================================
# [Module 1] Trend Radar - (v1 disabled) -> replaced by trend_radar_v2.py
# Legacy TrendRadar class below is kept only for backward compatibility.
# Active implementation is TrendRadarV2 in trend_radar_v2.py.
# =================================================================
class TrendRadar:
    """
    Deprecated module placeholder.
    trend_radar_v2.py의 TrendRadarV2 사용을 권장합니다.
    """

    HISTORY_FILE = "keyword_history.json"
    CACHE_FILE = "wp_posts_cache.json"
    CACHE_EXPIRY_HOURS = 6

    def __init__(self):
        self.seeds = []
        self.history = {"keywords": [], "topics": {}}
        self.existing_posts = []

    def mine_hot_keyword(self):
        return None

    def get_top_keywords(self, count=5):
        return []
# =================================================================
# [Module 2] Visual Engine - thumbnail generation
# =================================================================
class VisualEngine:
    def _base_html(self, keyword, title, subtitle, width, height):
        safe_keyword = escape(str(keyword))
        safe_title = escape(str(title))
        safe_subtitle = escape(str(subtitle))
        safe_brand = escape(str(CONFIG["BRAND_NAME"]))
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
                body {{ margin: 0; padding: 0; background: #0a1630; }}
                #container {{
                    width: {width}px; height: {height}px;
                    background:
                        radial-gradient(1400px 600px at 90% -20%, rgba(180,160,130,0.35), transparent 55%),
                        linear-gradient(145deg, #071733 0%, #113b72 52%, #0b2344 100%);
                    font-family: 'Pretendard', sans-serif;
                    color: #ffffff;
                    box-sizing: border-box;
                    position: relative;
                    padding: 56px 64px;
                    overflow: hidden;
                }}
                .chip {{
                    display: inline-block;
                    border: 1px solid rgba(255,255,255,0.35);
                    border-radius: 999px;
                    padding: 10px 18px;
                    font-size: 24px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                    margin-bottom: 24px;
                }}
                .title {{
                    font-size: 64px;
                    font-weight: 700;
                    line-height: 1.25;
                    letter-spacing: -1px;
                    max-width: 88%;
                    word-break: keep-all;
                    text-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
                }}
                .subtitle {{
                    margin-top: 20px;
                    font-size: 30px;
                    font-weight: 500;
                    color: rgba(255,255,255,0.84);
                    max-width: 88%;
                    line-height: 1.4;
                }}
                .brand {{
                    position: absolute;
                    bottom: 44px;
                    left: 64px;
                    font-size: 24px;
                    letter-spacing: 3px;
                    color: rgba(255,255,255,0.72);
                }}
                .accent {{
                    position: absolute;
                    right: -120px;
                    bottom: -120px;
                    width: 420px;
                    height: 420px;
                    border-radius: 50%;
                    background: radial-gradient(circle, rgba(180,160,130,0.32) 0%, rgba(180,160,130,0) 70%);
                }}
            </style>
        </head>
        <body>
            <div id="container">
                <div class="chip">{safe_keyword}</div>
                <div class="title">{safe_title}</div>
                <div class="subtitle">{safe_subtitle}</div>
                <div class="brand">{safe_brand}</div>
                <div class="accent"></div>
            </div>
        </body>
        </html>
        """

    @retry_request(max_retries=2, delay=2, exceptions=(Exception,))
    def _render_to_image(self, html, output_path, width, height):
        temp_html = f"temp_visual_{int(time.time() * 1000)}.html"
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html)

        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument(f"--window-size={width + 80},{height + 120}")
        opts.add_argument("--hide-scrollbars")
        opts.add_argument("--force-device-scale-factor=1")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        try:
            driver.get(f"file://{os.path.abspath(temp_html)}")
            time.sleep(1.2)
            driver.find_element(By.ID, "container").screenshot(output_path)
        finally:
            driver.quit()
            if os.path.exists(temp_html):
                os.remove(temp_html)
        return output_path

    def generate_cover(self, keyword, title, output_path="cover_thumb.png"):
        html = self._base_html(
            keyword=keyword,
            title=title,
            subtitle="건설면허 실무 실행 가이드",
            width=1200,
            height=630,
        )
        return self._render_to_image(html, output_path, 1200, 630)

    def generate_inline(self, keyword, section_title, idx):
        output_path = f"inline_{idx}.png"
        html = self._base_html(
            keyword=keyword,
            title=section_title,
            subtitle="핵심 점검 포인트와 대응 전략",
            width=1200,
            height=675,
        )
        return self._render_to_image(html, output_path, 1200, 675)

    def generate(self, keyword, title):
        # backward compatibility
        return self.generate_cover(keyword, title)


# =================================================================
# [Module 3] Columnist AI - content generation
# =================================================================
class ColumnistEngine:
    def __init__(self):
        ensure_config(["GEMINI_API_KEY"], "mnakr:columnist")
        self.client = genai.Client(api_key=CONFIG["GEMINI_API_KEY"])
        self.fact_data = get_fact_prompt_injection()
        self.local_fallback_enabled = _cfg_bool("LOCAL_LLM_FALLBACK_ENABLED", False)
        self.local_fallback_on_any_error = _cfg_bool("LOCAL_LLM_FALLBACK_ON_ANY_ERROR", False)
        self.local_llm_model = str(CONFIG.get("LOCAL_LLM_MODEL", "qwen2.5:7b-instruct")).strip()
        self.local_llm_endpoint = str(CONFIG.get("LOCAL_LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate")).strip()
        self.local_llm_timeout_sec = max(30, _cfg_int("LOCAL_LLM_TIMEOUT_SEC", 360))
        self.local_llm_num_predict = max(512, _cfg_int("LOCAL_LLM_NUM_PREDICT", 2600))
        self.local_llm_temperature = max(0.0, min(1.0, _cfg_float("LOCAL_LLM_TEMPERATURE", 0.25)))
        self.local_llm_keep_alive = str(CONFIG.get("LOCAL_LLM_KEEP_ALIVE", "20m")).strip() or "20m"
        self.openai_content_fallback_enabled = _cfg_bool("OPENAI_CONTENT_FALLBACK_ENABLED", True)
        self.openai_api_key = str(CONFIG.get("OPENAI_API_KEY", "")).strip()
        self.openai_content_model = (
            str(CONFIG.get("OPENAI_CONTENT_FALLBACK_MODEL", "")).strip()
            or str(CONFIG.get("OPENAI_MODEL", "gpt-5-mini")).strip()
        )

    @retry_request(max_retries=2, delay=3, exceptions=(Exception,))
    def write(self, keyword):
        keyword = _normalize_focus_keyword(keyword)
        if not is_conversion_keyword(keyword):
            raise ValueError("Keyword must be directly related to construction-business conversion intent.")

        system_prompt = f"""당신은 2026년 기준 건설업 컨설팅 실무 칼럼을 작성하는 한국어 전문 에디터입니다.
타겟 키워드: "{keyword}"

[최우선 원칙: 팩트 정확성]
아래 검증된 사실 데이터만 사용하고, 상충되는 수치나 표현은 절대 만들지 마세요.
{self.fact_data}

[언어 규칙]
1. 본문/제목/요약/FAQ 답변은 모두 한국어만 사용합니다.
2. 영문 단어, 영문 문장, 영문 슬로건을 쓰지 않습니다.
3. 예외는 URL, JSON 키 이름, english_slug 값만 허용합니다.

[SEO/전환 요건]
1. headline: 55자 이내, 키워드를 앞부분에 포함
2. english_slug: 소문자 하이픈 2~4 토큰
3. summary: 120~160자
4. intro: 400자 이상, 첫 문장에 키워드 포함
5. body1~body3: 각 800자 이상
6. conclusion: 300자 이상 + 상담 전환 CTA 포함
7. [FAQ]Q:...|A:...[/FAQ] 블록 2개 이상 포함
8. [EXTLINK]라벨|url[/EXTLINK] 형식의 공신력 외부 링크 1개 이상 포함
9. 체크리스트/단계/비용/일정/리스크 관점의 실무 포인트 포함

[포맷 토큰]
- 문단: [PARA]
- 핵심포인트: [POINT]...[/POINT]
- 목록: [LIST]a|b|c[/LIST]
- 숫자 강조: [NUM]...[/NUM]
- 외부링크: [EXTLINK]라벨|URL[/EXTLINK]

[출력]
아래 스키마의 JSON만 반환:
{{"headline":"","english_slug":"","summary":"","intro":"","body1_title":"","body1_text":"","body2_title":"","body2_text":"","body3_title":"","body3_text":"","conclusion":""}}
"""

        source_name = "gemini"
        logger.info("Writing content with Gemini model: gemini-2.5-pro")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=system_prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            raw_text = str(response.text or "").strip()
        except Exception as gemini_err:
            safe = _safe_error_text(gemini_err)
            is_retry_limited = self._should_use_local_fallback(gemini_err)
            openai_fallback_used = False
            if is_retry_limited and self._can_use_openai_content_fallback():
                logger.warning(
                    "Gemini quota/rate limit detected. "
                    f"Switching to OpenAI content fallback model={self.openai_content_model}."
                )
                try:
                    raw_text = self._write_with_openai(system_prompt)
                    source_name = f"openai:{self.openai_content_model}"
                    openai_fallback_used = True
                except Exception as openai_err:
                    logger.warning(
                        "OpenAI content fallback failed: "
                        f"{_safe_error_text(openai_err)}"
                    )

            if not openai_fallback_used:
                if not self.local_fallback_enabled or not is_retry_limited:
                    if is_retry_limited and not self.local_fallback_enabled:
                        cooldown_sec, cooldown_until = _set_genai_rate_limit_cooldown(
                            gemini_err,
                            context="columnist_write",
                        )
                        until_local = cooldown_until.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
                        logger.warning(
                            "Gemini quota/rate limit detected. "
                            "Local/OpenAI fallback is unavailable, so this run will wait for API reset."
                        )
                        raise RetryBypassError(
                            f"Gemini quota/rate limit detected; cooldown={cooldown_sec}s until {until_local}; "
                            f"reason={safe}"
                        ) from gemini_err
                    raise
                logger.warning(f"Gemini write failed, switching to local fallback: {safe}")
                try:
                    raw_text = self._write_with_local_llm(system_prompt)
                    source_name = f"local:{self.local_llm_model}"
                except Exception as local_err:
                    raise RuntimeError(
                        f"Gemini write failed ({safe}) and local fallback failed ({_safe_error_text(local_err)})"
                    ) from local_err

        content = self._parse_content_json(raw_text, source_name)
        logger.info(f"content generated via {source_name}")

        fact_errors = self._validate_and_warn(content)
        prev_fact_sig = self._fact_error_signature(fact_errors)
        for _ in range(3):
            if not fact_errors:
                break
            self._auto_fix_fact_errors(content, fact_errors)
            fact_errors = self._validate_and_warn(content)
            cur_fact_sig = self._fact_error_signature(fact_errors)
            if fact_errors and cur_fact_sig == prev_fact_sig:
                logger.warning("팩트 자동보정 진행 없음 - 동일 오류 반복, 추가 자동 보정 중단")
                break
            prev_fact_sig = cur_fact_sig

        self._normalize_markup_tokens(content)
        self._ensure_heading_structure(keyword, content)
        self._ensure_featured_snippet_intro(keyword, content)
        self._ensure_local_intent(keyword, content)
        self._ensure_keyword_in_headings(keyword, content)
        self._ensure_keyword_density(keyword, content)
        self._ensure_outbound_link(keyword, content)
        self._ensure_slug_and_meta(keyword, content)
        self._ensure_conversion_intent(keyword, content)
        self._ensure_behavioral_sales_blocks(keyword, content)
        self._normalize_faq_token_syntax(content)
        self._ensure_faq_blocks(keyword, content)
        self._ensure_faq_answer_depth(keyword, content)
        self._clean_placeholder_noise(content)
        self._ensure_korean_only_content(content)
        self._ensure_minimum_lengths(keyword, content)
        self._ensure_summary_signal_terms(keyword, content)
        self._ensure_summary_keyword_alignment(keyword, content)
        self._ensure_korean_naturalness(keyword, content)
        final_fact_errors = self._validate_and_warn(content)
        if final_fact_errors:
            forced = self._force_fix_remaining_fact_errors(content, final_fact_errors)
            if forced:
                self._validate_and_warn(content)
        self._seo_score_snapshot(keyword, content)
        return content

    def _should_use_local_fallback(self, error):
        if self.local_fallback_on_any_error:
            return True
        text = _safe_error_text(error).lower()
        fallback_tokens = (
            "429",
            "resource_exhausted",
            "quota exceeded",
            "rate limit",
            "timed out",
            "connection",
            "temporarily unavailable",
        )
        return any(token in text for token in fallback_tokens)

    def _can_use_openai_content_fallback(self):
        return bool(
            self.openai_content_fallback_enabled
            and self.openai_api_key
            and self.openai_content_model
        )

    def _extract_json_payload(self, raw_text):
        src = str(raw_text or "").strip()
        if not src:
            return ""
        if src.startswith("```json"):
            src = src[7:]
        if src.startswith("```"):
            src = src[3:]
        if src.endswith("```"):
            src = src[:-3]
        src = src.strip()
        if src.startswith("{") and src.endswith("}"):
            return src
        first = src.find("{")
        last = src.rfind("}")
        if first >= 0 and last > first:
            return src[first:last + 1].strip()
        return src

    def _parse_content_json(self, raw_text, source_name="unknown"):
        payload = self._extract_json_payload(raw_text)
        try:
            return json.loads(payload)
        except Exception as e:
            preview = payload[:180].replace("\n", " ")
            raise ValueError(f"invalid JSON from {source_name}: {_safe_error_text(e)} | preview={preview}") from e

    def _write_with_local_llm(self, system_prompt):
        endpoint = self.local_llm_endpoint
        if not endpoint:
            raise ValueError("LOCAL_LLM_ENDPOINT is empty")
        payload = {
            "model": self.local_llm_model,
            "prompt": system_prompt,
            "stream": False,
            "keep_alive": self.local_llm_keep_alive,
            "options": {
                "temperature": self.local_llm_temperature,
                "num_predict": self.local_llm_num_predict,
            },
        }
        start_ts = time.time()
        resp = requests.post(endpoint, json=payload, timeout=self.local_llm_timeout_sec)
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
        raw_text = str(data.get("response") or "").strip()
        if not raw_text:
            raise ValueError("local LLM returned empty response")
        eval_count = int(data.get("eval_count", 0) or 0)
        eval_duration = float(data.get("eval_duration", 0) or 0) / 1e9
        tps = (eval_count / eval_duration) if eval_duration > 0 else 0.0
        logger.info(
            "local LLM done: "
            f"model={self.local_llm_model}, wall={time.time() - start_ts:.2f}s, "
            f"eval_tokens={eval_count}, tps={tps:.1f}"
        )
        return raw_text

    def _write_with_openai(self, system_prompt):
        if not self._can_use_openai_content_fallback():
            raise ValueError("OpenAI content fallback is not configured")
        start_ts = time.time()
        res = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.openai_content_model,
                "input": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Return ONLY valid JSON that follows the requested schema. "
                                    "Do not include markdown fences."
                                ),
                            }
                        ],
                    },
                    {"role": "user", "content": [{"type": "input_text", "text": system_prompt}]},
                ],
                "max_output_tokens": 3600,
            },
            timeout=90,
        )
        if res.status_code != 200:
            raise RuntimeError(f"openai fallback failed: {res.status_code} {res.text[:220]}")
        data = res.json()
        raw_text = str(data.get("output_text", "")).strip()
        if not raw_text:
            chunks = []
            for item in data.get("output", []) or []:
                for content in item.get("content", []) or []:
                    text = content.get("text")
                    if text:
                        chunks.append(str(text))
            raw_text = "\n".join(chunks).strip()
        if not raw_text:
            raise ValueError("OpenAI fallback returned empty output")
        logger.info(
            "OpenAI content fallback done: "
            f"model={self.openai_content_model}, wall={time.time() - start_ts:.2f}s"
        )
        return raw_text

    def _ensure_heading_structure(self, keyword, content):
        heading_keys = ["body1_title", "body2_title", "body3_title"]
        defaults = ["핵심 요건", "실무 체크리스트", "실행 로드맵"]
        seen = set()
        fixed = 0

        for idx, key in enumerate(heading_keys):
            fallback = f"{keyword} {defaults[idx]}"
            title = self._sanitize_heading_text(content.get(key, ""), fallback=fallback)
            if len(_strip_markup_tokens(title)) < 6:
                title = fallback

            norm = _normalize_topic(title)
            if norm in seen:
                title = fallback
                norm = _normalize_topic(title)

            seen.add(norm)
            clipped = self._sanitize_heading_text(title, fallback=fallback)[:58].strip()
            if str(content.get(key, "")).strip() != clipped:
                fixed += 1
            content[key] = clipped

        if fixed:
            logger.info(f"Heading structure normalized: {fixed}")

    def _normalize_markup_tokens(self, content):
        fields = ["summary", "intro", "body1_text", "body2_text", "body3_text", "conclusion"]
        token_re = re.compile(r"\[\s*(/?)\s*(PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]", flags=re.IGNORECASE)
        fixed = 0
        for field in fields:
            src = str(content.get(field, ""))
            if not src:
                continue
            dst = token_re.sub(lambda m: f"[{'/' if m.group(1) else ''}{str(m.group(2)).upper()}]", src)
            if dst != src:
                content[field] = dst
                fixed += 1
        if fixed:
            logger.info(f"Markup token normalization applied: {fixed}")

    def _sanitize_heading_text(self, value, fallback=""):
        src = _strip_markup_tokens(str(value or ""))
        src = re.sub(r"\[\s*/?\s*[A-Za-z가-힣]+\s*\]", " ", src, flags=re.IGNORECASE)
        src = re.sub(r"[\u4e00-\u9fff]+", " ", src)
        src = re.sub(r"__HTML_BLOCK_\d+__", " ", src)
        src = re.sub(r"\s+", " ", src).strip(" -|:;,.")
        if src:
            return src
        return re.sub(r"\s+", " ", str(fallback or "")).strip()

    def _ensure_keyword_in_headings(self, keyword, content):
        """Ensure focus keyword appears in H2 headings."""
        kw_words = [w for w in keyword.split() if len(w) >= 2]
        if not kw_words:
            return

        heading_keys = ['body1_title', 'body2_title', 'body3_title']
        fixed = 0
        for key in heading_keys:
            title = self._sanitize_heading_text(content.get(key, ""))
            if not title:
                continue
            if any(w in title for w in kw_words):
                content[key] = title
                continue
            content[key] = self._sanitize_heading_text(f"{kw_words[0]} - {title}", fallback=title)
            fixed += 1
            logger.info(f"Heading adjusted for keyword: '{title}' -> '{content[key]}'")

        if fixed:
            logger.info(f"Heading keyword adjustments applied: {fixed}")

    def _clean_placeholder_noise(self, content):
        fields = ["headline", "summary", "intro", "body1_text", "body2_text", "body3_text", "conclusion"]
        patterns = [
            r"\b(?:tbd|lorem ipsum|coming soon|to be updated|n/?a)\b",
            r"\{\{[^{}]{1,120}\}\}",
            r"\[\[[^\[\]]{1,120}\]\]",
            r"<\s*placeholder[^>]*>",
            r"__HTML_BLOCK_\d+__",
            r"\[/\]",
        ]
        fixed = 0
        for field in fields:
            src = str(content.get(field, ""))
            dst = src
            for pattern in patterns:
                dst = re.sub(pattern, " ", dst, flags=re.IGNORECASE)
            dst = re.sub(
                r"\[LIST\]\s*(?:[a-zA-Z]|\d)\s*(?:\|\s*(?:[a-zA-Z]|\d)\s*){1,8}\[/LIST\]",
                "[LIST]핵심 요건 확인|필수 서류 점검|일정 및 리스크 관리[/LIST]",
                dst,
                flags=re.IGNORECASE,
            )
            dst = re.sub(r"[ \t]{2,}", " ", dst)
            dst = re.sub(r"\(\s*\)", "", dst)
            dst = re.sub(r"\[\s*\]", "", dst)
            dst = re.sub(r"\s+\[PARA\]", "[PARA]", dst)
            dst = re.sub(r"\[PARA\]\s+", "[PARA]", dst)
            dst = dst.strip()
            if dst != src:
                content[field] = dst
                fixed += 1
        if fixed:
            logger.info(f"Placeholder cleanup applied: {fixed}")

    def _dedupe_para_segments(self, text, max_repeat=1):
        src = str(text or "")
        if not src:
            return ""
        segments = [seg.strip() for seg in re.split(r"\[PARA\]+", src) if seg.strip()]
        if not segments:
            return src
        counts = {}
        kept = []
        for seg in segments:
            norm = re.sub(r"[\W_]+", "", _strip_markup_tokens(seg)).lower()
            if norm:
                seen = counts.get(norm, 0)
                if seen >= int(max_repeat):
                    continue
                counts[norm] = seen + 1
            kept.append(seg)
        return "[PARA]".join(kept) if kept else src

    def _ensure_summary_signal_terms(self, keyword, content):
        summary = re.sub(r"\s+", " ", str(content.get("summary", "")).strip())
        summary_lower = summary.lower()
        signal_terms = [
            "요건", "일정", "비용", "리스크", "체크리스트",
            "requirements", "timeline", "cost", "risk", "checklist",
        ]
        hit = sum(1 for term in signal_terms if term in summary_lower or term in summary)
        if hit < 2:
            summary = (
                f"{summary} {keyword} 핵심 요건, 일정, 비용, 리스크를 실무 기준으로 점검합니다."
            ).strip()
            summary = re.sub(r"\s+", " ", summary)
        if len(summary) > 160:
            summary = summary[:157].rstrip() + "..."
        if len(summary) < 110:
            summary = (
                summary
                + " 체크리스트 기반으로 진행하면 반려와 재작업을 줄일 수 있습니다."
            ).strip()
            if len(summary) > 160:
                summary = summary[:157].rstrip() + "..."
        content["summary"] = summary

    def _ensure_summary_keyword_alignment(self, keyword, content):
        keyword = _normalize_focus_keyword(keyword)
        summary = _build_seo_description(
            keyword,
            content.get("summary", ""),
            min_len=110,
            max_len=160,
        )
        content["summary"] = summary

    def _ensure_faq_answer_depth(self, keyword, content):
        _ = keyword
        fields = ["body3_text", "conclusion"]
        faq_pattern = re.compile(
            r"\[FAQ\]\s*(?:Q|질문)\s*:\s*(.+?)\|\s*(?:A|답변)\s*:\s*(.+?)\[/FAQ\]",
            flags=re.DOTALL,
        )
        fixed = 0
        quality_terms = ("timeline", "document", "risk", "cost", "일정", "서류", "리스크", "비용")

        def _upgrade(match):
            nonlocal fixed
            q = str(match.group(1)).strip()
            a = str(match.group(2)).strip()
            plain = _strip_markup_tokens(a)
            lower_plain = plain.lower()
            needs_more = len(plain) < 26 or not any(t in lower_plain or t in plain for t in quality_terms)
            if not needs_more:
                return f"[FAQ]Q: {q}|A: {a}[/FAQ]"
            fixed += 1
            upgraded = (
                f"{plain.rstrip('. ')}. 서류, 일정, 비용, 리스크를 사전 점검한 뒤 접수하면 반려 가능성을 낮출 수 있습니다."
            )
            return f"[FAQ]Q: {q}|A: {upgraded}[/FAQ]"

        for field in fields:
            src = str(content.get(field, ""))
            dst = faq_pattern.sub(_upgrade, src)
            content[field] = dst

        if fixed:
            logger.info(f"FAQ answer depth normalized: {fixed}")

    def _ensure_keyword_density(self, keyword, content):
        """Guarantee minimum keyword repetition across major sections."""
        keyword_topic = _with_particle(keyword, "은/는")
        text_fields = ['intro', 'body1_text', 'body2_text', 'body3_text', 'conclusion']
        full_text = " ".join([str(content.get(f, '')) for f in text_fields])
        kw_count = full_text.count(keyword)

        if kw_count >= 8:
            logger.info(f"Keyword density ok: '{keyword}' count={kw_count}")
            return

        logger.info(f"Keyword density low: '{keyword}' count={kw_count} -> adjusting")
        target_counts = {
            'intro': 2,
            'body1_text': 2,
            'body2_text': 2,
            'body3_text': 2,
            'conclusion': 1,
        }

        for field, target in target_counts.items():
            text_field = str(content.get(field, ''))
            if not text_field:
                continue
            current = text_field.count(keyword)
            if current >= target:
                continue

            needed = target - current
            inject_lines = [
                f"{keyword_topic} 요건·서류·일정 정합성을 먼저 맞추는 것이 핵심입니다.",
                f"{keyword} 진행 전 리스크와 비용 변수를 먼저 점검해야 재작업을 줄일 수 있습니다.",
                f"{keyword_topic} 체크리스트 기반으로 단계별 실행 순서를 확정하면 승인 확률이 높아집니다.",
            ]
            for idx in range(needed):
                inject = inject_lines[idx % len(inject_lines)]
                if '[PARA]' in text_field:
                    text_field = text_field.replace('[PARA]', f'[PARA]{inject} ', 1)
                elif '.' in text_field:
                    pos = text_field.rfind('.')
                    if pos > 0:
                        text_field = text_field[:pos] + f'. {inject}' + text_field[pos:]
                else:
                    text_field += f' {inject}'

            content[field] = text_field

        new_full = " ".join([str(content.get(f, '')) for f in text_fields])
        new_count = new_full.count(keyword)
        logger.info(f"Keyword density adjusted: {kw_count} -> {new_count}")

    def _ensure_featured_snippet_intro(self, keyword, content):
        intro = str(content.get('intro', '')).strip()
        first_para = intro.split('[PARA]', 1)[0].strip()
        first_len = len(_strip_markup_tokens(first_para))
        if keyword in first_para and 50 <= first_len <= 220:
            return

        keyword_topic = _with_particle(keyword, "은/는")
        snippet = (
            f"{keyword_topic} 요건, 일정, 비용, 리스크를 먼저 빠르게 점검하는 것이 핵심입니다. "
            "아래 체크리스트 순서대로 진행하면 반려와 재작업을 줄일 수 있습니다."
        )
        content['intro'] = f"{snippet}[PARA]{intro}" if intro else snippet
        logger.info('Featured snippet style intro was added')

    def _ensure_local_intent(self, keyword, content):
        blob = " ".join([str(content.get('intro', '')), str(content.get('conclusion', ''))])
        if 'Seoul' in blob or 'Gyeonggi' in blob or '서울' in blob or '경기' in blob:
            return
        local_line = (
            "[PARA]본 가이드는 서울·경기 실무 기준에 맞춰 정리했으며, "
            "지역별 세부 차이는 실시간 상담에서 확인할 수 있습니다."
        )
        content['conclusion'] = str(content.get('conclusion', '')) + local_line
        logger.info('Local intent line added')

    def _ensure_outbound_link(self, keyword, content):
        """Guarantee at least two authoritative outbound links."""
        self._normalize_extlink_blocks(keyword, content)
        allowed_domains = ['law.go.kr', 'cgbo.co.kr', 'kosca.or.kr', 'cak.or.kr']
        all_text = " ".join([str(content.get(f, '')) for f in ['body1_text', 'body2_text', 'body3_text']])
        existing_links = re.findall(r"\[EXTLINK\].+?\|(.+?)\[/EXTLINK\]", all_text, flags=re.DOTALL)
        authoritative = [u.strip() for u in existing_links if any(d in u for d in allowed_domains)]
        authoritative_unique = list(dict.fromkeys(authoritative))

        primary_link = ('국가법령정보센터', 'https://www.law.go.kr')
        secondary_link = ('대한건설협회', 'https://www.cak.or.kr')

        to_insert = []
        if len(authoritative_unique) < 2:
            if primary_link[1] not in authoritative_unique:
                to_insert.append(primary_link)
            if len(authoritative_unique) + len(to_insert) < 2 and secondary_link[1] not in authoritative_unique:
                to_insert.append(secondary_link)

        targets = ['body2_text', 'body1_text', 'body3_text']
        for idx, (label, url) in enumerate(to_insert):
            target = targets[min(idx, len(targets) - 1)]
            src = str(content.get(target, ''))
            if src:
                content[target] = src + f"[PARA]참고 출처: [EXTLINK]{label}|{url}[/EXTLINK]."
                logger.info(f"Outbound link inserted: {label} -> {target}")

    def _pick_authoritative_link(self, keyword, label_text=''):
        _ = f"{keyword} {label_text}"
        return ('국가법령정보센터', 'https://www.law.go.kr')

    def _normalize_extlink_blocks(self, keyword, content):
        fields = ['body1_text', 'body2_text', 'body3_text', 'conclusion', 'intro', 'summary']
        pattern = re.compile(r"\[EXTLINK\](.+?)\[/EXTLINK\]", flags=re.DOTALL)

        def repl(match):
            inner = str(match.group(1)).strip()
            if '|' in inner:
                label, url = inner.split('|', 1)
                label = str(label or "").strip() or "국가법령정보센터"
                url = str(url or "").strip() or "https://www.law.go.kr"
                return f"[EXTLINK]{label}|{url}[/EXTLINK]"
            label, url = self._pick_authoritative_link(keyword, inner)
            link_label = inner if inner else label
            return f"[EXTLINK]{link_label}|{url}[/EXTLINK]"

        fixed = 0
        for field in fields:
            src = str(content.get(field, ''))
            dst = pattern.sub(repl, src)
            if src != dst:
                content[field] = dst
                fixed += 1
        if fixed:
            logger.info(f"EXTLINK format auto-fix applied: {fixed}")

    def _ensure_slug_and_meta(self, keyword, content):
        slug = str(content.get('english_slug', '')).strip().lower()
        slug_tokens = [tok for tok in slug.split('-') if tok]
        slug_valid = bool(re.match(r'^[a-z0-9-]{8,80}$', slug)) and 2 <= len(slug_tokens) <= 8
        if not slug_valid:
            slug = build_slug_from_keyword(keyword)
            content['english_slug'] = slug
            logger.info(f"Slug normalized: {slug}")

        headline = self._sanitize_heading_text(content.get("headline", ""), fallback=keyword)
        if keyword not in headline:
            headline = f"{keyword} | {headline}" if headline else keyword
        if len(_strip_markup_tokens(headline)) < 18:
            headline = self._sanitize_heading_text(
                f"{headline} 실무 체크리스트",
                fallback=f"{keyword} 실무 체크리스트",
            )
        if len(headline) > 58:
            headline = headline[:58].rstrip()
        content["headline"] = headline

        summary = re.sub(r"\s+", " ", str(content.get('summary', '')).strip())
        if len(summary) > 160:
            summary = summary[:157].rstrip() + '...'
        elif len(summary) < 120:
            summary = (
                summary
                + f" {keyword} 요건, 일정, 비용, 리스크를 한 번에 점검할 수 있는 실무 가이드입니다."
            ).strip()
            if len(summary) > 160:
                summary = summary[:157].rstrip() + '...'
        content['summary'] = summary

        intro = str(content.get('intro', '')).strip()
        if keyword not in intro[:120]:
            content['intro'] = f"{keyword} 실행은 체크리스트 기반 사전진단부터 시작해야 합니다.[PARA]{intro}"

    def _ensure_conversion_intent(self, keyword, content):
        kakao_url = str(CONFIG.get('KAKAO_OPENCHAT_URL', '')).strip()
        kakao_link = (
            f"[PARA][EXTLINK]카카오톡 1:1 상담 바로가기|{kakao_url}[/EXTLINK]"
            if kakao_url else ''
        )
        cta = (
            "[PARA][POINT]1:1 실무 상담이 필요하면 지금 카카오톡으로 바로 문의하세요.[/POINT]"
            "[PARA]현재 법인 상태, 자본금, 기술인력, 목표 일정을 공유해 주시면 "
            "등록·추가등록·양도양수 이슈를 당일 기준으로 점검해 드립니다."
            f"{kakao_link}"
        )
        conclusion = str(content.get('conclusion', ''))
        if '상담' not in conclusion and '문의' not in conclusion:
            content['conclusion'] = conclusion + cta

        for key in ('body1_title', 'body2_title', 'body3_title'):
            title = self._sanitize_heading_text(content.get(key, ""))
            if not is_conversion_keyword(title):
                content[key] = self._sanitize_heading_text(f"{keyword} {title}".strip(), fallback=keyword)
            else:
                content[key] = title

    def _koreanize_text_block(self, text):
        src = str(text or "")
        if not src:
            return ""

        holders = {}

        def hold(match):
            key = f"@@{len(holders)}@@"
            holders[key] = match.group(0)
            return key

        # Keep URLs and markup tokens intact while normalizing language.
        src = re.sub(r"https?://[^\s\]|]+", hold, src)
        src = re.sub(
            r"\[(?:PARA|POINT|/POINT|FAQ|/FAQ|LIST|/LIST|NUM|/NUM|EXTLINK|/EXTLINK)\]",
            hold,
            src,
            flags=re.IGNORECASE,
        )

        replacements = [
            (r"\bA\s*to\s*Z\b", "처음부터 끝까지"),
            (r"\bpre[\s-]?check\b", "사전진단"),
            (r"\bcheck[\s-]?list\b", "체크리스트"),
            (r"\brisk\b", "리스크"),
            (r"\bopportunity\s*cost\b", "기회비용"),
            (r"\btimeline\b", "일정"),
            (r"\bcosts?\b", "비용"),
            (r"\bconsult(?:ation)?\b", "상담"),
            (r"\binquiry\b", "문의"),
            (r"\bcore\b", "핵심"),
            (r"\bsummary\b", "요약"),
            (r"\bfeatured\s+snippet\b", "요약 스니펫"),
            (r"\bauthoritative\b", "공신력 있는"),
            (r"\bKorea Law Information Center\b", "국가법령정보센터"),
            (r"\bKorea Construction Association\b", "대한건설협회"),
            (r"\bStep\s*([1-9])\b", r"\1단계"),
        ]
        for pattern, repl in replacements:
            src = re.sub(pattern, repl, src, flags=re.IGNORECASE)

        src = re.sub(r"\b[A-Za-z]{2,}\b", "", src)
        src = re.sub(r"[\u4e00-\u9fff]+", " ", src)
        src = re.sub(r"[^0-9A-Za-z가-힣\s\-_.:,;!?()\[\]{}\/|=+%#@<>\"'~]", " ", src)
        src = re.sub(r"\(\s*\)", "", src)
        src = re.sub(r"\[\s*\]", "", src)
        src = re.sub(r"__HTML_BLOCK_\d+__", "", src)
        src = re.sub(r"\s{2,}", " ", src)
        src = re.sub(r"\s+([,.;:!?])", r"\1", src)
        src = src.strip()

        for key, value in holders.items():
            src = src.replace(key, value)
        return src

    def _ensure_korean_only_content(self, content):
        fields = [
            "headline",
            "summary",
            "intro",
            "body1_title",
            "body1_text",
            "body2_title",
            "body2_text",
            "body3_title",
            "body3_text",
            "conclusion",
        ]
        fixed = 0
        for field in fields:
            before = str(content.get(field, ""))
            after = self._koreanize_text_block(before)
            if before != after:
                content[field] = after
                fixed += 1
        if fixed:
            logger.info(f"Korean-only normalization applied: {fixed}")

    def _ensure_korean_naturalness(self, keyword, content):
        fields = [
            "headline",
            "summary",
            "intro",
            "body1_title",
            "body1_text",
            "body2_title",
            "body2_text",
            "body3_title",
            "body3_text",
            "conclusion",
        ]
        fixed = 0
        for field in fields:
            before = str(content.get(field, ""))
            after = _naturalize_korean_text(before, keyword=keyword)
            if before != after:
                content[field] = after
                fixed += 1
        # Keep summary constraints after natural-language cleanup.
        content["summary"] = _build_seo_description(
            keyword,
            content.get("summary", ""),
            min_len=110,
            max_len=160,
        )
        if fixed:
            logger.info(f"Korean-naturalness normalization applied: {fixed}")

    def _ensure_behavioral_sales_blocks(self, keyword, content):
        body2 = str(content.get('body2_text', ''))
        body3 = str(content.get('body3_text', ''))
        conclusion = str(content.get('conclusion', ''))
        keyword_topic = _with_particle(keyword, "은/는")

        if not any(t in body2 for t in ['체크리스트', '리스크', '기회비용', '사전진단']):
            body2 += (
                f"[PARA][POINT]{keyword_topic} 체크리스트-사전진단 기반으로 진행하면 리스크와 기회비용을 줄이고 승인 확률을 높일 수 있습니다.[/POINT]"
            )
        has_kr_steps = all(x in body3 for x in ["1단계", "2단계", "3단계"])
        if not has_kr_steps:
            body3 += (
                "[PARA][LIST]"
                "1단계: 사전진단|2단계: 자본금·기술인력·서류 정합성 점검|3단계: 접수 일정 확정 및 리스크 관리"
                "[/LIST]"
            )
        if '카카오' not in conclusion and ('상담' in conclusion or '문의' in conclusion):
            kakao_url = str(CONFIG.get('KAKAO_OPENCHAT_URL', '')).strip()
            if kakao_url:
                conclusion += f"[PARA][EXTLINK]카카오톡 상담 바로가기|{kakao_url}[/EXTLINK]"

        content['body2_text'] = body2
        content['body3_text'] = body3
        content['conclusion'] = conclusion

    def _normalize_faq_token_syntax(self, content):
        fields = ["body1_text", "body2_text", "body3_text", "conclusion", "intro"]
        block_re = re.compile(r"\[FAQ\](.+?)\[/FAQ\]", flags=re.DOTALL | re.IGNORECASE)
        fixed = 0

        def _normalize_block(match):
            nonlocal fixed
            inner = str(match.group(1) or "")
            src = inner.replace("｜", "|").strip()

            m = re.match(
                r"(?is)\s*(?:Q|질문)\s*[:：]\s*(.+?)\s*\|\s*(?:A|답변)\s*[:：]\s*(.+)\s*$",
                src,
            )
            if not m:
                m = re.match(
                    r"(?is)\s*(?:Q|질문)\s*[:：]\s*(.+?)\s*(?:\n|<br\s*/?>)\s*(?:A|답변)\s*[:：]\s*(.+)\s*$",
                    src,
                )
            if not m:
                return match.group(0)

            q = re.sub(r"\s+", " ", str(m.group(1) or "")).strip()
            a = re.sub(r"\s+", " ", str(m.group(2) or "")).strip()
            if not q or not a:
                return match.group(0)

            fixed += 1
            return f"[FAQ]Q: {q}|A: {a}[/FAQ]"

        for field in fields:
            before = str(content.get(field, ""))
            after = block_re.sub(_normalize_block, before)
            content[field] = after

        if fixed:
            logger.info(f"FAQ syntax normalized: {fixed}")

    def _ensure_faq_blocks(self, keyword, content):
        combined = " ".join([str(content.get('body3_text', '')), str(content.get('conclusion', ''))])
        faq_pattern = r"\[FAQ\]\s*(?:Q|질문)\s*:\s*(.+?)\|\s*(?:A|답변)\s*:\s*(.+?)\[/FAQ\]"
        valid_faq_count = len(re.findall(faq_pattern, combined, flags=re.DOTALL))
        if valid_faq_count >= 2:
            return

        faqs = [
            f"[FAQ]Q: {keyword} 진행 기간은 얼마나 걸리나요?|A: 업종과 현재 준비상태에 따라 달라지며, 사전진단 후 당일 기준 일정표를 안내합니다.[/FAQ]",
            f"[FAQ]Q: {keyword}에서 가장 많이 막히는 지점은 무엇인가요?|A: 자본금, 기술인력, 서류 정합성 이슈가 반려의 주요 원인이라 사전 점검이 필수입니다.[/FAQ]",
        ]
        needed = 2 - valid_faq_count
        content['conclusion'] = str(content.get('conclusion', '')) + '[PARA]' + ''.join(faqs[:needed])
        logger.info(f"FAQ auto-added: {needed}")

    def _ensure_minimum_lengths(self, keyword, content):
        targets = {
            "intro": 400,
            "body1_text": 800,
            "body2_text": 800,
            "body3_text": 800,
            "conclusion": 300,
        }
        keyword_topic = _with_particle(keyword, "이/가")
        filler_pool = [
            f"{keyword_topic} 요건·서류·일정 정합성을 먼저 맞추는 것이 핵심입니다.",
            f"{keyword} 진행 전 체크리스트 기반 점검으로 재작업 가능성을 줄일 수 있습니다.",
            f"{keyword_topic} 단계별 실행 순서를 고정하면 리스크 관리가 쉬워집니다.",
            f"{keyword} 관련 비용·일정·서류를 한 번에 점검해야 누락을 줄일 수 있습니다.",
        ]

        for field, min_chars in targets.items():
            raw = str(content.get(field, "")).strip()
            if not raw:
                raw = f"{keyword} 실무 기준 핵심 항목을 이 섹션에서 정리합니다."
            guard = 0
            while len(_strip_markup_tokens(raw)) < min_chars and guard < 12:
                raw = (raw + "[PARA]" + filler_pool[guard % len(filler_pool)]).strip()
                guard += 1
            deduped = self._dedupe_para_segments(raw, max_repeat=1)
            refill = 0
            while len(_strip_markup_tokens(deduped)) < min_chars and refill < 12:
                line = filler_pool[(guard + refill) % len(filler_pool)]
                deduped = (deduped + f"[PARA]{line} ({refill + 1}단계)").strip()
                refill += 1
            content[field] = deduped

        summary = re.sub(r"\s+", " ", str(content.get("summary", "")).strip())
        if len(summary) < 110:
            summary = (
                summary
                + f" {keyword} 요건, 일정, 비용, 리스크 핵심 포인트를 빠르게 확인해보세요."
            ).strip()
        if len(summary) > 160:
            summary = summary[:157].rstrip() + "..."
        content["summary"] = summary

    def _seo_score_snapshot(self, keyword, content):
        text_blob = " ".join(
            [
                str(content.get('intro', '')),
                str(content.get('body1_text', '')),
                str(content.get('body2_text', '')),
                str(content.get('body3_text', '')),
                str(content.get('conclusion', '')),
            ]
        )
        checks = {
            'focus_in_title': keyword in str(content.get('headline', '')),
            'focus_in_intro': keyword in str(content.get('intro', ''))[:200],
            'focus_density': text_blob.count(keyword) >= 8,
            'has_outbound': '[EXTLINK]' in text_blob,
            'faq_count': text_blob.count('[FAQ]') >= 2,
            'slug_valid': bool(re.match(r'^[a-z0-9-]{8,80}$', str(content.get('english_slug', '')))),
            'summary_len': 110 <= len(str(content.get('summary', ''))) <= 160,
        }
        score = sum(1 for v in checks.values() if v) / len(checks) * 100
        logger.info(f"SEO snapshot: {score:.0f}% ({checks})")


    def _auto_fix_fact_errors(self, content, errors):
        fields = ["summary", "intro", "body1_text", "body2_text", "body3_text", "conclusion"]
        fixed = 0
        known_industries = list(CONSTRUCTION_STANDARDS.get("종합건설업", {}).keys())

        def _err_value(err_obj, *keys):
            for key in keys:
                if key in err_obj and str(err_obj.get(key, "")).strip():
                    return str(err_obj.get(key, "")).strip()
            return ""

        def _amount_variants(amount_text):
            src = str(amount_text or "").strip()
            variants = {src, src.replace(" ", ""), src.replace(",", "")}
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", src)
            if not m:
                return {v for v in variants if v}
            num_text = m.group(1)
            num_forms = {num_text}
            try:
                num_val = float(num_text)
                if abs(num_val - int(num_val)) < 1e-9:
                    num_forms.add(str(int(num_val)))
                compact = f"{num_val:.4f}".rstrip("0").rstrip(".")
                if compact:
                    num_forms.add(compact)

                # Also cover Korean amount notation variants, e.g. 8억 5천만원.
                eok_int = int(num_val)
                man_val = int(round((num_val - eok_int) * 10000))
                if man_val > 0:
                    if man_val % 1000 == 0:
                        thousand = man_val // 1000
                        variants.update(
                            {
                                f"{eok_int}억 {thousand}천만원",
                                f"{eok_int}억{thousand}천만원",
                                f"{eok_int}억 {thousand}천만 원",
                                f"{eok_int}억{thousand}천만 원",
                                f"{eok_int}억 {thousand}천만",
                                f"{eok_int}억{thousand}천만",
                            }
                        )
                    else:
                        variants.update(
                            {
                                f"{eok_int}억 {man_val}만원",
                                f"{eok_int}억{man_val}만원",
                                f"{eok_int}억 {man_val}만 원",
                                f"{eok_int}억{man_val}만 원",
                                f"{eok_int}억 {man_val}만",
                                f"{eok_int}억{man_val}만",
                            }
                        )
            except Exception:
                pass
            for n in num_forms:
                variants.add(f"{n}\uc5b5\uc6d0")
                variants.add(f"{n}\uc5b5")
                variants.add(f"{n}\uc5b5 \uc6d0")
            expanded = set()
            for token in variants:
                t = str(token or "").strip()
                if not t:
                    continue
                expanded.add(t)
                expanded.add(t.replace(" ", ""))
            return expanded

        def _has_other_industry(span_text, current_industry):
            scope = str(span_text or "")
            for name in known_industries:
                if not name or name == current_industry:
                    continue
                if name in scope:
                    return True
            return False

        for err in errors:
            wrong = _err_value(err, "\ubc1c\uacac\uac12", "諛쒓껄媛?")
            right = _err_value(err, "\uc815\ud655\uac12", "?뺥솗媛?")
            industry = _err_value(err, "\uc5c5\uc885", "?낆쥌")

            if not wrong or not right or wrong == right:
                continue

            variants = _amount_variants(wrong)
            for field in fields:
                text_field = str(content.get(field, ""))
                updated = text_field

                if industry:
                    replaced_once = False
                    for token in sorted(variants, key=len, reverse=True):
                        pattern_ctx = re.compile(
                            rf"{re.escape(industry)}[^\n]{{0,180}}?{re.escape(token)}",
                            flags=re.IGNORECASE,
                        )
                        match = None
                        for m in pattern_ctx.finditer(updated):
                            segment = m.group(0)
                            if _has_other_industry(segment, industry):
                                continue
                            match = m
                            break
                        if match:
                            s, e = match.span()
                            segment = updated[s:e]
                            segment = re.sub(
                                re.escape(token),
                                right,
                                segment,
                                count=1,
                                flags=re.IGNORECASE,
                            )
                            updated = updated[:s] + segment + updated[e:]
                            replaced_once = True
                            break
                    if replaced_once:
                        pass
                else:
                    for token in sorted(variants, key=len, reverse=True):
                        updated = updated.replace(token, right)

                if updated != text_field:
                    content[field] = updated
                    fixed += 1

        if fixed:
            logger.info(f"fact auto-fix applied: {fixed}")

    def _force_fix_remaining_fact_errors(self, content, errors):
        fields = ["summary", "intro", "body1_text", "body2_text", "body3_text", "conclusion"]
        amount_pattern = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*억(?:\s*원)?")
        fixed = 0

        def _amount_tokens(value):
            src = str(value or "").strip()
            if not src:
                return None
            match = amount_pattern.search(src.replace(",", ""))
            if not match:
                return None
            num = match.group(1)
            compact = f"{float(num):.4f}".rstrip("0").rstrip(".") if "." in num else num
            forms = {
                src,
                src.replace(",", ""),
                src.replace(" ", ""),
                f"{compact}억",
                f"{compact}억원",
                f"{compact}억 원",
            }
            return compact, [f for f in forms if f]

        for err in errors or []:
            if isinstance(err, dict):
                raw_values = err.values()
            else:
                raw_values = [err]
            values = [str(v).strip() for v in raw_values if str(v).strip()]
            amount_candidates = []
            for value in values:
                parsed = _amount_tokens(value)
                if parsed:
                    amount_candidates.append(parsed)
            if len(amount_candidates) < 2:
                continue

            wrong_num, wrong_forms = amount_candidates[0]
            right_num, right_forms = amount_candidates[1]
            if wrong_num == right_num:
                continue

            right_text = right_forms[0] if right_forms else f"{right_num}억"
            for field in fields:
                before = str(content.get(field, ""))
                after = before
                for token in sorted(set(wrong_forms), key=len, reverse=True):
                    after = after.replace(token, right_text)
                after = re.sub(
                    rf"{re.escape(wrong_num)}\s*억(?:\s*원)?",
                    f"{right_num}억",
                    after,
                    flags=re.IGNORECASE,
                )
                if after != before:
                    content[field] = after
                    fixed += 1

        if fixed:
            logger.info(f"fact force-fix applied: {fixed}")
        return fixed

    def _fact_error_signature(self, errors):
        rows = []
        for err in errors or []:
            rows.append(
                (
                    str(err.get("type", "")),
                    str(err.get("업종", "")),
                    str(err.get("항목", "")),
                    str(err.get("발견값", "")),
                    str(err.get("정확값", "")),
                )
            )
        return tuple(sorted(rows))

    def _validate_and_warn(self, content):
        full_text = "\n".join([
            content.get('intro', ''),
            content.get('body1_text', ''),
            content.get('body2_text', ''),
            content.get('body3_text', ''),
            content.get('conclusion', '')
        ])
        
        errors = validate_fact(full_text)
        if errors:
            logger.warning("⚠️ 팩트 오류 감지됨 - 수동 검토 필요")
            seen = set()
            shown = 0
            for err in errors:
                key = (
                    str(err.get("type", "")),
                    str(err.get("업종", "")),
                    str(err.get("항목", "")),
                    str(err.get("발견값", "")),
                    str(err.get("정확값", "")),
                )
                if key in seen:
                    continue
                seen.add(key)
                shown += 1
                logger.warning(f"   [{err.get('type', 'fact')}] {err.get('발견값')} -> {err.get('정확값')}")
                if shown >= 12:
                    remain = len(errors) - shown
                    if remain > 0:
                        logger.warning(f"   ... 추가 팩트 오류 {remain}건 생략")
                    break
        else:
            logger.info("✅ 팩트 검증 통과")
        return errors


# =================================================================
# [Module 3.5] QA Auditor - quality validation
class PublicationQAAuditor:
    MIN_LENGTH = {
        "intro": 400,
        "body1_text": 800,
        "body2_text": 800,
        "body3_text": 800,
        "conclusion": 300,
    }

    def _build_text_blob(self, content):
        fields = ["intro", "body1_text", "body2_text", "body3_text", "conclusion"]
        return " ".join([str(content.get(f, "")) for f in fields])

    def _section_lengths(self, content):
        result = {}
        for key in self.MIN_LENGTH:
            result[key] = len(_strip_markup_tokens(content.get(key, "")))
        return result

    def _contains_placeholder_text(self, text):
        src = str(text or "")
        patterns = [
            r"\b(?:tbd|lorem ipsum|coming soon|to be updated|n/?a)\b",
            r"\{\{[^{}]{1,120}\}\}",
            r"\[\[[^\[\]]{1,120}\]\]",
            r"<\s*placeholder[^>]*>",
        ]
        return any(re.search(pattern, src, flags=re.IGNORECASE) for pattern in patterns)

    def _extract_faq_pairs(self, text):
        src = str(text or "")
        return re.findall(
            r"\[FAQ\]\s*(?:Q|질문)\s*:\s*(.+?)\|\s*(?:A|답변)\s*:\s*(.+?)\[/FAQ\]",
            src,
            flags=re.DOTALL,
        )

    def _seo_checks(self, keyword, content):
        text_blob = self._build_text_blob(content)
        keyword_count = text_blob.count(keyword)
        intro = str(content.get("intro", ""))
        first_para = intro.split("[PARA]", 1)[0]
        allowed_domains = ["law.go.kr", "cgbo.co.kr", "kosca.or.kr", "cak.or.kr"]
        extlinks = re.findall(r"\[EXTLINK\].+?\|(.+?)\[/EXTLINK\]", text_blob, flags=re.DOTALL)
        authoritative_links = [u for u in extlinks if any(domain in u for domain in allowed_domains)]
        checks = {
            "focus_in_title": keyword in str(content.get("headline", "")),
            "focus_in_intro": keyword in str(content.get("intro", ""))[:220],
            "featured_snippet_intro": keyword in first_para and 50 <= len(_strip_markup_tokens(first_para)) <= 220,
            "focus_density": keyword_count >= 8,
            "has_outbound": "[EXTLINK]" in text_blob,
            "authoritative_links_2plus": len(set(authoritative_links)) >= 2,
            "faq_count": text_blob.count("[FAQ]") >= 2,
            "slug_valid": bool(re.match(r"^[a-z0-9-]{8,80}$", str(content.get("english_slug", "")))),
            "summary_len": 110 <= len(str(content.get("summary", ""))) <= 160,
        }
        score = round(sum(1 for v in checks.values() if v) / len(checks) * 100, 1)
        return {"score": score, "checks": checks, "keyword_count": keyword_count}

    def _content_checks(self, content):
        lengths = self._section_lengths(content)
        checks = {f"{k}_min_len": lengths[k] >= min_len for k, min_len in self.MIN_LENGTH.items()}
        plain_text = _strip_markup_tokens(self._build_text_blob(content))
        blob = self._build_text_blob(content)
        lower_blob = blob.lower()
        behavioral_terms = [
            "리스크", "기회비용", "체크리스트", "사전진단",
            "risk", "opportunity cost", "checklist", "pre-check",
            "1단계", "2단계", "3단계", "step 1", "step 2", "step 3",
        ]
        hit_count = sum(1 for t in behavioral_terms if t in blob)
        if hit_count < 3:
            hit_count = sum(1 for t in behavioral_terms if t in lower_blob)
        encoding = _mojibake_metrics(blob)
        faq_pairs = self._extract_faq_pairs(blob)
        faq_answer_lengths = [len(_strip_markup_tokens(a)) for _q, a in faq_pairs]
        headings = [str(content.get(k, "")).strip() for k in ("body1_title", "body2_title", "body3_title")]
        norm_headings = [_normalize_topic(h) for h in headings if h]
        checks["total_plain_chars"] = len(plain_text) >= sum(self.MIN_LENGTH.values())
        checks["total_plain_words"] = len(plain_text.split()) >= 450
        checks["behavioral_framework"] = hit_count >= 3
        checks["action_steps"] = (
            all(x in blob for x in ["1단계", "2단계", "3단계"])
            or all(x in lower_blob for x in ["step 1", "step 2", "step 3"])
        )
        checks["encoding_clean"] = not encoding.get("flagged", False)
        placeholder_blob = f"{blob} {str(content.get('summary', ''))}"
        checks["no_placeholder_text"] = not self._contains_placeholder_text(placeholder_blob)
        checks["faq_answer_quality"] = bool(faq_pairs) and all(length >= 18 for length in faq_answer_lengths)
        checks["heading_uniqueness"] = len(norm_headings) >= 3 and len(set(norm_headings)) == len(norm_headings)
        score = round(sum(1 for v in checks.values() if v) / len(checks) * 100, 1)
        return {
            "score": score,
            "checks": checks,
            "section_chars": lengths,
            "total_plain_chars": len(plain_text),
            "total_plain_words": len(plain_text.split()),
            "behavioral_hits": hit_count,
            "faq_count": len(faq_pairs),
            "encoding": encoding,
        }

    def _design_checks(self, html, expect_images=False, min_figure_count=1):
        figure_count = html.count("<figure")
        required_figures = max(1, int(min_figure_count or 1)) if expect_images else 0
        kakao_url = str(CONFIG.get("KAKAO_OPENCHAT_URL", "")).strip()
        encoding = _mojibake_metrics(_strip_markup_tokens(html))
        raw_token_leak = bool(
            re.search(r"\[\s*/?\s*(?:PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]", str(html), flags=re.IGNORECASE)
        )
        h2_ids = re.findall(r"<h2[^>]*\sid=[\"']([^\"']+)[\"']", str(html), flags=re.IGNORECASE)
        checks = {
            "summary_card": "background:#f8f9fb" in html and "border-left:3px solid #003764" in html,
            "toc_block": "border:1px solid #e2e8f0" in html and "<ol" in html and 'href="#' in html,
            "trust_box": (
                ("Author" in html and "Updated" in html)
                or ("작성자" in html and "업데이트" in html)
            ),
            "h2_sections": html.count("<h2 id=") >= 3,
            "cta_block": "background:#001a33" in html and ("open.kakao.com" in html or "tel:" in html),
            "kakao_emphasis": (kakao_url in html) if kakao_url else ("open.kakao.com" in html),
            "section_spacing": html.count("margin-bottom:56px;") >= 3,
            "image_blocks": (figure_count >= required_figures) if expect_images else True,
            "faq_schema": "\"FAQPage\"" in html,
            "article_schema": "\"@type\": \"Article\"" in html,
            "render_encoding_clean": not encoding.get("flagged", False),
            "no_raw_tokens_in_html": not raw_token_leak,
            "no_html_block_placeholder": "__HTML_BLOCK_" not in str(html),
            "unique_h2_ids": len(h2_ids) >= 3 and len(set(h2_ids)) == len(h2_ids),
            "no_javascript_links": "javascript:" not in str(html).lower(),
        }
        score = round(sum(1 for v in checks.values() if v) / len(checks) * 100, 1)
        return {
            "score": score,
            "checks": checks,
            "encoding": encoding,
            "figure_count": figure_count,
            "required_figures": required_figures,
        }

    def _legal_checks(self, content):
        text_blob = self._build_text_blob(content)
        fact_blob = "\n".join(
            [str(content.get(k, "")) for k in ("intro", "body1_text", "body2_text", "body3_text", "conclusion")]
        )
        fact_errors = validate_fact(fact_blob)
        allowed_domains = ["law.go.kr", "cgbo.co.kr", "kosca.or.kr", "cak.or.kr"]
        link_matches = re.findall(r"\[EXTLINK\].+?\|(.+?)\[/EXTLINK\]", text_blob)
        authoritative = [u for u in link_matches if any(domain in u for domain in allowed_domains)]
        has_law_link = any("law.go.kr" in u for u in authoritative)
        checks = {
            "fact_validation_passed": len(fact_errors) == 0,
            "has_law_go_link": has_law_link,
            "has_authoritative_external_link_2plus": len(set(authoritative)) >= 2,
        }
        score = round(sum(1 for v in checks.values() if v) / len(checks) * 100, 1)
        return {"score": score, "checks": checks, "fact_errors": fact_errors}

    def _publish_readiness_checks(self, content, rendered_html):
        headline = str(content.get("headline", "")).strip()
        summary = str(content.get("summary", "")).strip()
        slug = str(content.get("english_slug", "")).strip().lower()
        slug_tokens = [tok for tok in slug.split("-") if tok]
        blob = self._build_text_blob(content)
        faq_pairs = self._extract_faq_pairs(blob)
        faq_answer_lengths = [len(_strip_markup_tokens(a)) for _q, a in faq_pairs]

        checks = {
            "title_length_range": 18 <= len(headline) <= 58,
            "slug_token_range": bool(re.match(r"^[a-z0-9-]{8,80}$", slug)) and 2 <= len(slug_tokens) <= 8,
            "summary_no_placeholder": not self._contains_placeholder_text(summary),
            "raw_tokens_absent": not bool(
                re.search(
                    r"\[\s*/?\s*(?:PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]",
                    str(rendered_html),
                    flags=re.IGNORECASE,
                )
            ),
            "no_html_block_placeholder": "__HTML_BLOCK_" not in str(rendered_html),
            "cta_links_present": ("open.kakao.com" in str(rendered_html)) or ("tel:" in str(rendered_html)),
            "schema_blocks_present": "\"FAQPage\"" in str(rendered_html) and "\"@type\": \"Article\"" in str(rendered_html),
            "faq_answers_substantial": len(faq_pairs) >= 2 and all(length >= 18 for length in faq_answer_lengths),
        }
        score = round(sum(1 for v in checks.values() if v) / len(checks) * 100, 1)
        return {
            "score": score,
            "checks": checks,
            "faq_count": len(faq_pairs),
        }

    def audit(self, keyword, content, rendered_html=None, expect_images=False, min_figure_count=1):
        rendered_html = rendered_html or ""
        seo = self._seo_checks(keyword, content)
        text_quality = self._content_checks(content)
        design = self._design_checks(
            rendered_html,
            expect_images=expect_images,
            min_figure_count=min_figure_count,
        )
        legal = self._legal_checks(content)
        publish_readiness = self._publish_readiness_checks(content, rendered_html)
        overall = round(
            (seo["score"] + text_quality["score"] + design["score"] + legal["score"] + publish_readiness["score"]) / 5,
            1,
        )

        image_requirement_ok = True
        if expect_images:
            image_requirement_ok = bool(design.get("checks", {}).get("image_blocks", False))

        # Strict gate: SEO/text/legal/design all must pass
        pass_gate = (
            seo["score"] == 100.0
            and text_quality["score"] >= 90.0
            and legal["score"] == 100.0
            and design["score"] >= 90.0
            and publish_readiness["score"] == 100.0
            and text_quality.get("checks", {}).get("encoding_clean", False)
            and design.get("checks", {}).get("render_encoding_clean", False)
            and image_requirement_ok
        )

        report = {
            "checked_at": datetime.now().isoformat(),
            "keyword": keyword,
            "overall_score": overall,
            "pass_gate": pass_gate,
            "seo": seo,
            "content": text_quality,
            "design": design,
            "legal": legal,
            "publish_readiness": publish_readiness,
        }
        return report

    def summarize_failures(self, report):
        failures = []
        for area in ("seo", "content", "design", "legal", "publish_readiness"):
            checks = report.get(area, {}).get("checks", {})
            for name, ok in checks.items():
                if not ok:
                    failures.append(f"{area}:{name}")
        return failures

# =================================================================
# [Module 4] Publisher - WordPress 諛쒗뻾
# =================================================================
class WPEngine:
    def __init__(self, verify_auth=True, allow_no_auth=False):
        ensure_config(["WP_URL"], "mnakr:wordpress")
        self.allow_no_auth = allow_no_auth
        self.wp_url = str(CONFIG["WP_URL"]).rstrip("/")
        self.wp_json_root = self.wp_url.split("/wp/v2")[0]
        self.auth_mode, self.auth_headers = self._resolve_auth_headers()
        self.headers = {**self.auth_headers, "Content-Type": "application/json"}
        self.linker = InternalLinker(self.wp_url, self.headers)
        self._existing_index = None
        self._taxonomy_cache = {}
        self._taxonomy_lookup_cache = {}
        if verify_auth:
            self._verify_auth()

    def _resolve_auth_headers(self):
        jwt_token = str(CONFIG.get("WP_JWT_TOKEN", "")).strip()
        if jwt_token:
            return "jwt", {"Authorization": f"Bearer {jwt_token}"}

        user = str(CONFIG.get("WP_USER", "")).strip()
        app_password = str(CONFIG.get("WP_APP_PASSWORD", "")).strip()
        password = str(CONFIG.get("WP_PASSWORD", "")).strip()
        selected_password = app_password or password
        if user and selected_password:
            if app_password:
                # WP Application Password remains valid even if spaces are removed.
                selected_password = re.sub(r"\s+", "", selected_password)
            auth = base64.b64encode(f"{user}:{selected_password}".encode()).decode()
            return "basic", {"Authorization": f"Basic {auth}"}

        if self.allow_no_auth:
            return "none", {}

        raise ValueError(
            "[mnakr:wordpress] WordPress auth credentials are missing. "
            "Set WP_JWT_TOKEN or WP_USER + WP_APP_PASSWORD (recommended) in .env."
        )

    def _verify_auth(self):
        check_url = f"{self.wp_url}/users/me"
        try:
            res = requests.get(
                check_url,
                headers=self.auth_headers,
                params={"context": "edit"},
                timeout=12,
            )
        except requests.RequestException as e:
            raise ValueError(f"[mnakr:wordpress] auth preflight request failed: {e}") from e

        if res.status_code in (200, 201):
            return

        code = ""
        message = res.text[:300]
        try:
            data = res.json()
            code = str(data.get("code", ""))
            message = str(data.get("message", "")).strip() or message
        except Exception:
            pass

        raise ValueError(
            "[mnakr:wordpress] WordPress authentication failed. "
            "Use an Application Password instead of a login password, or set WP_JWT_TOKEN. "
            f"(status={res.status_code}, code={code}, message={message})"
        )

    @retry_request(max_retries=3, delay=2, exceptions=(requests.RequestException,))
    def upload_image(self, path, alt_text="", title=""):
        url = f"{self.wp_url}/media"
        headers = {
            **self.auth_headers,
            "Content-Disposition": f"attachment; filename={os.path.basename(path)}",
            "Content-Type": self._guess_content_type(path),
        }
        with open(path, 'rb') as f:
            res = requests.post(url, headers=headers, data=f, timeout=20)
        res.raise_for_status()
        media = res.json()
        media_id = media.get("id")
        if not media_id:
            raise requests.RequestException("WordPress media upload succeeded but no media id was returned.")
        if alt_text or title:
            media = self._upsert_media_meta(media_id, alt_text=alt_text, title=title) or media
        return {
            "id": media_id,
            "source_url": media.get("source_url", ""),
            "alt_text": alt_text or media.get("alt_text", ""),
            "title": title,
        }

    def _guess_content_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            return "image/jpeg"
        if ext == ".webp":
            return "image/webp"
        return "image/png"

    def _upsert_media_meta(self, media_id, alt_text="", title=""):
        payload = {}
        if alt_text:
            payload["alt_text"] = alt_text
        if title:
            payload["title"] = title
            payload["caption"] = title
            payload["description"] = title
        if not payload:
            return None

        res = requests.post(
            f"{self.wp_url}/media/{media_id}",
            headers=self.headers,
            json=payload,
            timeout=20,
        )
        res.raise_for_status()
        return res.json()


    def _format_text(self, text, is_dark_bg=False):
        if not text:
            return ""

        text_color = "#ffffff" if is_dark_bg else "#2d2d2d"
        accent_color = "#b4a082" if is_dark_bg else "#003764"
        bg_light = "rgba(255,255,255,0.08)" if is_dark_bg else "#f8fafc"
        paragraph_style = f"margin-bottom:18px;line-height:1.85;color:{text_color};"

        def safe_escape(value):
            return escape(str(value or ""), quote=False)

        def normalize_plain(value):
            text_value = str(value or "")
            text_value = text_value.replace("\r\n", "\n").replace("\r", "\n")
            return re.sub(r"\s+", " ", text_value).strip()

        def strip_inline_html(value):
            text_value = str(value or "")
            text_value = re.sub(r"&lt;/?strong[^&]*&gt;", "", text_value, flags=re.IGNORECASE)
            text_value = re.sub(r"</?strong[^>]*>", "", text_value, flags=re.IGNORECASE)
            return text_value

        def render_inline(value):
            raw = str(value or "")
            placeholders = {}

            def hold(html_fragment):
                key = f"__HTML_BLOCK_{len(placeholders)}__"
                placeholders[key] = html_fragment
                return key

            def num_replacer(match):
                inner = safe_escape(match.group(1).strip())
                return hold(f'<strong style="color:{accent_color};font-size:1.1em;">{inner}</strong>')

            raw = re.sub(r"\[NUM\](.+?)\[/NUM\]", num_replacer, raw, flags=re.DOTALL)

            def extlink_replacer(match):
                link_text = safe_escape((match.group(1) or "").strip())
                url = _sanitize_url((match.group(2) or "").strip(), default="https://www.law.go.kr")
                return hold(
                    f'<a href="{escape(url, quote=True)}" target="_blank" rel="dofollow noopener noreferrer" '
                    f'style="color:{accent_color};text-decoration:underline;">{link_text}</a>'
                )

            raw = re.sub(r"\[EXTLINK\](.+?)\|(.+?)\[/EXTLINK\]", extlink_replacer, raw, flags=re.DOTALL)

            def extlink_nourl_replacer(match):
                link_text = safe_escape((match.group(1) or "").strip() or "\uad00\ub828 \ubc95\ub839")
                default_url = _sanitize_url("https://www.law.go.kr", default="https://www.law.go.kr")
                return hold(
                    f'<a href="{escape(default_url, quote=True)}" target="_blank" rel="dofollow noopener noreferrer" '
                    f'style="color:{accent_color};text-decoration:underline;">{link_text}</a>'
                )

            raw = re.sub(r"\[EXTLINK\](.+?)\[/EXTLINK\]", extlink_nourl_replacer, raw, flags=re.DOTALL)

            def markdown_bold_replacer(match):
                inner = safe_escape(match.group(1).strip())
                return hold(f'<strong style="color:{accent_color};">{inner}</strong>')

            raw = re.sub(r"\*\*([^*]+)\*\*", markdown_bold_replacer, raw)
            escaped_text = safe_escape(raw)
            # Resolve nested placeholders. Example:
            # **[NUM]1단계[/NUM]: 설명** -> key1 contains key0 and needs second pass.
            for _ in range(4):
                changed = False
                for key, html_fragment in placeholders.items():
                    if key in escaped_text:
                        escaped_text = escaped_text.replace(key, html_fragment)
                        changed = True
                if not changed:
                    break

            # Fail-safe: never leak internal placeholder keys to published HTML.
            escaped_text = re.sub(r"__HTML_BLOCK_\d+__", "", escaped_text)
            escaped_text = escaped_text.replace("[/]", "")

            return re.sub(r"\s{2,}", " ", escaped_text).strip()

        def build_paragraph(value):
            text_value = render_inline(strip_inline_html(normalize_plain(value)))
            if not text_value:
                return ""
            return f'<p style="{paragraph_style}">{text_value}</p>'

        def build_point(raw_token):
            inner = ""
            match = re.match(
                r"^\[\s*POINT\s*\](.+?)\[\s*/\s*POINT\s*\]$",
                str(raw_token),
                flags=re.DOTALL | re.IGNORECASE,
            )
            if match:
                inner = render_inline(strip_inline_html(normalize_plain(match.group(1))))
            if not inner:
                return ""
            return (
                '<div style="background:#003764;padding:24px;margin:24px 0;border-radius:8px;">'
                '<span style="color:#b4a082;font-size:12px;">\ud575\uc2ec \ud3ec\uc778\ud2b8</span>'
                f'<p style="color:#fff;margin:8px 0 0 0;">{inner}</p>'
                "</div>"
            )

        def build_list(raw_token):
            def split_list_items_preserving_extlink(text_value):
                src = str(text_value or "")
                parts = []
                buf = []
                depth = 0
                i = 0
                while i < len(src):
                    if src.startswith("[EXTLINK]", i):
                        depth += 1
                        buf.append("[EXTLINK]")
                        i += len("[EXTLINK]")
                        continue
                    if src.startswith("[/EXTLINK]", i):
                        depth = max(0, depth - 1)
                        buf.append("[/EXTLINK]")
                        i += len("[/EXTLINK]")
                        continue
                    ch = src[i]
                    if ch == "|" and depth == 0:
                        parts.append("".join(buf))
                        buf = []
                    else:
                        buf.append(ch)
                    i += 1
                parts.append("".join(buf))
                return parts

            match = re.match(
                r"^\[\s*LIST\s*\](.+?)\[\s*/\s*LIST\s*\]$",
                str(raw_token),
                flags=re.DOTALL | re.IGNORECASE,
            )
            if not match:
                return ""
            items = []
            for item in split_list_items_preserving_extlink(match.group(1)):
                cleaned = strip_inline_html(normalize_plain(item))
                cleaned = re.sub(r"^[A-Za-z]\s*[:.)-]?\s*(?=[가-힣A-Za-z0-9])", "", cleaned).strip()
                if re.fullmatch(r"[A-Za-z]|\d+", cleaned or ""):
                    continue
                if cleaned:
                    items.append(cleaned)
            if not items:
                return ""
            items_html = "".join(
                f'<li style="padding:10px 0;border-bottom:1px solid #e2e8f0;">{render_inline(item)}</li>'
                for item in items
            )
            return (
                f'<ul style="list-style:none;padding:0;margin:24px 0;background:{bg_light};padding:8px 24px;">'
                f"{items_html}</ul>"
            )

        def build_faq(raw_token):
            match = re.match(
                r"^\[\s*FAQ\s*\]\s*(?:Q|질문)\s*:\s*(.+?)\|\s*(?:A|답변)\s*:\s*(.+?)\[\s*/\s*FAQ\s*\]$",
                str(raw_token),
                flags=re.DOTALL | re.IGNORECASE,
            )
            if not match:
                return ""
            q = render_inline(strip_inline_html(normalize_plain(match.group(1))))
            a = render_inline(strip_inline_html(normalize_plain(match.group(2))))
            if not q or not a:
                return ""
            return (
                f'<div style="background:{bg_light};border-left:3px solid #b4a082;padding:20px 24px;margin:20px 0;">'
                '<span style="background:#003764;color:#fff;padding:4px 12px;margin-right:12px;">질문</span>'
                f'<span style="font-weight:600;">{q}</span><br>'
                '<span style="background:#b4a082;color:#fff;padding:4px 12px;margin-right:12px;">답변</span>'
                f"{a}</div>"
            )

        block_pattern = re.compile(
            r"\[\s*FAQ\s*\]\s*(?:Q|질문)\s*:\s*.+?\|\s*(?:A|답변)\s*:\s*.+?\[\s*/\s*FAQ\s*\]"
            r"|\[\s*POINT\s*\].+?\[\s*/\s*POINT\s*\]"
            r"|\[\s*LIST\s*\].+?\[\s*/\s*LIST\s*\]",
            flags=re.DOTALL | re.IGNORECASE,
        )

        def build_block(raw_token):
            token = str(raw_token or "")
            if re.match(r"^\[\s*FAQ\s*\]", token, flags=re.IGNORECASE):
                return build_faq(token)
            if re.match(r"^\[\s*POINT\s*\]", token, flags=re.IGNORECASE):
                return build_point(token)
            if re.match(r"^\[\s*LIST\s*\]", token, flags=re.IGNORECASE):
                return build_list(token)
            return ""

        source = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        segments = [seg.strip() for seg in re.split(r"\[PARA\]+", source) if seg.strip()]
        blocks = []

        for segment in segments:
            cursor = 0
            for match in block_pattern.finditer(segment):
                plain_prefix = segment[cursor:match.start()]
                if plain_prefix.strip():
                    paragraph = build_paragraph(plain_prefix)
                    if paragraph:
                        blocks.append(paragraph)
                block_html = build_block(match.group(0))
                if block_html:
                    blocks.append(block_html)
                cursor = match.end()

            plain_suffix = segment[cursor:]
            if plain_suffix.strip():
                paragraph = build_paragraph(plain_suffix)
                if paragraph:
                    blocks.append(paragraph)

        if not blocks:
            fallback = build_paragraph(source)
            rendered = fallback or ""
            rendered = re.sub(
                r"\[\s*/?\s*(?:PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]",
                "",
                rendered,
                flags=re.IGNORECASE,
            )
            rendered = re.sub(r"\s{2,}", " ", rendered)
            return rendered

        rendered = "".join(blocks)
        rendered = re.sub(
            r"\[\s*/?\s*(?:PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]",
            "",
            rendered,
            flags=re.IGNORECASE,
        )
        rendered = re.sub(r"\s{2,}", " ", rendered)
        return rendered

    def _summary_for_display(self, text):
        src = _naturalize_korean_text(text)
        if src.endswith("...") or src.endswith("…") or src.endswith("&hellip;"):
            src = src.replace("&hellip;", "").rstrip(" .,…;:")
            src = f"{src} 내용을 본문에서 이어서 확인하세요."
        return _naturalize_korean_text(src)

    def _image_html(self, media, fallback_alt=""):
        if not media:
            return ""
        src = _sanitize_url(str(media.get("source_url", "")).strip(), default="")
        if not src:
            return ""
        alt = escape(str(media.get("alt_text", "") or fallback_alt))
        title = escape(str(media.get("title", "") or ""))
        return (
            '<figure style="margin:26px 0 34px 0;">'
            f'<img src="{escape(src, quote=True)}" alt="{alt}" title="{title}" '
            'loading="lazy" decoding="async" '
            'style="width:100%;height:auto;border-radius:10px;box-shadow:0 8px 20px rgba(0,0,0,.12);" />'
            "</figure>"
        )

    def _slugify_anchor(self, text, default_name="section"):
        anchor = _normalize_topic(text)[:40]
        return anchor or default_name

    def _article_schema_html(self, keyword, content, featured_media):
        image_url = ""
        if isinstance(featured_media, dict):
            image_url = _sanitize_url(str(featured_media.get("source_url", "")).strip(), default="")
        text_blob = " ".join(
            [
                str(content.get("intro", "")),
                str(content.get("body1_text", "")),
                str(content.get("body2_text", "")),
                str(content.get("body3_text", "")),
                str(content.get("conclusion", "")),
            ]
        )
        word_count = len(_strip_markup_tokens(text_blob).split())
        citations = re.findall(r"\[EXTLINK\].+?\|(.+?)\[/EXTLINK\]", text_blob, flags=re.DOTALL)
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": str(content.get("headline", "")),
            "description": str(content.get("summary", "")),
            "keywords": [keyword],
            "inLanguage": "ko-KR",
            "wordCount": word_count,
            "mainEntityOfPage": {"@type": "WebPage"},
            "datePublished": datetime.now(timezone.utc).isoformat(),
            "dateModified": datetime.now(timezone.utc).isoformat(),
            "author": {"@type": "Person", "name": str(CONFIG.get("CONSULTANT_NAME", ""))},
            "publisher": {
                "@type": "Organization",
                "name": str(CONFIG.get("BRAND_NAME", "")),
            },
        }
        if image_url:
            schema["image"] = [image_url]
        if citations:
            schema["citation"] = list(dict.fromkeys(citations))[:5]
        return f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    def _resolve_local_media_path(self, image_path, fallbacks):
        raw = pathlib.Path(str(image_path or "").strip())
        base_dir = pathlib.Path(__file__).resolve().parent
        home_dir = pathlib.Path.home()
        candidate_paths = []

        if raw:
            if raw.is_absolute():
                candidate_paths.append(raw)
            else:
                candidate_paths.extend(
                    [
                        pathlib.Path.cwd() / raw,
                        base_dir / raw,
                        home_dir / "Desktop" / raw.name,
                        home_dir / "Pictures" / raw.name,
                        base_dir / "assets" / raw.name,
                        base_dir / "images" / raw.name,
                    ]
                )

        for name in fallbacks:
            filename = pathlib.Path(name).name
            candidate_paths.extend(
                [
                    pathlib.Path.cwd() / filename,
                    base_dir / filename,
                    home_dir / "Desktop" / filename,
                    home_dir / "Pictures" / filename,
                    base_dir / "assets" / filename,
                    base_dir / "images" / filename,
                ]
            )

        seen = set()
        for cand in candidate_paths:
            key = str(cand).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                if cand.exists() and cand.is_file():
                    return str(cand)
            except Exception:
                continue
        return ""

    def _discover_kakao_og_image(self, openchat_url):
        url = _sanitize_url(str(openchat_url or "").strip(), default="")
        if not url:
            return ""
        try:
            res = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
            )
            if res.status_code != 200:
                return ""
            match = re.search(
                r'<meta[^>]+property=[\"\']og:image[\"\'][^>]+content=[\"\']([^\"\']+)[\"\']',
                str(res.text or ""),
                flags=re.IGNORECASE,
            )
            if not match:
                return ""
            return _sanitize_url(unescape(match.group(1).strip()), default="")
        except Exception:
            return ""

    def _resolve_kakao_cta_media(self):
        channel_name = str(CONFIG.get("KAKAO_CHANNEL_NAME", "카카오 채널"))
        direct_url = _sanitize_url(str(CONFIG.get("KAKAO_CTA_IMAGE_URL", "")).strip(), default="")
        if direct_url:
            return {
                "id": None,
                "source_url": direct_url,
                "alt_text": f"{channel_name} 상담 이미지",
                "title": channel_name,
            }

        configured_path = str(CONFIG.get("KAKAO_CTA_IMAGE_PATH", "")).strip()
        resolved_path = self._resolve_local_media_path(
            configured_path,
            (
                "kakao_cta.png",
                "kakao_cta.jpg",
                "kakao_cta.jpeg",
                "kakao_cta.webp",
                "kakao.png",
                "kakao.jpg",
            ),
        )
        if resolved_path:
            try:
                return self.upload_image(
                    resolved_path,
                    alt_text=f"{channel_name} 상담 이미지",
                    title=channel_name,
                )
            except Exception as e:
                logger.warning(f"Kakao CTA image upload failed: {e}")

        og_image = self._discover_kakao_og_image(str(CONFIG.get("KAKAO_OPENCHAT_URL", "")).strip())
        if og_image:
            logger.info(f"Kakao CTA image resolved from openchat og:image: {og_image}")
            return {
                "id": None,
                "source_url": og_image,
                "alt_text": f"{channel_name} 상담 이미지",
                "title": channel_name,
            }

        if configured_path:
            logger.warning(f"Kakao CTA image not found: {configured_path}")
        return None

    def _clean_display_heading(self, value, fallback=""):
        text = _strip_markup_tokens(str(value or ""))
        text = re.sub(r"\[\s*/?\s*[A-Za-z가-힣]+\s*\]", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"[\u4e00-\u9fff]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" -|:;,.")
        if text:
            return text
        return re.sub(r"\s+", " ", str(fallback or "")).strip()

    def _render_post_html(
        self,
        keyword,
        content,
        featured_media=None,
        inline_media=None,
        include_related=True,
        kakao_media=None,
    ):
        brand = CONFIG['BRAND_NAME']
        consultant = CONFIG['CONSULTANT_NAME']
        phone = CONFIG['PHONE']
        kakao_url = _sanitize_url(str(CONFIG.get("KAKAO_OPENCHAT_URL", "")).strip(), default="#")
        kakao_channel = str(CONFIG.get("KAKAO_CHANNEL_NAME", "카카오 채널")).strip()
        inline_media = inline_media or []
        summary_display = self._summary_for_display(content.get("summary", ""))

        hero_img = self._image_html(featured_media, fallback_alt=f"{keyword} 대표 이미지")
        body1_img = self._image_html(
            inline_media[0] if len(inline_media) > 0 else None,
            fallback_alt=f"{keyword} 본문 이미지 1",
        )
        body2_img = self._image_html(
            inline_media[1] if len(inline_media) > 1 else None,
            fallback_alt=f"{keyword} 본문 이미지 2",
        )
        body3_img = self._image_html(
            inline_media[2] if len(inline_media) > 2 else None,
            fallback_alt=f"{keyword} 본문 이미지 3",
        )
        kakao_img = self._image_html(kakao_media, fallback_alt=f"{kakao_channel} 상담 이미지")
        if kakao_img and kakao_url:
            kakao_img = (
                f'<a href="{escape(kakao_url, quote=True)}" target="_blank" rel="noopener nofollow" '
                f'style="display:block;text-decoration:none;">{kakao_img}</a>'
            )

        body1_title = self._clean_display_heading(content.get("body1_title", ""), fallback=f"{keyword} 핵심 정리")
        body2_title = self._clean_display_heading(content.get("body2_title", ""), fallback=f"{keyword} 체크리스트")
        body3_title = self._clean_display_heading(content.get("body3_title", ""), fallback=f"{keyword} 실행 가이드")
        body1_id = self._slugify_anchor(body1_title, "body1")
        body2_id = self._slugify_anchor(body2_title, "body2")
        body3_id = self._slugify_anchor(body3_title, "body3")
        updated_at = datetime.now().strftime("%Y-%m-%d")

        toc_html = f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:18px 22px;margin:18px 0 30px 0;">
    <div style="font-size:14px;font-weight:700;color:#003764;margin-bottom:10px;">목차</div>
    <ol style="margin:0;padding-left:18px;line-height:1.8;">
        <li><a href="#{body1_id}" style="color:#003764;text-decoration:none;">{escape(str(body1_title))}</a></li>
        <li><a href="#{body2_id}" style="color:#003764;text-decoration:none;">{escape(str(body2_title))}</a></li>
        <li><a href="#{body3_id}" style="color:#003764;text-decoration:none;">{escape(str(body3_title))}</a></li>
    </ol>
</div>
"""

        trust_html = f"""
<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;margin:0 0 28px 0;font-size:14px;color:#31475b;">
    <strong style="color:#003764;">작성자</strong> {escape(str(consultant))} |
    <strong style="color:#003764;">업데이트</strong> {updated_at} |
    <strong style="color:#003764;">검토 기준</strong> 최신 법령 및 실무 사례
</div>
"""

        full_text = content.get('body1_text', '') + content.get('body2_text', '')
        related_posts = self.linker.find_related_posts(keyword, full_text) if include_related else []

        html = f"""
<div style="font-family:'Pretendard',-apple-system,sans-serif;color:#1a1a1a;line-height:1.95;max-width:780px;margin:0 auto;padding:0 24px;">
    <div style="background:#f8f9fb;padding:36px 40px;margin-bottom:48px;border-left:3px solid #003764;">
        <div style="font-size:17px;font-weight:600;color:#003764;">핵심 요약</div>
        <div style="margin-top:12px;">{self._format_text(summary_display)}</div>
    </div>
    {trust_html}
    {hero_img}
    <div style="font-size:19px;margin-bottom:56px;">{self._format_text(content.get('intro', ''))}</div>
    {toc_html}
    {body1_img}
    <div style="margin-bottom:56px;">
        <h2 id="{body1_id}" style="font-size:26px;font-weight:600;color:#003764;margin-bottom:28px;border-bottom:2px solid #003764;display:inline-block;padding-right:60px;padding-bottom:16px;">{content.get('body1_title', '')}</h2>
        <div style="font-size:19px;">{self._format_text(content.get('body1_text', ''))}</div>
    </div>
    {body2_img}
    <div style="margin-bottom:56px;">
        <h2 id="{body2_id}" style="font-size:26px;font-weight:600;color:#003764;margin-bottom:28px;border-bottom:2px solid #003764;display:inline-block;padding-right:60px;padding-bottom:16px;">{content.get('body2_title', '')}</h2>
        <div style="font-size:19px;">{self._format_text(content.get('body2_text', ''))}</div>
    </div>
    {body3_img}
    <div style="margin-bottom:56px;">
        <h2 id="{body3_id}" style="font-size:26px;font-weight:600;color:#003764;margin-bottom:28px;border-bottom:2px solid #003764;display:inline-block;padding-right:60px;padding-bottom:16px;">{content.get('body3_title', '')}</h2>
        <div style="font-size:19px;">{self._format_text(content.get('body3_text', ''))}</div>
    </div>
    <div style="background:#003764;padding:44px 48px;margin:56px 0;">
        <div style="font-size:20px;font-weight:600;color:#fff;margin-bottom:20px;">결론 및 실행 제안</div>
        <div style="font-size:18px;color:rgba(255,255,255,0.92);">{self._format_text(content.get('conclusion', ''), is_dark_bg=True)}</div>
    </div>
    <div style="background:#001a33;padding:52px 48px;text-align:center;margin:48px 0;">
        <div style="font-size:15px;color:#b4a082;letter-spacing:4px;margin-bottom:16px;">{brand}</div>
        <div style="font-size:28px;color:#fff;margin-bottom:14px;">지금 바로 카카오 상담 시작</div>
        <div style="font-size:17px;color:rgba(255,255,255,0.78);margin-bottom:20px;">{consultant}가 직접 응답합니다.</div>
        <a href="{escape(kakao_url, quote=True)}" target="_blank" rel="noopener nofollow"
           style="display:inline-block;background:#fee500;color:#191919;padding:18px 34px;text-decoration:none;font-weight:700;font-size:21px;border-radius:10px;margin-bottom:18px;">
            카카오톡 1:1 문의
        </a>
        {kakao_img}
        <div style="margin-top:22px;font-size:14px;color:rgba(255,255,255,0.62);">
            전화 상담: <a href="tel:{phone.replace('-', '')}" style="color:#fff;text-decoration:underline;">{phone}</a>
        </div>
    </div>
</div>
"""

        if related_posts:
            html = self.linker.inject_links(html, related_posts, keyword=keyword)

        faqs = extract_faqs_from_content(html)
        if faqs:
            html += generate_faq_schema(faqs)
        html += self._article_schema_html(keyword, content, featured_media)

        return html

    def _update_rankmath_meta(self, post_id, keyword, seo_title, seo_desc):
        endpoint = f"{self.wp_json_root}/rankmath/v1/updateMeta"
        # Rank Math custom endpoint update.
        meta_payload = {
            "focus_keyword": keyword,
            "rank_math_focus_keyword": keyword,
            "title": seo_title,
            "rank_math_title": seo_title,
            "description": seo_desc,
            "rank_math_description": seo_desc,
        }
        payload = {"objectType": "post", "objectID": int(post_id), "meta": meta_payload}
        try:
            res = requests.post(endpoint, headers=self.headers, json=payload, timeout=20)
            if res.status_code not in (200, 201):
                logger.warning(f"Rank Math updateMeta failed: {res.status_code} {res.text[:200]}")
                return False
            logger.info("Rank Math updateMeta applied")
        except requests.RequestException as e:
            logger.warning(f"Rank Math updateMeta request failed: {e}")
            return False

        # optional: trigger score refresh endpoint
        score_ep = f"{self.wp_json_root}/rankmath/v1/updateSeoScore"
        try:
            score_payload = {"postScores": {str(post_id): 100}}
            score_res = requests.post(score_ep, headers=self.headers, json=score_payload, timeout=10)
            if score_res.status_code in (200, 201):
                logger.info("Rank Math score refresh requested")
            elif score_res.status_code == 403:
                logger.info("Rank Math score refresh skipped due to permission")
            else:
                logger.warning(f"Rank Math score refresh response: {score_res.status_code} {score_res.text[:200]}")
        except requests.RequestException:
            pass

        retest_result = True
        # optional: retry Rank Math Re-test endpoint to reduce flaky manual retries.
        retest_attempts = max(0, _cfg_int("RANKMATH_RETEST_ATTEMPTS", 2))
        if retest_attempts > 0:
            retest_ep = f"{self.wp_json_root}/rankmath/v1/an/getPageSEOScore"
            retest_timeout = max(10, _cfg_int("RANKMATH_RETEST_TIMEOUT_SEC", 35))
            force_retest = _cfg_bool("RANKMATH_RETEST_FORCE", False)
            retest_ok = False
            for attempt in range(1, retest_attempts + 1):
                try:
                    retest_payload = {
                        "id": int(post_id),
                        "objectID": int(post_id),
                        "force": bool(force_retest and attempt == retest_attempts),
                    }
                    retest_res = requests.post(
                        retest_ep,
                        headers=self.headers,
                        json=retest_payload,
                        timeout=retest_timeout,
                    )
                    if retest_res.status_code not in (200, 201):
                        logger.warning(
                            "Rank Math re-test response: "
                            f"attempt={attempt}, status={retest_res.status_code}, body={retest_res.text[:180]}"
                        )
                        time.sleep(min(6, attempt * 2))
                        continue
                    data = retest_res.json() if retest_res.text else {}
                    if isinstance(data, dict) and data.get("success"):
                        score_data = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
                        logger.info(
                            "Rank Math re-test success: "
                            f"attempt={attempt}, page_score={score_data.get('page_score', 'N/A')}"
                        )
                        retest_ok = True
                        break
                    msg = ""
                    if isinstance(data, dict):
                        detail = data.get("data", {})
                        if isinstance(detail, dict):
                            msg = str(detail.get("message", "") or "")
                    logger.warning(
                        "Rank Math re-test failed: "
                        f"attempt={attempt}, message={msg[:180] if msg else retest_res.text[:180]}"
                    )
                except requests.RequestException as e:
                    logger.warning(f"Rank Math re-test request failed(attempt={attempt}): {e}")
                time.sleep(min(6, attempt * 2))
            if not retest_ok:
                logger.warning(f"Rank Math re-test did not succeed after {retest_attempts} attempts (post_id={post_id})")
                retest_result = False
        return retest_result

    def _build_taxonomy_source_text(self, keyword, content=None):
        chunks = [str(keyword or "")]
        if isinstance(content, dict):
            for key in (
                "headline",
                "summary",
                "intro",
                "body1_title",
                "body1_text",
                "body2_title",
                "body2_text",
                "body3_title",
                "body3_text",
                "conclusion",
            ):
                chunks.append(str(content.get(key, "") or ""))
        return " ".join(chunks)

    def _fetch_taxonomy_terms(self, taxonomy, force=False):
        taxonomy = str(taxonomy or "").strip().lower()
        if taxonomy not in {"categories", "tags"}:
            raise ValueError(f"Unsupported taxonomy: {taxonomy}")
        if (not force) and (taxonomy in self._taxonomy_cache):
            return self._taxonomy_cache.get(taxonomy, [])

        rows = []
        page = 1
        while True:
            res = requests.get(
                f"{self.wp_url}/{taxonomy}",
                headers=self.auth_headers,
                params={
                    "per_page": 100,
                    "page": page,
                    "hide_empty": False,
                    "_fields": "id,name,slug,parent,count",
                },
                timeout=15,
            )
            if res.status_code != 200:
                logger.warning(f"taxonomy fetch failed ({taxonomy}, status={res.status_code})")
                break
            data = res.json()
            if not data:
                break
            rows.extend(data)
            if page >= int(res.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1

        self._taxonomy_cache[taxonomy] = rows
        self._taxonomy_lookup_cache.pop(taxonomy, None)
        return rows

    def _get_taxonomy_lookup(self, taxonomy):
        taxonomy = str(taxonomy or "").strip().lower()
        cached = self._taxonomy_lookup_cache.get(taxonomy)
        if cached is not None:
            return cached

        rows = self._fetch_taxonomy_terms(taxonomy, force=False)
        by_slug = {}
        by_slug_norm = {}
        by_name_norm = {}
        by_id_name = {}
        by_id_slug = {}
        for row in rows:
            term_id = int(row.get("id", 0) or 0)
            if not term_id:
                continue
            name = str(row.get("name", "") or "").strip()
            slug = str(row.get("slug", "") or "").strip()
            name_norm = _normalize_topic(name)
            slug_norm = _normalize_slug_token(slug)
            if slug and slug not in by_slug:
                by_slug[slug] = term_id
            if slug_norm and slug_norm not in by_slug_norm:
                by_slug_norm[slug_norm] = term_id
            if name_norm and name_norm not in by_name_norm:
                by_name_norm[name_norm] = term_id
            by_id_name[term_id] = name
            by_id_slug[term_id] = slug

        out = {
            "rows": rows,
            "by_slug": by_slug,
            "by_slug_norm": by_slug_norm,
            "by_name_norm": by_name_norm,
            "by_id_name": by_id_name,
            "by_id_slug": by_id_slug,
        }
        self._taxonomy_lookup_cache[taxonomy] = out
        return out

    def _find_term_id_by_slug(self, taxonomy, slug):
        raw_slug = str(slug or "").strip()
        if not raw_slug:
            return 0
        lookup = self._get_taxonomy_lookup(taxonomy)
        direct = int(lookup["by_slug"].get(raw_slug, 0) or 0)
        if direct:
            return direct
        return int(lookup["by_slug_norm"].get(_normalize_slug_token(raw_slug), 0) or 0)

    def _find_term_id_by_name(self, taxonomy, name):
        raw_name = str(name or "").strip()
        if not raw_name:
            return 0
        lookup = self._get_taxonomy_lookup(taxonomy)
        target_norm = _normalize_topic(raw_name)
        if not target_norm:
            return 0
        target_plain = raw_name.strip().strip("'\"` ")
        best_id = 0
        best_name = ""
        best_score = -10**9
        for row in lookup.get("rows", []):
            term_id = int(row.get("id", 0) or 0)
            if not term_id:
                continue
            cand_name = str(row.get("name", "") or "").strip()
            if _normalize_topic(cand_name) != target_norm:
                continue
            cand_plain = cand_name.strip().strip("'\"` ")
            score = 0
            if cand_name == raw_name:
                score += 1000
            if cand_plain == raw_name:
                score += 900
            if cand_plain == target_plain:
                score += 700
            if cand_name and cand_name[0] in {"'", "\"", "`"}:
                score -= 250
            try:
                score += min(100, int(row.get("count", 0) or 0))
            except Exception:
                pass
            if score > best_score:
                best_score = score
                best_id = term_id
                best_name = cand_name

        if best_name and best_name[:1] in {"'", "\"", "`"} and raw_name[:1] not in {"'", "\"", "`"}:
            return 0
        if best_id:
            return int(best_id)
        return int(lookup["by_name_norm"].get(target_norm, 0) or 0)

    def _find_category_id_by_name_token(self, token_norm):
        token = str(token_norm or "").strip()
        if not token:
            return 0
        lookup = self._get_taxonomy_lookup("categories")
        for term_id, name in lookup["by_id_name"].items():
            if token in _normalize_topic(name):
                return int(term_id)
        return 0

    def _category_name_by_id(self, category_id):
        lookup = self._get_taxonomy_lookup("categories")
        return str(lookup["by_id_name"].get(int(category_id or 0), "") or "")

    @staticmethod
    def _has_any_token(source_norm, tokens):
        for token in tokens:
            if token and token in source_norm:
                return True
        return False

    def _ensure_tag_id(self, name):
        tag_name = str(name or "").strip()
        if not tag_name:
            return 0
        found = self._find_term_id_by_name("tags", tag_name)
        if found:
            return int(found)

        try:
            res = requests.post(
                f"{self.wp_url}/tags",
                headers=self.headers,
                json={"name": tag_name},
                timeout=15,
            )
        except requests.RequestException as e:
            logger.warning(f"tag create request failed ({tag_name}): {e}")
            return 0

        if res.status_code in (200, 201):
            try:
                created_id = int(res.json().get("id", 0) or 0)
            except Exception:
                created_id = 0
            if created_id:
                self._fetch_taxonomy_terms("tags", force=True)
                return created_id

        if res.status_code == 400:
            try:
                data = res.json()
            except Exception:
                data = {}
            if str(data.get("code", "")) == "term_exists":
                existing = int((data.get("data") or {}).get("term_id", 0) or 0)
                if existing:
                    self._fetch_taxonomy_terms("tags", force=True)
                    return existing

        logger.warning(f"tag create failed ({tag_name}): {res.status_code} {res.text[:180]}")
        return 0

    def _resolve_category_ids(self, keyword, content=None):
        source_text = self._build_taxonomy_source_text(keyword, content)
        text_norm = _normalize_topic(source_text)

        token = lambda value: _normalize_topic(value)
        listing_tokens = [token("\ub9e4\ubb3c"), token("\uc591\ub3c4\uac00"), token("\uc2e4\uc778\uc218"), token("\uae09\ub9e4")]
        mna_tokens = [
            token("\uc591\ub3c4\uc591\uc218"),
            token("\uc591\ub3c4"),
            token("\uc591\uc218"),
            token("\uc778\uc218"),
            token("\uc2e4\uc0ac"),
            token("\uacc4\uc57d\uc11c"),
            token("mna"),
            token("ma"),
        ]
        license_tokens = [
            token("\uba74\ud5c8"),
            token("\ub4f1\ub85d"),
            token("\ucd94\uac00\ub4f1\ub85d"),
            token("\uc2e0\uaddc\ub4f1\ub85d"),
            token("\ubc18\ub0a9"),
            token("\uc720\uc9c0"),
        ]
        requirement_tokens = [
            token("\ub4f1\ub85d\uae30\uc900"),
            token("\uc790\ubcf8\uae08"),
            token("\uae30\uc220\uc778\ub825"),
            token("\uc0ac\ubb34\uc2e4"),
            token("\uc7a5\ube44"),
            token("\uc2e4\ud0dc\uc870\uc0ac"),
            token("\ud589\uc815\ucc98\ubd84"),
            token("\uacf5\uc81c\uc870\ud569"),
            token("\uae30\uc5c5\uc9c4\ub2e8"),
            token("\uc2e0\uc6a9\ub4f1\uae09"),
            token("\uc7ac\ubb34\ube44\uc728"),
            token("\uc2dc\uacf5\ub2a5\ub825\ud3c9\uac00"),
        ]

        is_listing = self._has_any_token(text_norm, listing_tokens) and (token("\ub9e4\ubb3c") in text_norm)
        is_mna = self._has_any_token(text_norm, mna_tokens)
        is_license = self._has_any_token(text_norm, license_tokens)
        is_requirement = self._has_any_token(text_norm, requirement_tokens)

        cat_mna_listing = self._find_term_id_by_slug("categories", "mna-listings")
        cat_mna = self._find_term_id_by_slug("categories", "m-and-a")
        cat_license = self._find_term_id_by_slug("categories", "construction-license-guide")
        cat_requirements = self._find_term_id_by_slug("categories", "license-requirements")

        category_ids = []

        def add_cat(term_id):
            cid = int(term_id or 0)
            if cid and cid not in category_ids:
                category_ids.append(cid)

        if is_listing and cat_mna_listing:
            add_cat(cat_mna_listing)
        elif is_mna and cat_mna:
            add_cat(cat_mna)
        elif is_license and cat_license:
            add_cat(cat_license)
        else:
            add_cat(cat_license or cat_mna or cat_mna_listing)

        if is_requirement and (not is_listing):
            add_cat(cat_requirements)

        # Industry-focused subcategories
        industry_rules = [
            ([token("\ud1a0\ubaa9\uac74\ucd95\uacf5\uc0ac\uc5c5"), token("\ud1a0\uac74")], "civil-architecture", token("\ud1a0\ubaa9\uac74\ucd95\uacf5\uc0ac\uc5c5")),
            ([token("\ud1a0\ubaa9\uacf5\uc0ac\uc5c5"), token("\ud1a0\ubaa9")], "civil-engineering", token("\ud1a0\ubaa9\uacf5\uc0ac\uc5c5")),
            ([token("\uac74\ucd95\uacf5\uc0ac\uc5c5"), token("\uac74\ucd95")], "architecture", token("\uac74\ucd95\uacf5\uc0ac\uc5c5")),
            ([token("\uc885\ud569\uac74\uc124\uc5c5")], "general-construction", token("\uc885\ud569\uac74\uc124\uc5c5")),
            ([token("\uc804\ubb38\uac74\uc124\uc5c5")], "specialty-construction", token("\uc804\ubb38\uac74\uc124\uc5c5")),
            ([token("\uc2e4\ub0b4\uac74\ucd95")], "interior-construction", token("\uc2e4\ub0b4\uac74\ucd95\uacf5\uc0ac\uc5c5")),
            ([token("\uae08\uc18d"), token("\ucc3d\ud638"), token("\uc9c0\ubd95"), token("\uac74\ucd95\ubb3c\uc870\ub9bd")], "metal-window-door-roof-building-assembly", token("\uae08\uc18d\u318d\ucc3d\ud638\u318d\uc9c0\ubd95\u318d\uac74\ucd95\ubb3c\uc870\ub9bd\uacf5\uc0ac\uc5c5")),
            ([token("\ucc99\uadfc\ucf58\ud06c\ub9ac\ud2b8"), token("\ucca0\ucf58")], "rebar-concrete", token("\ucc99\uadfc\u318d\ucf58\ud06c\ub9ac\ud2b8\uacf5\uc0ac\uc5c5")),
            ([token("\ub3c4\uc7a5"), token("\uc2b5\uc2dd"), token("\ubc29\uc218"), token("\uc11d\uacf5")], "paint-waterproof", token("\ub3c4\uc7a5\u318d\uc2b5\uc2dd\u318d\ubc29\uc218\u318d\uc11d\uacf5\uc0ac\uc5c5")),
            ([token("\ube44\uacc4"), token("\ud574\uccb4")], "demolition-scaffolding", token("\uad6c\uc870\ubb3c\ud574\uccb4\u318d\ube44\uacc4\uacf5\uc0ac\uc5c5")),
            ([token("\ud3ec\uc7a5"), token("\uc9c0\ubc18\uc870\uc131")], "foundation-paving", token("\uc9c0\ubc18\uc870\uc131\u318d\ud3ec\uc7a5\uacf5\uc0ac\uc5c5")),
            ([token("\uae30\uacc4\uc124\ube44"), token("\uac00\uc2a4"), token("\uae30\uacc4\uac00\uc2a4")], "mechanical-gas", token("\uae30\uacc4\uac00\uc2a4\uc124\ube44\uacf5\uc0ac\uc5c5")),
            ([token("\uc0c1\ud558\uc218\ub3c4")], "water-sewerage", token("\uc0c1\ud558\uc218\ub3c4\uc124\ube44\uacf5\uc0ac\uc5c5")),
            ([token("\uc870\uacbd")], "landscaping", token("\uc870\uacbd\uacf5\uc0ac\uc5c5")),
            ([token("\uc804\uae30\uacf5\uc0ac\uc5c5"), token("\uc804\uae30\uacf5\uc0ac")], "", token("\uc804\uae30\uacf5\uc0ac\uc5c5")),
            ([token("\uc815\ubcf4\ud1b5\uc2e0\uacf5\uc0ac\uc5c5"), token("\uc815\ubcf4\ud1b5\uc2e0")], "", token("\uc815\ubcf4\ud1b5\uc2e0\uacf5\uc0ac\uc5c5")),
            ([token("\uc804\ubb38\uc18c\ubc29\uc2dc\uc124\uacf5\uc0ac\uc5c5"), token("\uc804\ubb38\uc18c\ubc29")], "", token("\uc804\ubb38\uc18c\ubc29\uc2dc\uc124\uacf5\uc0ac\uc5c5")),
            ([token("\uc77c\ubc18\uc18c\ubc29\uc2dc\uc124\uacf5\uc0ac\uc5c5"), token("\uc77c\ubc18\uc18c\ubc29")], "", token("\uc77c\ubc18\uc18c\ubc29\uc2dc\uc124\uacf5\uc0ac\uc5c5")),
        ]
        for tokens, slug, name_token in industry_rules:
            if not self._has_any_token(text_norm, tokens):
                continue
            term_id = self._find_term_id_by_slug("categories", slug) if slug else 0
            if not term_id:
                term_id = self._find_category_id_by_name_token(name_token)
            add_cat(term_id)
            if len(category_ids) >= 3:
                break

        return category_ids[:3]

    def _resolve_tag_names(self, keyword, content=None, category_ids=None):
        source_text = self._build_taxonomy_source_text(keyword, content)
        text_norm = _normalize_topic(source_text)
        token = lambda value: _normalize_topic(value)

        tags = []

        def add_tag(name):
            raw = str(name or "").strip()
            if not raw:
                return
            if raw not in tags:
                tags.append(raw)

        listing_tokens = [token("\ub9e4\ubb3c"), token("\uc591\ub3c4\uac00"), token("\uc2e4\uc778\uc218")]
        mna_tokens = [token("\uc591\ub3c4\uc591\uc218"), token("\uc591\ub3c4"), token("\uc591\uc218"), token("\uc778\uc218"), token("\uc2e4\uc0ac"), token("\uacc4\uc57d\uc11c")]
        license_tokens = [token("\uba74\ud5c8"), token("\ub4f1\ub85d"), token("\ub4f1\ub85d\uae30\uc900")]
        req_tokens = [token("\uc790\ubcf8\uae08"), token("\uae30\uc220\uc778\ub825"), token("\uc2dc\uacf5\ub2a5\ub825\ud3c9\uac00"), token("\uacf5\uc81c\uc870\ud569"), token("\uc2e4\ud0dc\uc870\uc0ac"), token("\ud589\uc815\ucc98\ubd84"), token("\uae30\uc5c5\uc9c4\ub2e8")]

        if self._has_any_token(text_norm, listing_tokens):
            add_tag("\uac74\uc124\uc5c5 \uc591\ub3c4\uc591\uc218 \ub9e4\ubb3c")
        if self._has_any_token(text_norm, mna_tokens):
            add_tag("\uac74\uc124\uc5c5 \uc591\ub3c4\uc591\uc218")
        if self._has_any_token(text_norm, license_tokens):
            add_tag("\uac74\uc124\uc5c5 \uba74\ud5c8")
        if self._has_any_token(text_norm, req_tokens):
            add_tag("\uac74\uc124\uc5c5 \ub4f1\ub85d\uae30\uc900")

        topic_tag_rules = [
            (token("\uc2e4\uc0ac"), "\uc2e4\uc0ac"),
            (token("\uacc4\uc57d\uc11c"), "\uacc4\uc57d\uc11c"),
            (token("\uc138\ubb34"), "\uc138\ubb34"),
            (token("\uccb4\ud06c\ub9ac\uc2a4\ud2b8"), "\uccb4\ud06c\ub9ac\uc2a4\ud2b8"),
            (token("\uc790\ubcf8\uae08"), "\uc790\ubcf8\uae08"),
            (token("\uae30\uc220\uc778\ub825"), "\uae30\uc220\uc778\ub825"),
            (token("\uc2dc\uacf5\ub2a5\ub825\ud3c9\uac00"), "\uc2dc\uacf5\ub2a5\ub825\ud3c9\uac00"),
            (token("\uacf5\uc81c\uc870\ud569"), "\uacf5\uc81c\uc870\ud569"),
            (token("\uae30\uc5c5\uc9c4\ub2e8"), "\uae30\uc5c5\uc9c4\ub2e8"),
            (token("\uc2e4\ud0dc\uc870\uc0ac"), "\uc2e4\ud0dc\uc870\uc0ac"),
            (token("\ud589\uc815\ucc98\ubd84"), "\ud589\uc815\ucc98\ubd84"),
        ]
        for marker, label in topic_tag_rules:
            if marker and marker in text_norm:
                add_tag(label)

        # Add selected category names as tags for more accurate archive filtering.
        for cid in category_ids or []:
            name = self._category_name_by_id(cid)
            if name:
                add_tag(name)

        # Stable brand tags to keep archive consistency.
        add_tag("\uc11c\uc6b8\uac74\uc124\uc815\ubcf4")
        add_tag("\uac15\uc9c0\ud604 \ud589\uc815\uc0ac")

        return tags[:10]

    def _resolve_tag_ids(self, tag_names):
        tag_ids = []
        for name in tag_names:
            tag_id = int(self._ensure_tag_id(name) or 0)
            if tag_id and tag_id not in tag_ids:
                tag_ids.append(tag_id)
            if len(tag_ids) >= 10:
                break
        return tag_ids

    def resolve_post_taxonomy(self, keyword, content=None):
        category_ids = self._resolve_category_ids(keyword, content=content)
        tag_names = self._resolve_tag_names(keyword, content=content, category_ids=category_ids)
        tag_ids = self._resolve_tag_ids(tag_names)
        return {
            "categories": category_ids,
            "tags": tag_ids,
            "tag_names": tag_names,
        }

    def _fetch_existing_index(self):
        if self._existing_index is not None:
            return self._existing_index

        titles = set()
        slugs = set()
        page = 1
        while True:
            res = requests.get(
                f"{self.wp_url}/posts",
                params={
                    "per_page": 100,
                    "page": page,
                    "status": "publish,draft,pending",
                    "_fields": "id,title,slug",
                },
                headers=self.auth_headers,
                timeout=10,
            )
            # Fallback when status parameter is rejected by server/account settings.
            if res.status_code == 400:
                res = requests.get(
                    f"{self.wp_url}/posts",
                    params={
                        "per_page": 100,
                        "page": page,
                        "status": "publish",
                        "_fields": "id,title,slug",
                    },
                    headers=self.auth_headers,
                    timeout=10,
                )
            if res.status_code != 200:
                break
            rows = res.json()
            if not rows:
                break
            for row in rows:
                titles.add(_normalize_topic(row.get("title", {}).get("rendered", "")))
                slugs.add(_normalize_slug_token(row.get("slug", "")))
            if page >= int(res.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1

        self._existing_index = {"titles": titles, "slugs": slugs}
        return self._existing_index

    def _post_exists(self, headline, slug):
        index = self._fetch_existing_index()
        h_norm = _normalize_topic(headline)
        s_norm = _normalize_slug_token(slug)
        if h_norm and h_norm in index["titles"]:
            return True
        if s_norm and s_norm in index["slugs"]:
            return True
        return False

    def _publish_preflight(
        self,
        keyword,
        content,
        rendered_html,
        seo_title,
        seo_desc,
        slug,
        expect_images=False,
        min_figure_count=1,
    ):
        slug_tokens = _slug_tokens(slug)
        checks = {
            "seo_title_len": 10 <= len(str(seo_title or "")) <= 60,
            "seo_desc_len": 90 <= len(str(seo_desc or "")) <= 160,
            "seo_desc_focus_keyword": _contains_focus_keyword(seo_desc, keyword),
            "slug_format": _is_valid_wp_slug(slug, min_tokens=2, max_tokens=12, min_len=8, max_len=140),
            "html_not_empty": len(str(rendered_html or "").strip()) >= 1200,
            "html_has_cta": ("open.kakao.com" in str(rendered_html)) or ("tel:" in str(rendered_html)),
            "html_schema": "\"FAQPage\"" in str(rendered_html) and "\"@type\": \"Article\"" in str(rendered_html),
            "no_raw_tokens": not bool(
                re.search(
                    r"\[\s*/?\s*(?:PARA|POINT|FAQ|LIST|NUM|EXTLINK)\s*\]",
                    str(rendered_html),
                    flags=re.IGNORECASE,
                )
            ),
        }
        failed_preflight = [name for name, ok in checks.items() if not ok]
        if failed_preflight:
            raise ValueError("Publish preflight failed: " + ", ".join(failed_preflight[:10]))

        auditor = PublicationQAAuditor()
        qa_report = auditor.audit(
            keyword,
            content,
            rendered_html=rendered_html,
            expect_images=bool(expect_images),
            min_figure_count=min_figure_count,
        )
        if not qa_report.get("pass_gate"):
            failures = auditor.summarize_failures(qa_report)
            raise ValueError("Publish preflight QA failed: " + ", ".join(failures[:12]))
        return qa_report

    @retry_request(max_retries=3, delay=2, exceptions=(requests.RequestException,))
    def publish(self, keyword, content, featured_media, inline_media=None, kakao_media=None, post_status=None):
        keyword = _normalize_focus_keyword(keyword)
        brand = CONFIG['BRAND_NAME']
        inline_media = inline_media or []
        effective_status = (
            str(post_status).strip().lower()
            if post_status is not None
            else str(CONFIG.get("WP_POST_STATUS", "publish")).strip().lower()
        ) or "publish"
        if effective_status not in {"publish", "draft", "pending", "private"}:
            effective_status = "publish"
        comment_status = str(CONFIG.get("WP_COMMENT_STATUS", "closed")).strip().lower() or "closed"
        if comment_status not in {"open", "closed"}:
            comment_status = "closed"
        ping_status = str(CONFIG.get("WP_PING_STATUS", "closed")).strip().lower() or "closed"
        if ping_status not in {"open", "closed"}:
            ping_status = "closed"
        
        seo_title = f"{content['headline']} | {brand}"
        if len(seo_title) > 60:
            seo_title = f"{content['headline'][:50]} | {brand}"
        
        seo_desc = _build_seo_description(keyword, content.get("summary", ""), min_len=110, max_len=160)
        content["summary"] = seo_desc
        slug_base = content.get("english_slug", "") or build_slug_from_keyword(keyword)
        slug = _compose_publish_slug(slug_base, keyword)

        if self._post_exists(content["headline"], slug):
            raise ValueError("Duplicate post detected: a similar topic already exists on seoulmna.kr.")
        
        meta = {
            "rank_math_focus_keyword": keyword,
            "rank_math_title": seo_title,
            "rank_math_description": seo_desc,
            "rank_math_twitter_title": seo_title,
            "rank_math_twitter_description": seo_desc,
            "rank_math_facebook_title": seo_title,
            "rank_math_facebook_description": seo_desc,
            "rank_math_robots": ["index", "follow", "max-snippet:-1", "max-image-preview:large", "max-video-preview:-1"],
        }

        content_blob = " ".join(
            [
                str(content.get("summary", "")),
                str(content.get("intro", "")),
                str(content.get("body1_text", "")),
                str(content.get("body2_text", "")),
                str(content.get("body3_text", "")),
                str(content.get("conclusion", "")),
            ]
        )
        content_encoding = _mojibake_metrics(content_blob)
        if content_encoding.get("flagged"):
            raise ValueError(
                "Encoding corruption detected before publish: "
                f"{content_encoding}"
            )

        rendered_html = self._render_post_html(
            keyword,
            content,
            featured_media=featured_media,
            inline_media=inline_media,
            kakao_media=kakao_media,
        )
        rendered_encoding = _mojibake_metrics(_strip_markup_tokens(rendered_html))
        if rendered_encoding.get("flagged"):
            raise ValueError(
                "Rendered HTML encoding corruption detected before publish: "
                f"{rendered_encoding}"
            )

        featured_media_id = featured_media["id"] if isinstance(featured_media, dict) else featured_media
        expected_image_count = (1 if featured_media_id else 0) + len(inline_media)
        self._publish_preflight(
            keyword=keyword,
            content=content,
            rendered_html=rendered_html,
            seo_title=seo_title,
            seo_desc=seo_desc,
            slug=slug,
            expect_images=bool(featured_media_id or inline_media),
            min_figure_count=expected_image_count if expected_image_count > 0 else 1,
        )
        gate_ok, gate_msg = _run_mnakr_prepublish_quality_gate(force=False, cache_sec=300)
        if not gate_ok:
            raise ValueError(f"Pre-publish contract gate failed: {gate_msg}")
        if gate_msg:
            logger.info(f"Pre-publish contract gate passed: {gate_msg}")
        taxonomy = self.resolve_post_taxonomy(keyword, content)
        payload = {
            "title": content["headline"],
            "content": rendered_html,
            "excerpt": seo_desc,
            "status": effective_status,
            "comment_status": comment_status,
            "ping_status": ping_status,
            "featured_media": featured_media_id,
            "meta": meta,
            "slug": slug,
            "categories": taxonomy.get("categories", []),
            "tags": taxonomy.get("tags", []),
        }
        logger.info(
            "publish taxonomy resolved: "
            f"categories={payload.get('categories', [])}, "
            f"tags={payload.get('tags', [])}, "
            f"tag_names={taxonomy.get('tag_names', [])}"
        )
        
        res = requests.post(f"{self.wp_url}/posts", headers=self.headers, json=payload, timeout=20)
        res.raise_for_status()
        try:
            post_data = res.json()
        except Exception as e:
            logger.warning(f"Rank Math post-process exception: {e}")
            return res

        post_id = int(post_data.get("id", 0) or 0)
        if post_id:
            rank_ok = self._update_rankmath_meta(
                post_id=post_id,
                keyword=keyword,
                seo_title=seo_title,
                seo_desc=seo_desc,
            )
            if (not rank_ok) and _cfg_bool("RANKMATH_RETEST_FAIL_DELETE_AND_QUEUE", True):
                optimizer = ContentPortfolioOptimizer()
                if optimizer.republish_mode == "deferred" and optimizer.republish_queue_enabled:
                    queue_item = {
                        "queued_at": datetime.now(timezone.utc).isoformat(),
                        "trashed_post_id": post_id,
                        "old_link": str(post_data.get("link", "")).strip(),
                        "old_title": str(post_data.get("title", {}).get("rendered", "") or content.get("headline", "")).strip(),
                        "keyword": str(keyword or "").strip(),
                        "reason": "rankmath_retest_failed",
                        "score": 0.0,
                        "age_days": 0,
                        "attempts": 0,
                        "last_error": "rankmath_retest_failed",
                    }
                    queue_state = {"queued": False, "duplicate": False, "queue_size": 0}
                    try:
                        trash_res = requests.delete(
                            f"{self.wp_url}/posts/{post_id}",
                            headers=self.auth_headers,
                            params={"force": "false"},
                            timeout=20,
                        )
                        _raise_for_status_with_context(
                            trash_res,
                            f"rankmath-failed-post trash failed(post_id={post_id})",
                        )
                        queue_state = optimizer._enqueue_republish_item(queue_item)
                    except Exception as qe:
                        logger.warning(
                            "Rank Math re-test rollback failed: "
                            f"post_id={post_id}, error={_safe_error_text(qe)}"
                        )
                    else:
                        logger.warning(
                            "Rank Math re-test failed; post moved to deferred queue: "
                            f"post_id={post_id}, queue_size={queue_state.get('queue_size', 0)}, "
                            f"duplicate={queue_state.get('duplicate', False)}"
                        )
                        raise ValueError(
                            f"Rank Math re-test failed; post {post_id} was deleted and queued for deferred republish."
                        )
                else:
                    logger.warning(
                        "Rank Math re-test failed but deferred queue is disabled. "
                        f"post_id={post_id} kept as-is."
                    )
            try:
                LifecycleOptimizer().register_post(post_data, keyword, content)
            except Exception as e:
                logger.warning(f"Lifecycle registration failed: {e}")
        return res


# =================================================================
# [GUI Application]
# =================================================================
class BlogGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{CONFIG['BRAND_NAME']} Blog Generator v3.0")
        self.root.geometry("800x700")
        self.root.configure(bg="#f5f6f8")

        self.is_running = False
        self.generated_content = None
        self.last_qa_report = None

        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f5f6f8")
        style.configure("Header.TLabel", background="#003764", foreground="#ffffff", font=("Malgun Gothic", 14, "bold"), padding=15)
        style.configure("TLabel", background="#f5f6f8", font=("Malgun Gothic", 10))
        style.configure("TButton", font=("Malgun Gothic", 10), padding=8)
        style.configure("Accent.TButton", background="#003764", foreground="#ffffff")
        style.configure("TProgressbar", thickness=20)

    def _create_widgets(self):
        header = ttk.Label(self.root, text=f"{CONFIG['BRAND_NAME']} blog auto publisher", style="Header.TLabel")
        header.pack(fill=tk.X)

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        kw_frame = ttk.LabelFrame(main_frame, text="Keyword", padding=15)
        kw_frame.pack(fill=tk.X, pady=(0, 15))

        btn_frame = ttk.Frame(kw_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_frame, text="Analyze priority keywords", command=self._fetch_keywords).pack(side=tk.LEFT)
        ttk.Label(btn_frame, text="  or manual input:").pack(side=tk.LEFT, padx=(10, 5))

        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(btn_frame, textvariable=self.keyword_var, width=40)
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.keyword_listbox = tk.Listbox(kw_frame, height=4, font=("Malgun Gothic", 10))
        self.keyword_listbox.pack(fill=tk.X, pady=(5, 0))
        self.keyword_listbox.bind('<<ListboxSelect>>', self._on_keyword_select)

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=15)

        self.generate_btn = ttk.Button(action_frame, text="Generate content", command=self._start_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.preview_btn = ttk.Button(action_frame, text="Preview", command=self._show_preview, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.publish_btn = ttk.Button(action_frame, text="Publish to WordPress", command=self._publish, state=tk.DISABLED)
        self.publish_btn.pack(side=tk.LEFT)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=15)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)

        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(pady=(5, 0))

        log_frame = ttk.LabelFrame(main_frame, text="Execution log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _update_progress(self, value, message):
        self.progress_var.set(value)
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def _run_quality_audit(self, keyword, content, expect_images=False, inline_image_count=2):
        inline_count = max(0, int(inline_image_count or 0)) if expect_images else 0
        try:
            preview_wp = WPEngine(verify_auth=False, allow_no_auth=True)
            featured_media = {"source_url": "https://example.com/cover.png"} if expect_images else None
            inline_media = _local_inline_media_placeholders(inline_count) if expect_images else None
            preview_html = preview_wp._render_post_html(
                keyword,
                content,
                featured_media=featured_media,
                inline_media=inline_media,
                include_related=False,
            )
        except Exception as e:
            logger.warning(f"QA preview html generation failed: {e}")
            preview_html = ""

        auditor = PublicationQAAuditor()
        report = auditor.audit(
            keyword,
            content,
            rendered_html=preview_html,
            expect_images=expect_images,
            min_figure_count=(1 + inline_count) if expect_images else 1,
        )
        try:
            os.makedirs("logs", exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join("logs", f"qa_report_{stamp}.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            report_path_display = str(report_path).replace("\\", "/")
            report["report_path"] = report_path_display
            logger.info(f"QA report saved: {report_path_display}")
        except Exception as e:
            logger.warning(f"QA report save failed: {e}")
        self.last_qa_report = report
        return report

    def _log_qa_report(self, report):
        if not report:
            self._log("No QA report")
            return
        self._log(
            f"QA score - overall {report['overall_score']} / SEO {report['seo']['score']} / "
            f"design {report['design']['score']} / content {report['content']['score']} / "
            f"legal {report['legal']['score']} / publish {report.get('publish_readiness', {}).get('score', 'N/A')}"
        )
        if report.get("pass_gate"):
            self._log("QA gate passed")
            return

        failures = PublicationQAAuditor().summarize_failures(report)
        if failures:
            self._log("QA failures: " + ", ".join(failures[:12]))

    def _fetch_keywords(self):
        self._log("Start priority keyword analysis from seoulmna.kr...")
        self.keyword_listbox.delete(0, tk.END)

        def fetch():
            radar = BusinessKeywordRadar()
            keywords = radar.get_top_keywords(10)
            self.root.after(0, lambda: self._populate_keywords(keywords))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_keywords(self, keywords):
        for kw in keywords:
            self.keyword_listbox.insert(tk.END, kw)
        self._log(f"Loaded {len(keywords)} priority keywords")

    def _on_keyword_select(self, event):
        selection = self.keyword_listbox.curselection()
        if selection:
            keyword = self.keyword_listbox.get(selection[0])
            self.keyword_var.set(keyword)

    def _start_generation(self):
        keyword = self.keyword_var.get().strip()

        radar = BusinessKeywordRadar()
        if not keyword:
            self._log("No keyword input. Auto-picking a priority keyword...")
            keyword = radar.mine_hot_keyword()
            if not keyword:
                messagebox.showwarning("No keyword", "No new priority keyword is available right now.")
                return
            self.keyword_var.set(keyword)
            self._log(f"Auto selected keyword: {keyword}")

        if not is_conversion_keyword(keyword):
            messagebox.showwarning("Warning", "Please input a conversion-intent construction keyword.")
            return

        if not radar.is_new_keyword(keyword):
            messagebox.showwarning("Duplicate topic", "A similar topic already exists on seoulmna.kr.")
            return

        self.is_running = True
        self.generate_btn.config(state=tk.DISABLED)
        self._log(f"Start content generation: {keyword}")

        def generate():
            try:
                self.root.after(0, lambda: self._update_progress(20, "Generating content with AI..."))

                writer = ColumnistEngine()
                content = writer.write(keyword)

                if content:
                    qa_report = self._run_quality_audit(keyword, content)
                    self.generated_content = {"keyword": keyword, "content": content, "qa": qa_report}
                    self.root.after(0, lambda: self._on_generation_complete(True))
                else:
                    self.root.after(0, lambda: self._on_generation_complete(False))

            except Exception as e:
                logger.exception("Content generation thread error")
                self.root.after(0, lambda: self._on_generation_error(_safe_error_text(e)))

        threading.Thread(target=generate, daemon=True).start()

    def _on_generation_complete(self, success):
        self.is_running = False
        self.generate_btn.config(state=tk.NORMAL)

        if success:
            self._update_progress(100, "Generation complete")
            self._log(f"Content generated: {self.generated_content['content'].get('headline', 'N/A')}")
            self._log_qa_report(self.generated_content.get("qa"))
            report_path = self.generated_content.get("qa", {}).get("report_path")
            if report_path:
                self._log(f"QA report: {report_path}")
            self.preview_btn.config(state=tk.NORMAL)
            qa_ok = bool(self.generated_content.get("qa", {}).get("pass_gate"))
            self.publish_btn.config(state=tk.NORMAL if qa_ok else tk.DISABLED)
            if not qa_ok:
                qa_report = self.generated_content.get("qa", {})
                failures = PublicationQAAuditor().summarize_failures(qa_report)
                report_path = qa_report.get("report_path", "")
                detail = ", ".join(failures[:8]) if failures else "check the execution log."
                if report_path:
                    detail += f"\nQA report: {report_path}"
                self._update_progress(92, "QA not passed - publish blocked")
                messagebox.showwarning(
                    "QA blocked",
                    "Publish was blocked by QA gate.\n"
                    f"Failures: {detail}\n"
                    "Review log and preview first.",
                )
        else:
            self._update_progress(0, "Generation failed")
            self._log("Content generation failed")

    def _on_generation_error(self, error):
        safe = _safe_error_text(error)
        self.is_running = False
        self.generate_btn.config(state=tk.NORMAL)
        self._update_progress(0, "Error")
        self._log(f"Error: {safe}")
        messagebox.showerror("Error", f"Error during content generation:\n{safe}")

    def _show_preview(self):
        if not self.generated_content:
            return

        content = self.generated_content['content']
        qa = self.generated_content.get("qa", {})
        preview_win = tk.Toplevel(self.root)
        preview_win.title("Content Preview")
        preview_win.geometry("700x600")

        text = scrolledtext.ScrolledText(preview_win, font=("Malgun Gothic", 11), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        preview_text = f"""Title: {content.get('headline', 'N/A')}
Slug: {content.get('english_slug', 'N/A')}

Summary:
{content.get('summary', 'N/A')}

Intro:
{content.get('intro', 'N/A')[:500]}...

Body1: {content.get('body1_title', 'N/A')}
{content.get('body1_text', 'N/A')[:300]}...

Body2: {content.get('body2_title', 'N/A')}
{content.get('body2_text', 'N/A')[:300]}...

Body3: {content.get('body3_title', 'N/A')}
{content.get('body3_text', 'N/A')[:300]}...

Conclusion:
{content.get('conclusion', 'N/A')}

QA:
overall {qa.get('overall_score', 'N/A')} / SEO {qa.get('seo', {}).get('score', 'N/A')}
design {qa.get('design', {}).get('score', 'N/A')} / content {qa.get('content', {}).get('score', 'N/A')}
legal {qa.get('legal', {}).get('score', 'N/A')} / publish {qa.get('publish_readiness', {}).get('score', 'N/A')} / gate {qa.get('pass_gate', False)}
"""
        text.insert(tk.END, preview_text)
        text.config(state=tk.DISABLED)

    def _publish(self):
        if not self.generated_content:
            return

        qa = self.generated_content.get("qa", {})
        if not qa.get("pass_gate"):
            failures = PublicationQAAuditor().summarize_failures(qa)
            messagebox.showwarning(
                "Publish blocked",
                "QA gate failed before publish.\n"
                + (", ".join(failures[:8]) if failures else "Please check logs."),
            )
            return

        post_status = str(CONFIG.get("WP_POST_STATUS", "publish")).strip().lower() or "publish"
        status_label = "publish now" if post_status == "publish" else f"status={post_status}"
        if not messagebox.askyesno("Confirm", f"Publish to WordPress ({status_label})?"):
            return

        gate_ok, gate_msg = _run_mnakr_prepublish_quality_gate(force=True, cache_sec=300)
        if not gate_ok:
            messagebox.showwarning(
                "Publish blocked",
                "Pre-publish contract gate failed.\n"
                f"{gate_msg}\n"
                "Run quality gate and fix issues before publish.",
            )
            self._log(f"Pre-publish contract gate failed: {gate_msg}")
            return

        self._log("Pre-publish contract gate passed")
        self._log("Start WordPress publish...")
        self._update_progress(60, "Generating images...")

        def publish():
            temp_paths = []
            try:
                keyword = self.generated_content['keyword']
                content = self.generated_content['content']

                image_plan = _inline_image_plan(content)
                inline_titles = list(image_plan.get("titles", []))
                inline_count = int(image_plan.get("count", 0) or 0)
                self._log(
                    f"Image plan: cover + {inline_count} inline "
                    f"(plain_chars={image_plan.get('plain_chars', 0)}, faq={image_plan.get('faq_count', 0)})"
                )

                final_qa = self._run_quality_audit(
                    keyword,
                    content,
                    expect_images=True,
                    inline_image_count=inline_count,
                )
                self.generated_content["qa"] = final_qa
                if not final_qa.get("pass_gate"):
                    failures = PublicationQAAuditor().summarize_failures(final_qa)
                    raise ValueError("Final QA failed before publish: " + ", ".join(failures[:10]))

                wp = WPEngine()
                visual = VisualEngine()
                cover_path = visual.generate_cover(keyword, content['headline'])
                temp_paths.append(cover_path)
                inline_paths = []
                for idx, section_title in enumerate(inline_titles, start=1):
                    p = visual.generate_inline(keyword, section_title, idx)
                    inline_paths.append(p)
                    temp_paths.append(p)

                self.root.after(0, lambda: self._update_progress(80, "Uploading to WordPress..."))

                featured_media = wp.upload_image(
                    cover_path,
                    alt_text=f"{keyword} 대표 썸네일 - {content.get('headline', '')}",
                    title=f"{keyword} 대표 이미지",
                )
                inline_media = []
                for idx, path in enumerate(inline_paths, start=1):
                    inline_media.append(
                        wp.upload_image(
                            path,
                            alt_text=f"{keyword} 본문 이미지 {idx} - {inline_titles[idx-1]}",
                            title=inline_titles[idx - 1],
                        )
                    )

                kakao_media = wp._resolve_kakao_cta_media()
                res = wp.publish(
                    keyword,
                    content,
                    featured_media,
                    inline_media=inline_media,
                    kakao_media=kakao_media,
                )

                for p in temp_paths:
                    if os.path.exists(p):
                        os.remove(p)

                if res and res.status_code in (200, 201):
                    post_data = res.json()
                    self.root.after(0, lambda: self._on_publish_complete(post_data))
                else:
                    self.root.after(0, lambda: self._on_publish_error("publish failed"))

            except Exception as e:
                logger.exception("Publish thread error")
                for p in temp_paths:
                    if os.path.exists(p):
                        os.remove(p)
                self.root.after(0, lambda: self._on_publish_error(e))

        threading.Thread(target=publish, daemon=True).start()

    def _on_publish_complete(self, post_data):
        self._update_progress(100, "Publish complete")
        url = post_data.get('link', 'N/A')
        self._log(f"Publish success: {url}")

        notifier = Notifier(CONFIG.get('DISCORD_WEBHOOK_URL'), CONFIG.get('SLACK_WEBHOOK_URL'))
        notifier.send(f"New post published\n{self.generated_content['content'].get('headline', 'N/A')}\n{url}")

        messagebox.showinfo("Success", f"Published to WordPress\n\n{url}")

        self.preview_btn.config(state=tk.DISABLED)
        self.publish_btn.config(state=tk.DISABLED)
        self.generated_content = None

    def _on_publish_error(self, error):
        safe = _safe_error_text(error)
        self._update_progress(0, "Publish failed")
        self._log(f"Publish error: {safe}")
        messagebox.showerror("Error", f"Error during publish:\n{safe}")


def run_lifecycle_maintenance():
    """Daily lifecycle maintenance for published posts."""
    if not _cfg_bool("LIFECYCLE_ENABLED", True):
        return
    try:
        lifecycle = LifecycleOptimizer()
        lifecycle.bootstrap_from_wordpress(max_posts=_cfg_int("LIFECYCLE_BOOTSTRAP_LIMIT", 40))
        lifecycle.process_due_tasks(limit=max(1, _cfg_int("LIFECYCLE_DAILY_LIMIT", 10)))
    except Exception as e:
        logger.warning(f"lifecycle maintenance error: {_safe_error_text(e)}")


def run_portfolio_cleanup():
    """Daily cleanup: rewrite or delete+republish low-performing posts."""
    if not _cfg_bool("PORTFOLIO_CLEANUP_ENABLED", True):
        return
    try:
        result = ContentPortfolioOptimizer().run_daily_cleanup()
        logger.info(
            "portfolio cleanup done: "
            f"reviewed={result.get('reviewed', 0)}, actions={result.get('actions', 0)}"
        )
    except Exception as e:
        logger.warning(f"portfolio cleanup error: {_safe_error_text(e)}")


def run_portfolio_republish_queue():
    """Process deferred republish queue within configured local time windows."""
    try:
        result = ContentPortfolioOptimizer().run_deferred_republish_queue()
        logger.info(
            "portfolio republish queue done: "
            f"queued={result.get('queued', 0)}, processed={result.get('processed', 0)}, "
            f"failed={result.get('failed', 0)}, skipped_window={result.get('skipped_window', False)}"
        )
    except Exception as e:
        logger.warning(f"portfolio republish queue error: {_safe_error_text(e)}")


def run_query_rewrite_loop():
    """Search query data 기반 저CTR 고노출 쿼리 리라이트 루프."""
    if not _cfg_bool("QUERY_REWRITE_ENABLED", True):
        return
    try:
        result = QueryCTRRewriteOptimizer().run_daily()
        logger.info(
            "🧩 query rewrite loop 완료: "
            f"queued={result.get('queued', 0)}, applied={result.get('applied', 0)}"
        )
    except Exception as e:
        logger.warning(f"query rewrite loop 오류: {e}")

def run_serp_snippet_audit(limit=None):
    """Audit published post SERP snippets and find mojibake-like corruption."""
    wp = WPEngine()
    max_scan = max(1, int(limit or _cfg_int("SERP_AUDIT_SCAN_LIMIT", 120)))

    posts = []
    page = 1
    while len(posts) < max_scan:
        res = requests.get(
            f"{wp.wp_url}/posts",
            headers=wp.auth_headers,
            params={
                "per_page": 100,
                "page": page,
                "status": "publish",
                "_fields": "id,slug,link,title,date",
            },
            timeout=15,
        )
        if res.status_code != 200:
            break
        rows = res.json()
        if not rows:
            break
        posts.extend(rows)
        if page >= int(res.headers.get("X-WP-TotalPages", 1)):
            break
        page += 1

    posts = posts[:max_scan]
    flagged = []

    for post in posts:
        post_id = int(post.get("id", 0) or 0)
        link = str(post.get("link", "")).strip()
        if not post_id or not link:
            continue

        try:
            page_res = requests.get(link, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if page_res.status_code != 200:
                continue
            title, description = _extract_head_snippet(page_res.text)
        except requests.RequestException:
            continue

        check = _is_serp_snippet_garbled(title, description)
        if not check.get("flagged"):
            continue

        flagged.append(
            {
                "post_id": post_id,
                "slug": str(post.get("slug", "")),
                "link": link,
                "head_title": title,
                "head_description": description,
                "marker_hit": bool(check.get("marker_hit")),
                "metrics": check.get("metrics", {}),
            }
        )

    report = {
        "timestamp": datetime.now().isoformat(),
        "checked": len(posts),
        "flagged_count": len(flagged),
        "flagged": flagged,
    }

    report_file = str(CONFIG.get("SERP_AUDIT_FILE", "serp_audit.json")).strip() or "serp_audit.json"
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"serp audit report write failed: {_safe_error_text(e)}")

    if flagged:
        logger.warning(f"SERP audit flagged {len(flagged)} / {len(posts)} posts")
        for row in flagged[:20]:
            logger.warning(f"SERP garbled: post_id={row['post_id']}, slug={row['slug']}")
    else:
        logger.info(f"SERP audit clean: checked={len(posts)}, flagged=0")

    return report


def _clone_replace_post_preserve_slug(post_id):
    """Clone a post, move original to trash, and promote clone to original slug."""
    wp = WPEngine()

    src_res = requests.get(
        f"{wp.wp_url}/posts/{int(post_id)}",
        headers=wp.auth_headers,
        params={"context": "edit"},
        timeout=20,
    )
    _raise_for_status_with_context(src_res, f"serp repair read failed(post_id={post_id})")
    src = src_res.json()

    old_slug = str(src.get("slug", "")).strip()
    if not old_slug:
        raise ValueError(f"serp repair failed: empty slug(post_id={post_id})")

    old_status = str(src.get("status", "publish")).strip().lower() or "publish"
    if old_status not in {"publish", "draft", "pending", "private"}:
        old_status = "publish"

    title_raw = str(src.get("title", {}).get("raw") or src.get("title", {}).get("rendered") or "")
    content_raw = str(src.get("content", {}).get("raw") or src.get("content", {}).get("rendered") or "")
    excerpt_raw = str(src.get("excerpt", {}).get("raw") or _strip_html_text(src.get("excerpt", {}).get("rendered", "")))

    temp_slug = f"{old_slug}-serpfix-{int(time.time())}"
    create_payload = {
        "title": title_raw,
        "content": content_raw,
        "excerpt": excerpt_raw,
        "slug": temp_slug,
        "status": "draft",
        "featured_media": int(src.get("featured_media", 0) or 0),
        "categories": src.get("categories", []),
        "tags": src.get("tags", []),
        "comment_status": str(src.get("comment_status", "open") or "open"),
        "ping_status": str(src.get("ping_status", "closed") or "closed"),
    }

    create_res = requests.post(
        f"{wp.wp_url}/posts",
        headers=wp.headers,
        json=create_payload,
        timeout=20,
    )
    _raise_for_status_with_context(create_res, f"serp repair clone create failed(post_id={post_id})")
    cloned = create_res.json()
    new_id = int(cloned.get("id", 0) or 0)
    if not new_id:
        raise ValueError(f"serp repair failed: clone id missing(post_id={post_id})")

    try:
        trash_res = requests.delete(
            f"{wp.wp_url}/posts/{int(post_id)}",
            headers=wp.auth_headers,
            params={"force": False},
            timeout=20,
        )
        _raise_for_status_with_context(trash_res, f"serp repair trash failed(post_id={post_id})")

        promote_res = requests.post(
            f"{wp.wp_url}/posts/{new_id}",
            headers=wp.headers,
            json={"slug": old_slug, "status": old_status},
            timeout=20,
        )
        _raise_for_status_with_context(promote_res, f"serp repair promote failed(new_id={new_id})")

        promoted = promote_res.json()
        return {
            "old_post_id": int(post_id),
            "new_post_id": new_id,
            "slug": old_slug,
            "status": old_status,
            "new_link": str(promoted.get("link", "")),
        }
    except Exception:
        # best-effort rollback: remove orphan clone if promote failed
        try:
            requests.delete(
                f"{wp.wp_url}/posts/{new_id}",
                headers=wp.auth_headers,
                params={"force": True},
                timeout=20,
            )
        except Exception:
            pass
        raise


def run_serp_snippet_repair(max_actions=None):
    """Repair garbled SERP snippets by clone+replace while preserving original slug URL."""
    limit = max(1, int(max_actions or _cfg_int("SERP_REPAIR_MAX_ACTIONS", 1)))
    before = run_serp_snippet_audit()
    targets = list(before.get("flagged", []))[:limit]

    actions = []
    for row in targets:
        post_id = int(row.get("post_id", 0) or 0)
        if not post_id:
            continue
        try:
            replaced = _clone_replace_post_preserve_slug(post_id)
            actions.append({"post_id": post_id, "status": "replaced", **replaced})
            logger.info(f"SERP repair replaced: old={post_id}, new={replaced.get('new_post_id')}")
        except Exception as e:
            actions.append({"post_id": post_id, "status": "failed", "error": _safe_error_text(e)})
            logger.warning(f"SERP repair failed(post_id={post_id}): {_safe_error_text(e)}")

    after = run_serp_snippet_audit()
    report = {
        "timestamp": datetime.now().isoformat(),
        "requested": len(targets),
        "actions": actions,
        "before_flagged_count": int(before.get("flagged_count", 0) or 0),
        "after_flagged_count": int(after.get("flagged_count", 0) or 0),
        "after_flagged": after.get("flagged", []),
    }

    log_file = str(CONFIG.get("SERP_REPAIR_LOG_FILE", "serp_repair_actions.json")).strip() or "serp_repair_actions.json"
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"SERP repair report write failed: {_safe_error_text(e)}")

    return report


def _pid_exists(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes  # type: ignore

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            try:
                out = subprocess.check_output(
                    ["tasklist", "/FI", f"PID eq {int(pid)}"],
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                )
                return str(pid) in out and "No tasks are running" not in out
            except Exception:
                return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _acquire_scheduler_lock():
    lock_file = str(CONFIG.get("SCHEDULER_LOCK_FILE", "mnakr_scheduler.lock")).strip() or "mnakr_scheduler.lock"
    current_pid = os.getpid()
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            old_pid = int(raw) if raw else 0
        except Exception:
            old_pid = 0
        if old_pid and old_pid != current_pid and _pid_exists(old_pid):
            raise ValueError(f"Scheduler already running (pid={old_pid}).")

    with open(lock_file, "w", encoding="utf-8") as f:
        f.write(str(current_pid))

    def _cleanup():
        try:
            if os.path.exists(lock_file):
                with open(lock_file, "r", encoding="utf-8") as f:
                    owner = f.read().strip()
                if str(current_pid) == owner:
                    os.remove(lock_file)
        except Exception:
            pass

    atexit.register(_cleanup)
    logger.info(f"scheduler lock acquired: {lock_file} (pid={current_pid})")


def _scheduler_state_file():
    return str(CONFIG.get("SCHEDULER_STATE_FILE", "scheduler_state.json")).strip() or "scheduler_state.json"


def _startup_once_state_file():
    return str(CONFIG.get("STARTUP_ONCE_STATE_FILE", "logs/startup_blog_once_state.json")).strip() or "logs/startup_blog_once_state.json"


def _load_startup_once_state():
    path = _startup_once_state_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_startup_once_state(state):
    path = _startup_once_state_file()
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state or {}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"startup-once state 저장 실패: {_safe_error_text(e)}")


def _load_scheduler_state():
    path = _scheduler_state_file()
    if not os.path.exists(path):
        return {"last_runs": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("last_runs", {}), dict):
            return data
    except Exception:
        pass
    return {"last_runs": {}}


def _save_scheduler_state(state):
    path = _scheduler_state_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"scheduler state 저장 실패: {e}")


def _mark_scheduler_job_run(job_key, success=True, error=""):
    state = _load_scheduler_state()
    state.setdefault("last_runs", {})
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "status": "success" if success else "failed",
    }
    if not success and error:
        entry["error"] = str(error)[:240]
    state["last_runs"][str(job_key)] = entry
    _save_scheduler_state(state)

def _job_ran_today(job_key, now_local=None):
    now_local = now_local or datetime.now().astimezone()
    state = _load_scheduler_state()
    entry = state.get("last_runs", {}).get(str(job_key), "")
    status = "success"
    raw = ""
    if isinstance(entry, dict):
        raw = str(entry.get("time", "")).strip()
        status = str(entry.get("status", "success")).strip().lower() or "success"
    else:
        raw = str(entry).strip()
    if not raw or status != "success":
        return False
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date() == now_local.date()

def _time_reached(now_local, hhmm):
    try:
        hour, minute = [int(x) for x in str(hhmm).split(":", 1)]
        target = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return now_local >= target
    except Exception:
        return False


def _in_startup_catchup_window(now_local):
    min_hour = max(0, min(23, _cfg_int("STARTUP_CATCHUP_MIN_LOCAL_HOUR", 9)))
    max_hour = max(0, min(23, _cfg_int("STARTUP_CATCHUP_MAX_LOCAL_HOUR", 22)))
    hour = int(now_local.hour)
    if min_hour <= max_hour:
        return min_hour <= hour <= max_hour
    # overnight window support, e.g. 22~06
    return hour >= min_hour or hour <= max_hour


_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _normalize_hhmm(raw, fallback="09:00"):
    text = str(raw or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if not m:
        return str(fallback)
    hour = int(m.group(1))
    minute = int(m.group(2))
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return str(fallback)


def _normalize_target_slots(raw_slots, fallback=None):
    fallback = fallback or [("daily", _normalize_hhmm(CONFIG.get("SCHEDULE_TIME", "09:00"), "09:00"))]
    out = []
    seen = set()
    for row in raw_slots or []:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        day = str(row[0] or "").strip().lower()
        hhmm = _normalize_hhmm(row[1], "09:00")
        if day != "daily" and day not in _WEEKDAYS:
            continue
        key = (day, hhmm)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out or list(fallback)


def _prev_weekday(day):
    day = str(day or "").strip().lower()
    if day == "daily":
        return "daily"
    if day not in _WEEKDAYS:
        return day
    idx = _WEEKDAYS.index(day)
    return _WEEKDAYS[(idx - 1) % len(_WEEKDAYS)]


def _resolve_publish_slots(target_slots):
    normalized_targets = _normalize_target_slots(target_slots)
    if not _cfg_bool("PUBLISH_PREV_DAY_ENABLED", True):
        return normalized_targets

    publish_time = _normalize_hhmm(str(CONFIG.get("PUBLISH_PREV_DAY_TIME", "21:00")).strip(), "21:00")
    out = []
    seen = set()
    for day, _hhmm in normalized_targets:
        key = (_prev_weekday(day), publish_time)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out or [("daily", publish_time)]


def _run_tracked_job(job_key, fn):
    try:
        result = fn()
        if result is False:
            raise ValueError("job returned False")
    except Exception as e:
        safe = _safe_error_text(e)
        _mark_scheduler_job_run(job_key, success=False, error=safe)
        is_expected_false = isinstance(e, ValueError) and str(e) == "job returned False"
        if is_expected_false:
            logger.warning(f"스케줄 작업 미완료: {job_key} ({safe})")
        elif str(job_key).startswith("unit:"):
            # Unit test scenarios intentionally trigger failures; keep logs concise.
            logger.error(f"스케줄 작업 실패: {job_key} ({safe})")
        else:
            logger.exception(f"스케줄 작업 실패: {job_key} ({safe})")
        return False
    _mark_scheduler_job_run(job_key, success=True)
    return True

def _run_startup_catchup(
    publish_slots,
    lifecycle_time,
    cleanup_time,
    query_rewrite_time=None,
    republish_queue_time=None,
):
    if not _cfg_bool("RUN_MISSED_ON_STARTUP", True):
        return

    now_local = datetime.now().astimezone()
    if not _in_startup_catchup_window(now_local):
        logger.info(
            "startup catch-up skipped: outside local window "
            f"(hour={now_local.hour}, min={_cfg_int('STARTUP_CATCHUP_MIN_LOCAL_HOUR', 9)}, "
            f"max={_cfg_int('STARTUP_CATCHUP_MAX_LOCAL_HOUR', 22)})"
        )
        return

    today_name = now_local.strftime("%A").lower()
    pending = []
    allow_maintenance = _cfg_bool("STARTUP_CATCHUP_ALLOW_MAINTENANCE", False)

    for day, hhmm, job_key in publish_slots:
        is_today_slot = (day == today_name) or (day == "daily")
        if is_today_slot and _time_reached(now_local, hhmm) and not _job_ran_today(job_key, now_local):
            pending.append((job_key, run_scheduled))

    if allow_maintenance and _time_reached(now_local, lifecycle_time) and not _job_ran_today("lifecycle_maint", now_local):
        pending.append(("lifecycle_maint", run_lifecycle_maintenance))

    if allow_maintenance and _time_reached(now_local, cleanup_time) and not _job_ran_today("portfolio_cleanup", now_local):
        pending.append(("portfolio_cleanup", run_portfolio_cleanup))

    if allow_maintenance and query_rewrite_time and _time_reached(now_local, query_rewrite_time) and not _job_ran_today("query_rewrite", now_local):
        pending.append(("query_rewrite", run_query_rewrite_loop))

    if (
        allow_maintenance
        and republish_queue_time
        and _time_reached(now_local, republish_queue_time)
        and not _job_ran_today("portfolio_republish_queue", now_local)
    ):
        pending.append(("portfolio_republish_queue", run_portfolio_republish_queue))

    max_jobs = max(0, _cfg_int("MAX_STARTUP_CATCHUP_JOBS", 2))
    if max_jobs <= 0:
        return

    for job_key, fn in pending[:max_jobs]:
        logger.info(f"startup catch-up run: {job_key}")
        _run_tracked_job(job_key, fn)


def run_scheduled():
    """Run one scheduled publish cycle."""
    ensure_config(["GEMINI_API_KEY", "WP_URL"], "mnakr:scheduled")
    _validate_wp_domain()
    if _is_genai_cooldown_active("scheduled publish cycle"):
        return False
    logger.info("scheduled run started")
    lifecycle = LifecycleOptimizer()
    try:
        lifecycle.bootstrap_from_wordpress(max_posts=_cfg_int("LIFECYCLE_BOOTSTRAP_LIMIT", 40))
        lifecycle.process_due_tasks(limit=4)
    except Exception as e:
        logger.warning(f"lifecycle follow-up error: {_safe_error_text(e)}")

    radar = BusinessKeywordRadar()
    retry_limit = max(1, _cfg_int("SCHEDULE_KEYWORD_RETRY_LIMIT", 3))
    try:
        keywords = radar.get_top_keywords(count=retry_limit, force_refresh=True)
    except TypeError:
        keywords = radar.get_top_keywords(count=retry_limit)

    if not keywords:
        logger.warning("no eligible keyword")
        return False

    writer = ColumnistEngine()
    attempt_failures = []
    total = len(keywords)

    for idx, keyword in enumerate(keywords, start=1):
        logger.info(f"selected keyword[{idx}/{total}]: {keyword}")
        try:
            content = writer.write(keyword)
        except Exception as e:
            safe = _safe_error_text(e)
            attempt_failures.append((keyword, f"write_failed:{safe}"))
            logger.warning(f"auto publish candidate skipped: write failed (keyword={keyword}, reason={safe})")
            if (not writer.local_fallback_enabled) and writer._should_use_local_fallback(e):
                if not isinstance(e, RetryBypassError):
                    _set_genai_rate_limit_cooldown(e, context="run_scheduled")
                logger.warning("Gemini quota/rate limit persists. Stop this cycle and retry at next schedule window.")
                break
            continue
        if not content:
            attempt_failures.append((keyword, "content_generation_empty"))
            continue

        temp_paths = []
        try:
            preview_wp = WPEngine(verify_auth=False, allow_no_auth=True)
            preview_html = preview_wp._render_post_html(
                keyword, content, featured_media=None, inline_media=None, include_related=False
            )
            qa_report = PublicationQAAuditor().audit(keyword, content, rendered_html=preview_html)
            if not qa_report.get("pass_gate"):
                failures = PublicationQAAuditor().summarize_failures(qa_report)
                logger.warning(
                    "auto publish candidate blocked: QA gate failed "
                    f"(keyword={keyword}, overall={qa_report.get('overall_score')}, failures={failures[:10]})"
                )
                attempt_failures.append((keyword, "qa_gate_failed"))
                continue

            wp = WPEngine()
            candidate_title = str(content.get("headline", "")).strip()
            candidate_slug = _compose_publish_slug(
                content.get("english_slug", "") or build_slug_from_keyword(keyword),
                keyword,
            )
            if wp._post_exists(candidate_title, candidate_slug):
                logger.info(
                    "auto publish candidate skipped: duplicate topic detected early "
                    f"(keyword={keyword}, title={candidate_title[:60]}, slug={candidate_slug})"
                )
                attempt_failures.append((keyword, "duplicate_early"))
                continue

            visual = VisualEngine()
            cover_path = visual.generate_cover(keyword, content['headline'])
            temp_paths.append(cover_path)
            image_plan = _inline_image_plan(content)
            inline_titles = list(image_plan.get("titles", []))
            logger.info(
                "auto publish image plan: "
                f"inline={len(inline_titles)}, plain_chars={image_plan.get('plain_chars', 0)}, faq={image_plan.get('faq_count', 0)}"
            )
            inline_paths = []
            for img_idx, title in enumerate(inline_titles):
                p = visual.generate_inline(keyword, title, img_idx + 1)
                inline_paths.append(p)
                temp_paths.append(p)

            final_preview_html = preview_wp._render_post_html(
                keyword,
                content,
                featured_media={"source_url": "https://example.com/cover.png"},
                inline_media=_local_inline_media_placeholders(len(inline_titles)),
                include_related=False,
            )
            final_qa = PublicationQAAuditor().audit(
                keyword,
                content,
                rendered_html=final_preview_html,
                expect_images=True,
                min_figure_count=1 + len(inline_titles),
            )
            if not final_qa.get("pass_gate"):
                failures = PublicationQAAuditor().summarize_failures(final_qa)
                logger.warning(
                    "auto publish candidate blocked: final QA failed "
                    f"(keyword={keyword}, overall={final_qa.get('overall_score')}, failures={failures[:10]})"
                )
                attempt_failures.append((keyword, "final_qa_failed"))
                continue

            gate_ok, gate_msg = _run_mnakr_prepublish_quality_gate(force=True, cache_sec=300)
            if not gate_ok:
                logger.warning(
                    f"auto publish candidate blocked: pre-publish contract gate failed (keyword={keyword}, reason={gate_msg})"
                )
                attempt_failures.append((keyword, "contract_gate_failed"))
                continue
            logger.info(f"auto publish pre-publish contract gate passed: {gate_msg}")

            featured_media = wp.upload_image(
                cover_path,
                alt_text=f"{keyword} 대표 썸네일 - {content.get('headline', '')}",
                title=f"{keyword} 대표 이미지",
            )
            inline_media = [
                wp.upload_image(
                    path,
                    alt_text=f"{keyword} 본문 이미지 {media_idx + 1} - {inline_titles[media_idx]}",
                    title=inline_titles[media_idx],
                )
                for media_idx, path in enumerate(inline_paths)
            ]
            kakao_media = wp._resolve_kakao_cta_media()
            try:
                res = wp.publish(
                    keyword,
                    content,
                    featured_media,
                    inline_media=inline_media,
                    kakao_media=kakao_media,
                )
            except ValueError as e:
                if "Duplicate post detected" in str(e):
                    logger.info(
                        "auto publish candidate skipped: duplicate topic detected at publish gate "
                        f"(keyword={keyword})"
                    )
                    attempt_failures.append((keyword, "duplicate_publish_gate"))
                    continue
                raise

            if res and res.status_code in (200, 201):
                post_data = res.json()
                logger.info(f"auto publish success: {post_data.get('link', 'N/A')}")

                notifier = Notifier(CONFIG.get('DISCORD_WEBHOOK_URL'), CONFIG.get('SLACK_WEBHOOK_URL'))
                notifier.send(f"[AUTO] new post published!\n{content.get('headline', 'N/A')}\n{post_data.get('link', '')}")
                return True

            logger.error(f"auto publish candidate failed: unexpected status (keyword={keyword})")
            attempt_failures.append((keyword, f"publish_status_{getattr(res, 'status_code', 'unknown')}"))
        except Exception as e:
            safe = _safe_error_text(e)
            logger.exception(f"auto publish candidate error ({keyword}): {safe}")
            attempt_failures.append((keyword, safe))
        finally:
            for p in temp_paths:
                if os.path.exists(p):
                    os.remove(p)

    summary = ", ".join([f"{kw}:{reason}" for kw, reason in attempt_failures[:5]])
    logger.warning(f"auto publish failed for all candidates ({len(attempt_failures)}/{total}): {summary}")
    return False


def run_taxonomy_sync(limit=None, include_tagged=False, dry_run=False):
    """
    Backfill categories/tags for recent posts.
    - default: only posts with empty tags are targeted
    - include_tagged=True: retag all scanned posts
    """
    ensure_config(["WP_URL"], "mnakr:taxonomy-sync")
    wp = WPEngine()
    max_scan = max(1, int(limit or _cfg_int("TAXONOMY_SYNC_LIMIT", 60)))

    scanned_rows = []
    page = 1
    while len(scanned_rows) < max_scan:
        res = requests.get(
            f"{wp.wp_url}/posts",
            headers=wp.auth_headers,
            params={
                "per_page": 100,
                "page": page,
                "status": "publish",
                "context": "edit",
                "_fields": "id,slug,title,excerpt,categories,tags",
            },
            timeout=20,
        )
        if res.status_code != 200:
            logger.warning(f"taxonomy sync read failed: status={res.status_code}, body={res.text[:180]}")
            break
        rows = res.json()
        if not rows:
            break
        scanned_rows.extend(rows)
        if page >= int(res.headers.get("X-WP-TotalPages", 1)):
            break
        page += 1

    scanned_rows = scanned_rows[:max_scan]
    report = {
        "scanned": len(scanned_rows),
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "dry_run": bool(dry_run),
        "include_tagged": bool(include_tagged),
        "items": [],
    }

    for row in scanned_rows:
        post_id = int(row.get("id", 0) or 0)
        if not post_id:
            report["skipped"] += 1
            continue

        existing_categories = [int(x) for x in row.get("categories", []) if str(x).isdigit()]
        existing_tags = [int(x) for x in row.get("tags", []) if str(x).isdigit()]
        if (not include_tagged) and existing_tags:
            report["skipped"] += 1
            continue

        title_obj = row.get("title", {})
        title = ""
        if isinstance(title_obj, dict):
            title = str(title_obj.get("raw") or title_obj.get("rendered") or "")
        else:
            title = str(title_obj or "")
        title = _strip_html_text(title)
        excerpt_obj = row.get("excerpt", {})
        excerpt = ""
        if isinstance(excerpt_obj, dict):
            excerpt = str(excerpt_obj.get("raw") or excerpt_obj.get("rendered") or "")
        else:
            excerpt = str(excerpt_obj or "")
        excerpt = _strip_html_text(excerpt)

        content_hint = {"headline": title, "summary": excerpt}
        taxonomy = wp.resolve_post_taxonomy(title, content=content_hint)
        new_categories = [int(x) for x in taxonomy.get("categories", []) if int(x or 0) > 0]
        new_tags = [int(x) for x in taxonomy.get("tags", []) if int(x or 0) > 0]

        same_categories = sorted(existing_categories) == sorted(new_categories)
        same_tags = sorted(existing_tags) == sorted(new_tags)
        if same_categories and same_tags:
            report["skipped"] += 1
            continue

        item_log = {
            "post_id": post_id,
            "slug": str(row.get("slug", "")),
            "old_categories": existing_categories,
            "new_categories": new_categories,
            "old_tags_count": len(existing_tags),
            "new_tags_count": len(new_tags),
            "tag_names": taxonomy.get("tag_names", []),
        }

        if dry_run:
            report["updated"] += 1
            report["items"].append({**item_log, "mode": "dry_run"})
            continue

        payload = {}
        if new_categories:
            payload["categories"] = new_categories
        payload["tags"] = new_tags
        try:
            ures = requests.post(
                f"{wp.wp_url}/posts/{post_id}",
                headers=wp.headers,
                json=payload,
                timeout=20,
            )
            _raise_for_status_with_context(ures, f"taxonomy sync update failed(post_id={post_id})")
            report["updated"] += 1
            report["items"].append(item_log)
        except Exception as e:
            report["failed"] += 1
            report["items"].append({**item_log, "error": _safe_error_text(e)})

    logger.info(
        "taxonomy sync done: "
        f"scanned={report['scanned']}, updated={report['updated']}, "
        f"skipped={report['skipped']}, failed={report['failed']}, dry_run={report['dry_run']}"
    )
    for item in report["items"][:20]:
        logger.info(
            "taxonomy sync item: "
            f"post_id={item.get('post_id')} slug={item.get('slug')} "
            f"cats={item.get('old_categories')}->{item.get('new_categories')} "
            f"tags={item.get('old_tags_count')}->{item.get('new_tags_count')}"
        )
    return report


def run_startup_once():
    """
    Execute blog publish flow at startup/login once per local day.
    Retry is allowed on failure up to STARTUP_ONCE_MAX_ATTEMPTS_PER_DAY.
    A day is consumed when one attempt succeeds.
    """
    ensure_config(["GEMINI_API_KEY", "WP_URL"], "mnakr:startup-once")
    _validate_wp_domain()
    now_local = datetime.now().astimezone()
    today_key = now_local.date().isoformat()
    state = _load_startup_once_state()
    if str(state.get("last_success_date", "")).strip() == today_key:
        logger.info(f"startup-once skipped: already succeeded today ({today_key})")
        return True
    if _is_genai_cooldown_active("startup-once publish"):
        logger.warning("startup-once deferred: Gemini cooldown active (attempt count unchanged)")
        return False

    if str(state.get("last_attempt_date", "")).strip() != today_key:
        state["attempt_count_today"] = 0

    attempt_count = max(0, _cfg_int("STARTUP_ONCE_MAX_ATTEMPTS_PER_DAY", 3))
    current_attempts = max(0, int(state.get("attempt_count_today", 0) or 0))
    if attempt_count > 0 and current_attempts >= attempt_count:
        logger.info(
            f"startup-once skipped: daily attempt limit reached ({today_key}, {current_attempts}/{attempt_count})"
        )
        return True

    state["last_attempt_date"] = today_key
    state["attempt_count_today"] = current_attempts + 1
    state["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
    _save_startup_once_state(state)

    ok = _run_tracked_job("startup_once_publish", run_scheduled)
    cooldown_remain, _cooldown_until = _get_genai_cooldown_remaining_sec()
    deferred_cooldown = (not ok) and (cooldown_remain > 0)
    if deferred_cooldown:
        # 429/cooldown failures should not consume today's attempt budget.
        state["attempt_count_today"] = current_attempts
        logger.warning(
            "startup-once failed under Gemini cooldown; restored daily attempt count "
            f"({today_key}, {current_attempts}/{attempt_count})"
        )
    state["last_result"] = "deferred_cooldown" if deferred_cooldown else ("success" if ok else "failed")
    state["last_result_at"] = datetime.now(timezone.utc).isoformat()
    if ok:
        state["last_success_date"] = today_key
    _save_startup_once_state(state)
    return ok


def start_scheduler():
    """Start scheduler (background)."""
    try:
        import schedule
    except ImportError:
        logger.warning("schedule package missing - pip install schedule")
        return
    _acquire_scheduler_lock()
    publish_slots = []
    
    def configure_jobs():
        nonlocal publish_slots
        schedule.clear("auto_publish")
        publish_slots = []
        auto_enabled = _cfg_bool("AUTO_SCHEDULE_ENABLED", True)
        if auto_enabled:
            target_slots = AIScheduleOptimizer().recommend_slots()
            if not target_slots:
                target_slots = [("tuesday", "08:30")]
        else:
            schedule_time = _normalize_hhmm(str(CONFIG.get("SCHEDULE_TIME", "09:00")).strip(), "09:00")
            target_slots = [("daily", schedule_time)]

        normalized_targets = _normalize_target_slots(target_slots)
        resolved_publish_slots = _resolve_publish_slots(normalized_targets)

        for day, hhmm in resolved_publish_slots:
            try:
                job_key = f"auto_publish:{day}:{hhmm}"
                publish_slots.append((day, hhmm, job_key))
                if day == "daily":
                    schedule.every().day.at(hhmm).do(_run_tracked_job, job_key, run_scheduled).tag("auto_publish")
                else:
                    job = getattr(schedule.every(), day)
                    job.at(hhmm).do(_run_tracked_job, job_key, run_scheduled).tag("auto_publish")
            except Exception as e:
                logger.warning(f"schedule slot register failed ({day} {hhmm}): {_safe_error_text(e)}")

        if _cfg_bool("PUBLISH_PREV_DAY_ENABLED", True):
            logger.info("target slots: " + ", ".join([f"{d} {t}" for d, t in normalized_targets]))
            logger.info("publish slots (prev-day fixed): " + ", ".join([f"{d} {t}" for d, t in resolved_publish_slots]))
        elif auto_enabled:
            logger.info("AI schedule applied: " + ", ".join([f"{d} {t}" for d, t in normalized_targets]))
        else:
            logger.info("fixed schedule applied: " + ", ".join([f"{d} {t}" for d, t in resolved_publish_slots]))

    configure_jobs()
    recalc_time = str(CONFIG.get("AUTO_SCHEDULE_RECALC_TIME", "00:10")).strip() or "00:10"
    schedule.clear("auto_recalc")
    schedule.every().day.at(recalc_time).do(_run_tracked_job, "auto_recalc", configure_jobs).tag("auto_recalc")
    logger.info(f"schedule recalculation time: daily {recalc_time}")
    lifecycle_time = str(CONFIG.get("LIFECYCLE_DAILY_TIME", "00:20")).strip() or "00:20"
    schedule.clear("lifecycle_maint")
    schedule.every().day.at(lifecycle_time).do(_run_tracked_job, "lifecycle_maint", run_lifecycle_maintenance).tag("lifecycle_maint")
    logger.info(f"lifecycle maintenance time: daily {lifecycle_time}")
    cleanup_time = str(CONFIG.get("PORTFOLIO_CLEANUP_TIME", "00:35")).strip() or "00:35"
    schedule.clear("portfolio_cleanup")
    schedule.every().day.at(cleanup_time).do(_run_tracked_job, "portfolio_cleanup", run_portfolio_cleanup).tag("portfolio_cleanup")
    logger.info(f"portfolio cleanup time: daily {cleanup_time}")
    republish_queue_time = str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_TIME", "22:10")).strip() or "22:10"
    schedule.clear("portfolio_republish_queue")
    schedule.every().day.at(republish_queue_time).do(
        _run_tracked_job,
        "portfolio_republish_queue",
        run_portfolio_republish_queue,
    ).tag("portfolio_republish_queue")
    logger.info(f"portfolio republish queue time: daily {republish_queue_time}")
    query_rewrite_time = str(CONFIG.get("QUERY_REWRITE_TIME", "00:45")).strip() or "00:45"
    schedule.clear("query_rewrite")
    schedule.every().day.at(query_rewrite_time).do(_run_tracked_job, "query_rewrite", run_query_rewrite_loop).tag("query_rewrite")
    logger.info(f"query rewrite loop time: daily {query_rewrite_time}")
    serp_audit_time = str(CONFIG.get("SERP_AUDIT_TIME", "01:10")).strip() or "01:10"
    schedule.clear("serp_audit")
    schedule.every().day.at(serp_audit_time).do(_run_tracked_job, "serp_audit", run_serp_snippet_audit).tag("serp_audit")
    logger.info(f"SERP audit time: daily {serp_audit_time}")
    _run_startup_catchup(
        publish_slots,
        lifecycle_time,
        cleanup_time,
        query_rewrite_time,
        republish_queue_time,
    )
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.exception(f"스케줄러 루프 오류: {_safe_error_text(e)}")
            time.sleep(5)

def show_scheduler_plan():
    auto_enabled = _cfg_bool("AUTO_SCHEDULE_ENABLED", True)
    if auto_enabled:
        target_slots = AIScheduleOptimizer().recommend_slots()
        if not target_slots:
            target_slots = [("tuesday", "08:30")]
        print("AUTO_SCHEDULE_ENABLED=true")
        print("wp_post_status=" + (str(CONFIG.get("WP_POST_STATUS", "publish")).strip() or "publish"))
        normalized_targets = _normalize_target_slots(target_slots)
        resolved_publish_slots = _resolve_publish_slots(normalized_targets)
        print("target_slots=" + ", ".join([f"{d} {t}" for d, t in normalized_targets]))
        print("planned_slots=" + ", ".join([f"{d} {t}" for d, t in resolved_publish_slots]))
        print("publish_prev_day_enabled=" + str(_cfg_bool("PUBLISH_PREV_DAY_ENABLED", True)).lower())
        print("publish_prev_day_time=" + _normalize_hhmm(str(CONFIG.get("PUBLISH_PREV_DAY_TIME", "21:00")).strip(), "21:00"))
        print("lifecycle_daily_time=" + (str(CONFIG.get("LIFECYCLE_DAILY_TIME", "00:20")).strip() or "00:20"))
        print("portfolio_cleanup_time=" + (str(CONFIG.get("PORTFOLIO_CLEANUP_TIME", "00:35")).strip() or "00:35"))
        print("portfolio_republish_mode=" + (str(CONFIG.get("PORTFOLIO_DELETE_REPUBLISH_MODE", "deferred")).strip() or "deferred"))
        print("portfolio_republish_queue_time=" + (str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_TIME", "22:10")).strip() or "22:10"))
        print("query_rewrite_time=" + (str(CONFIG.get("QUERY_REWRITE_TIME", "00:45")).strip() or "00:45"))
        print("serp_audit_time=" + (str(CONFIG.get("SERP_AUDIT_TIME", "01:10")).strip() or "01:10"))
        cooldown_remain, cooldown_until = _get_genai_cooldown_remaining_sec()
        print(f"genai_cooldown_remaining_sec={cooldown_remain}")
        if cooldown_remain > 0 and cooldown_until is not None:
            print("genai_cooldown_until=" + cooldown_until.astimezone().isoformat(timespec="seconds"))
        print("run_mode=continuous(--scheduler)")
        print("run_conditions=computer_on,terminal_open,no_sleep,internet_on,wp_auth_valid")
        return
    schedule_time = _normalize_hhmm(str(CONFIG.get("SCHEDULE_TIME", "09:00")).strip(), "09:00")
    target_slots = [("daily", schedule_time)]
    resolved_publish_slots = _resolve_publish_slots(target_slots)
    print("AUTO_SCHEDULE_ENABLED=false")
    print("wp_post_status=" + (str(CONFIG.get("WP_POST_STATUS", "publish")).strip() or "publish"))
    print(f"target_slot=daily {schedule_time}")
    print("planned_slots=" + ", ".join([f"{d} {t}" for d, t in resolved_publish_slots]))
    print("publish_prev_day_enabled=" + str(_cfg_bool("PUBLISH_PREV_DAY_ENABLED", True)).lower())
    print("publish_prev_day_time=" + _normalize_hhmm(str(CONFIG.get("PUBLISH_PREV_DAY_TIME", "21:00")).strip(), "21:00"))
    print("lifecycle_daily_time=" + (str(CONFIG.get("LIFECYCLE_DAILY_TIME", "00:20")).strip() or "00:20"))
    print("portfolio_cleanup_time=" + (str(CONFIG.get("PORTFOLIO_CLEANUP_TIME", "00:35")).strip() or "00:35"))
    print("portfolio_republish_mode=" + (str(CONFIG.get("PORTFOLIO_DELETE_REPUBLISH_MODE", "deferred")).strip() or "deferred"))
    print("portfolio_republish_queue_time=" + (str(CONFIG.get("PORTFOLIO_REPUBLISH_QUEUE_TIME", "22:10")).strip() or "22:10"))
    print("query_rewrite_time=" + (str(CONFIG.get("QUERY_REWRITE_TIME", "00:45")).strip() or "00:45"))
    print("serp_audit_time=" + (str(CONFIG.get("SERP_AUDIT_TIME", "01:10")).strip() or "01:10"))
    cooldown_remain, cooldown_until = _get_genai_cooldown_remaining_sec()
    print(f"genai_cooldown_remaining_sec={cooldown_remain}")
    if cooldown_remain > 0 and cooldown_until is not None:
        print("genai_cooldown_until=" + cooldown_until.astimezone().isoformat(timespec="seconds"))
    print("run_mode=continuous(--scheduler)")
    print("run_conditions=computer_on,terminal_open,no_sleep,internet_on,wp_auth_valid")


def _cli_arg_int(flag, default):
    try:
        idx = sys.argv.index(flag)
    except ValueError:
        return int(default)
    if idx + 1 >= len(sys.argv):
        return int(default)
    try:
        return int(str(sys.argv[idx + 1]).strip())
    except Exception:
        return int(default)


# =================================================================
# [Main]
# =================================================================
if __name__ == "__main__":
    try:
        # WordPress authentication check mode
        if "--wp-check" in sys.argv:
            ensure_config(["WP_URL"], "mnakr:wp-check")
            _validate_wp_domain()
            WPEngine()
            print("WordPress auth check passed.")
        # schedule-check mode
        elif "--schedule-check" in sys.argv:
            show_scheduler_plan()
        # scheduler mode
        elif "--scheduler" in sys.argv:
            ensure_config(["GEMINI_API_KEY", "WP_URL"], "mnakr:scheduler")
            _validate_wp_domain()
            start_scheduler()
        # SERP snippet audit mode
        elif "--serp-audit" in sys.argv:
            ensure_config(["WP_URL"], "mnakr:serp-audit")
            _validate_wp_domain()
            report = run_serp_snippet_audit()
            print(json.dumps({"checked": report.get("checked", 0), "flagged_count": report.get("flagged_count", 0)}, ensure_ascii=False))
        # SERP snippet repair mode
        elif "--serp-repair" in sys.argv:
            ensure_config(["WP_URL"], "mnakr:serp-repair")
            _validate_wp_domain()
            report = run_serp_snippet_repair()
            print(json.dumps({"requested": report.get("requested", 0), "before_flagged_count": report.get("before_flagged_count", 0), "after_flagged_count": report.get("after_flagged_count", 0)}, ensure_ascii=False))
        # portfolio deferred republish queue mode
        elif "--portfolio-republish-queue" in sys.argv:
            ensure_config(["GEMINI_API_KEY", "WP_URL"], "mnakr:portfolio-republish-queue")
            _validate_wp_domain()
            run_portfolio_republish_queue()
        # taxonomy sync mode (backfill categories/tags)
        elif "--taxonomy-sync" in sys.argv:
            ensure_config(["WP_URL"], "mnakr:taxonomy-sync")
            _validate_wp_domain()
            limit = _cli_arg_int("--taxonomy-limit", _cfg_int("TAXONOMY_SYNC_LIMIT", 60))
            include_tagged = "--taxonomy-include-tagged" in sys.argv
            dry_run = ("--taxonomy-dry-run" in sys.argv) or ("--dry-run" in sys.argv)
            report = run_taxonomy_sync(limit=limit, include_tagged=include_tagged, dry_run=dry_run)
            print(
                json.dumps(
                    {
                        "scanned": report.get("scanned", 0),
                        "updated": report.get("updated", 0),
                        "skipped": report.get("skipped", 0),
                        "failed": report.get("failed", 0),
                        "dry_run": report.get("dry_run", False),
                    },
                    ensure_ascii=False,
                )
            )
        # CLI mode
        elif "--cli" in sys.argv:
            ok = run_scheduled()
            sys.exit(0 if ok else 2)
        # startup once mode (at-logon, one attempt per day)
        elif "--startup-once" in sys.argv:
            ok = run_startup_once()
            sys.exit(0 if ok else 2)
        # GUI mode (default)
        else:
            ensure_config(["GEMINI_API_KEY", "WP_URL"], "mnakr:gui")
            _validate_wp_domain()
            root = tk.Tk()
            app = BlogGeneratorApp(root)
            root.mainloop()
    except ValueError as e:
        message = str(e)
        logger.error(message)
        cli_modes = {
            "--scheduler",
            "--cli",
            "--startup-once",
            "--wp-check",
            "--schedule-check",
            "--serp-audit",
            "--serp-repair",
            "--portfolio-republish-queue",
            "--taxonomy-sync",
        }
        if not any(flag in sys.argv for flag in cli_modes):
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Configuration Error", message)
            root.destroy()
        else:
            print(message)
        sys.exit(1)









