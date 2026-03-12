# =================================================================
# [유틸리티 모듈] 재시도, 로깅, 알림 기능
# =================================================================

from __future__ import annotations

__all__ = [
    "setup_logger",
    "retry_request",
    "Notifier",
    "load_config",
    "require_config",
    "ProgressCallback",
]

import logging
import os
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import wraps
from typing import Any

import requests


# =================================================================
# [로깅 설정]
# =================================================================
def setup_logger(name: str = "mnakr", log_dir: str = "logs") -> logging.Logger:
    """Create logger with daily file rollover and deduplicated handlers."""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
    log_file_abs = os.path.abspath(log_file)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    has_console = False
    has_today_file = False

    for handler in list(logger.handlers):
        is_file = isinstance(handler, logging.FileHandler)
        is_console = isinstance(handler, logging.StreamHandler) and not is_file

        if is_file:
            current = os.path.abspath(getattr(handler, "baseFilename", ""))
            if current == log_file_abs:
                has_today_file = True
                handler.setLevel(logging.DEBUG)
                handler.setFormatter(formatter)
            else:
                logger.removeHandler(handler)
                try:
                    handler.close()
                except OSError:
                    pass
        elif is_console:
            has_console = True
            handler.setLevel(logging.INFO)
            handler.setFormatter(formatter)

    if not has_today_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not has_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

def retry_request(max_retries: int = 3, delay: int = 2, backoff: int = 2, exceptions: tuple[type, ...] = (Exception,)) -> Callable:
    """
    API 호출 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 대기 시간 증가 배수
        exceptions: 재시도할 예외 타입들
    """
    def decorator(func: Callable) -> Callable:  # noqa: D401
        """Inner decorator that wraps *func* with retry logic."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("mnakr")
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:  # type: ignore[misc]
                    if getattr(e, "no_retry", False):
                        logger.warning(f"[재시도 중단] {func.__name__}: {type(e).__name__}")
                        raise
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"[재시도 {attempt + 1}/{max_retries}] {func.__name__} 실패: {type(e).__name__}")
                        logger.info(f"   {wait_time}초 후 재시도...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"[실패] {func.__name__} - 최대 재시도 횟수 초과: {type(e).__name__}")

            raise last_exception  # type: ignore[misc]
        return wrapper
    return decorator


# =================================================================
# [알림 기능]
# =================================================================
class Notifier:
    """Discord/Slack notification sender with retry and payload safety."""

    MAX_MESSAGE_LEN = 1800
    MAX_RETRIES = 2
    RETRY_DELAY = 1.2

    def __init__(self, discord_url: str | None = None, slack_url: str | None = None) -> None:
        """Create a notifier with optional Discord / Slack webhook URLs."""
        self.discord_url = discord_url
        self.slack_url = slack_url
        self.logger = logging.getLogger("mnakr")

    def _compact_message(self, message: object) -> str:
        """Truncate *message* to ``MAX_MESSAGE_LEN`` characters if needed."""
        text = str(message or "").strip()
        if len(text) <= self.MAX_MESSAGE_LEN:
            return text
        return text[: self.MAX_MESSAGE_LEN - 32].rstrip() + " ... (truncated)"

    def _post_with_retry(self, url: str, payload: dict, ok_statuses: set, channel: str) -> bool:
        """POST *payload* to *url*, retrying up to ``MAX_RETRIES`` on failure."""
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code in ok_statuses:
                    return True
                last_error = f"status={res.status_code}"
            except (requests.RequestException, OSError) as e:
                last_error = f"{type(e).__name__}"

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY * (attempt + 1))

        self.logger.warning(f"{channel} notification failed: {last_error}")
        return False

    def send(self, message: str, title: str = "블로그 생성기 알림") -> bool:
        """Send notifications to configured channels."""
        compact = self._compact_message(message)
        results = []

        if self.discord_url:
            results.append(("Discord", self._send_discord(compact, title)))

        if self.slack_url:
            results.append(("Slack", self._send_slack(compact, title)))

        if not results:
            self.logger.debug("notification skipped: no webhook configured")
            return False

        return all(ok for _name, ok in results)

    def _send_discord(self, message: str, title: str) -> bool:
        """Send an embed message to the configured Discord webhook."""
        payload = {
            "embeds": [
                {
                    "title": str(title or "알림")[:240],
                    "description": message,
                    "color": 3066993,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            ]
        }
        if self.discord_url is None:
            return False
        ok = self._post_with_retry(self.discord_url, payload, {200, 204}, "Discord")
        if ok:
            self.logger.info("Discord notification sent")
        return ok

    def _send_slack(self, message: str, title: str) -> bool:
        """Send a formatted text block to the configured Slack webhook."""
        payload = {
            "text": f"*{str(title or '알림')[:120]}*\n{message}"
        }
        if self.slack_url is None:
            return False
        ok = self._post_with_retry(self.slack_url, payload, {200}, "Slack")
        if ok:
            self.logger.info("Slack notification sent")
        return ok

def _parse_bool(value: object, default: bool = False) -> bool:
    """Coerce *value* (string/int/None) to ``bool``; return *default* on ambiguity."""
    if value is None:
        return default
    v = str(value).strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off"}:
        return False
    return default


def _load_env_file(env_path: str) -> dict[str, str]:
    """Parse a simple ``KEY=VALUE`` env file, ignoring comments and empty lines."""
    loaded: dict[str, str] = {}
    if not os.path.exists(env_path):
        return loaded

    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            loaded[key] = value.strip().strip('"').strip("'")
    return loaded


def load_config(extra_defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load settings from .env + OS environment."""
    defaults = {
        "GEMINI_API_KEY": "",
        "WP_URL": "",
        "WP_USER": "",
        "WP_PASSWORD": "",
        "WP_APP_PASSWORD": "",
        "WP_JWT_TOKEN": "",
        "WP_AUTH_MODE": "auto",
        "MAIN_SITE": "",
        "GUIDE_LINK": "",
        "BRAND_NAME": "서울건설정보",
        "CONSULTANT_NAME": "",
        "CONSULTANT": "",
        "PHONE": "",
        "SITE_URL": "",
        "ADMIN_ID": "",
        "ADMIN_PW": "",
        "JSON_FILE": "service_account.json",
        "SHEET_NAME": "",
        "TAB_CONSULT": "",
        "TAB_ITEM": "",
        "DISCORD_WEBHOOK_URL": "",
        "SLACK_WEBHOOK_URL": "",
        "SCHEDULE_ENABLED": False,
        "SCHEDULE_TIME": "09:00",
    }
    if extra_defaults:
        defaults.update(extra_defaults)

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    file_values = _load_env_file(env_path)

    config = dict(defaults)
    for key in defaults:
        env_val = os.getenv(key)
        if env_val is not None and env_val != "":
            config[key] = env_val
            continue
        if key in file_values and file_values[key] != "":
            config[key] = file_values[key]

    # aliases / derived defaults
    if not config.get("SITE_URL") and config.get("MAIN_SITE"):
        config["SITE_URL"] = config["MAIN_SITE"]
    if not config.get("CONSULTANT") and config.get("CONSULTANT_NAME"):
        config["CONSULTANT"] = config["CONSULTANT_NAME"]
    if not config.get("CONSULTANT_NAME") and config.get("CONSULTANT"):
        config["CONSULTANT_NAME"] = config["CONSULTANT"]

    config["SCHEDULE_ENABLED"] = _parse_bool(config.get("SCHEDULE_ENABLED"), default=False)
    config["SCHEDULE_TIME"] = str(config.get("SCHEDULE_TIME") or "09:00").strip() or "09:00"
    return config


def require_config(config: dict[str, Any], required_keys: Sequence[str], context: str = "app") -> dict[str, Any]:
    """Raise ValueError if required keys are missing/empty."""
    missing = [k for k in required_keys if not str(config.get(k, "")).strip()]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"[{context}] Missing required config keys: {joined}. Set them in .env")
    return config


# =================================================================
# [진행률 콜백]
# =================================================================
class ProgressCallback:
    """GUI 진행률 업데이트용 콜백 클래스"""

    def __init__(self, callback_func: Callable | None = None) -> None:
        """Initialise with an optional GUI callback (receives ``(progress, message)``)."""
        self.callback = callback_func
        self.current_step = 0
        self.total_steps = 5
        self.steps = [
            "키워드 발굴 중...",
            "AI 콘텐츠 생성 중...",
            "썸네일 생성 중...",
            "WordPress 업로드 중...",
            "완료!"
        ]

    def update(self, step: int | None = None, message: str | None = None) -> tuple[float, str]:
        """진행 상태 업데이트"""
        if step is not None:
            self.current_step = step

        msg = message or self.steps[min(self.current_step, len(self.steps)-1)]
        progress = (self.current_step / self.total_steps) * 100

        if self.callback:
            self.callback(progress, msg)

        return progress, msg

