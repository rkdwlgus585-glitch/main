from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gabji
from selenium import webdriver
from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchWindowException,
    TimeoutException,
    UnexpectedAlertPresentException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from tistory_ops.listing_template import (
    build_auto_image_urls,
    build_listing_content,
    build_listing_title,
    evaluate_cx_quality,
    evaluate_legal_quality,
    evaluate_seo_quality,
)
from utils import load_config

CONFIG = load_config(
    {
        "TISTORY_BLOG_DOMAIN": "seoulmna.tistory.com",
        "TISTORY_SOURCE_URL_TEMPLATE": "http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1",
        "TISTORY_LOGIN_URL": "https://www.tistory.com/auth/login",
        "TISTORY_LOGIN_ID": "",
        "TISTORY_LOGIN_PASSWORD": "",
        "TISTORY_AUTO_LOGIN": "0",
        "TISTORY_CHROME_DEBUGGER": "",
        "TISTORY_CHROME_USER_DATA_DIR": "",
        "TISTORY_CHROME_PROFILE_DIR": "Default",
        "TISTORY_PAGE_TIMEOUT_SEC": "30",
        "TISTORY_PUBLISH_DELAY_SEC": "0.6",
        "TISTORY_PUBLISH_STATE_FILE": "logs/tistory_publish_state.json",
        "TISTORY_PUBLISH_AUDIT_DIR": "logs/tistory_publish_audit",
        "TISTORY_ALLOWED_BLOG_DOMAINS": "seoulmna.tistory.com",
        "TISTORY_AUTO_IMAGES": "1",
        "TISTORY_IMAGE_COUNT": "2",
        "TISTORY_SEO_MIN_SCORE": "90",
        "TISTORY_LEGAL_MIN_SCORE": "85",
        "TISTORY_CX_MIN_SCORE": "85",
    }
)


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _to_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return int(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return bool(default)
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _default_chrome_user_data_dir() -> str:
    import os

    localapp = os.environ.get("LOCALAPPDATA", str(Path.home()))
    return str(Path(localapp) / "Google" / "Chrome" / "User Data CodexTistory")


def _extract_registration_no(data: dict[str, Any], explicit: str = "") -> str:
    if str(explicit or "").strip():
        return str(explicit).strip()
    candidates = [
        data.get("등록번호"),
        data.get("registration_no"),
        data.get("registration"),
        data.get("?깅줉踰덊샇"),
        data.get("uid"),
    ]
    for val in candidates:
        text = str(val or "").strip()
        if text:
            return text
    return ""


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    return obj if isinstance(obj, dict) else {}


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"published": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"published": {}}
    if not isinstance(payload, dict):
        return {"published": {}}
    pub = payload.get("published")
    if not isinstance(pub, dict):
        payload["published"] = {}
    return payload


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _content_digest(title: str, content: str, source_url: str) -> str:
    parts = [str(title or "").strip(), str(source_url or "").strip(), str(content or "").strip()]
    joined = "\n".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _content_signature(content: str) -> str:
    text = str(content or "").lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _wrap_preview_html_document(content: str, title: str) -> str:
    safe_title = str(title or "Tistory Preview").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!doctype html>\n"
        "<html lang='ko'>\n"
        "<head>\n"
        "  <meta charset='utf-8' />\n"
        "  <meta name='viewport' content='width=device-width, initial-scale=1' />\n"
        f"  <title>{safe_title}</title>\n"
        "  <style>body{margin:0;padding:20px;background:#0b1320;}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{content}\n"
        "</body>\n"
        "</html>\n"
    )


def _parse_allowed_domains(override_domains: list[str] | None = None) -> set[str]:
    allowed: set[str] = set()
    raw = str(CONFIG.get("TISTORY_ALLOWED_BLOG_DOMAINS", "")).strip()
    if raw:
        for token in raw.split(","):
            dom = str(token or "").strip().lower()
            if dom:
                allowed.add(dom)
    for token in (override_domains or []):
        dom = str(token or "").strip().lower()
        if dom:
            allowed.add(dom)
    return allowed


def _validate_blog_domain(blog_domain: str, override_domains: list[str] | None = None) -> str:
    normalized = str(blog_domain or "").strip().lower()
    if not normalized:
        raise ValueError("blog domain is empty")
    if "/" in normalized:
        raise ValueError("blog domain must be host only (e.g. seoulmna.tistory.com)")
    allowed = _parse_allowed_domains(override_domains)
    if allowed and normalized not in allowed:
        allow_text = ", ".join(sorted(allowed))
        raise ValueError(f"blog domain safety gate blocked: {normalized} (allowed: {allow_text})")
    return normalized


def _duplicate_decision(
    state: dict[str, Any],
    registration_no: str,
    content_digest: str,
    content_signature: str,
    republish_changed: bool = True,
) -> tuple[str, dict[str, Any] | None]:
    reg = str(registration_no or "").strip()
    if not reg:
        return "allow_no_registration", None
    published = state.get("published")
    if not isinstance(published, dict):
        return "allow_new", None
    for reg_key, info in published.items():
        if not isinstance(info, dict):
            continue
        if str(reg_key) == reg:
            continue
        if str(info.get("content_signature") or "").strip() == str(content_signature or "").strip():
            return "skip_duplicate_signature", info
    entry = published.get(reg)
    if not isinstance(entry, dict):
        return "allow_new", None
    prev_digest = str(entry.get("content_digest") or "").strip()
    if prev_digest and prev_digest != str(content_digest or "").strip():
        if republish_changed:
            return "allow_changed", entry
        return "skip_changed", entry
    return "skip_duplicate", entry


def _mark_published(
    state: dict[str, Any],
    registration_no: str,
    title: str,
    blog_domain: str,
    source_url: str,
    content_digest: str,
    content_signature: str,
) -> dict[str, Any]:
    published = state.setdefault("published", {})
    prev = published.get(str(registration_no))
    publish_count = 1
    if isinstance(prev, dict):
        try:
            publish_count = int(prev.get("publish_count", 1)) + 1
        except Exception:
            publish_count = 2
    published[str(registration_no)] = {
        "title": str(title or "").strip(),
        "blog_domain": str(blog_domain or "").strip(),
        "source_url": str(source_url or "").strip(),
        "content_digest": str(content_digest or "").strip(),
        "content_signature": str(content_signature or "").strip(),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "publish_count": publish_count,
    }
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state


def _resolve_source_url(data: dict[str, Any], override_source: str = "") -> str:
    if str(override_source or "").strip():
        return str(override_source).strip()
    reg = _extract_registration_no(data)
    uid = _digits(reg)
    if not uid:
        return ""
    template = str(CONFIG.get("TISTORY_SOURCE_URL_TEMPLATE", "")).strip()
    if "{uid}" not in template:
        template = "http://www.nowmna.com/yangdo_view1.php?uid={uid}&page_no=1"
    return template.format(uid=uid)


def _load_listing_data(args: argparse.Namespace) -> dict[str, Any]:
    if args.registration:
        lookup = gabji.ListingSheetLookup()
        return lookup.load_listing(args.registration)
    if args.image:
        generator = gabji.GabjiGenerator()
        return generator.analyze_image(args.image)
    if args.json_input:
        return _load_json(args.json_input)
    raise ValueError("one of --registration, --image, --json-input is required")


def build_post_package(
    data: dict[str, Any],
    title_override: str = "",
    source_url: str = "",
    image_urls: list[str] | None = None,
    auto_images: bool = True,
    image_count: int = 2,
) -> dict[str, str]:
    title = str(title_override or "").strip() or build_listing_title(data)
    src_url = _resolve_source_url(data, source_url)
    effective_images = [str(x).strip() for x in (image_urls or []) if str(x).strip()]
    if (not effective_images) and auto_images:
        effective_images = build_auto_image_urls(data, max_images=max(0, int(image_count)))
    content = build_listing_content(data, source_url=src_url, image_urls=effective_images)
    return {"title": title, "content": content, "source_url": src_url}


def _write_audit(
    audit_dir: Path,
    status: str,
    registration_no: str,
    payload_preview: dict[str, Any],
    error: str = "",
    tag: str = "",
    extra: dict[str, Any] | None = None,
) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_reg = _digits(registration_no) or "unknown"
    safe_tag = re.sub(r"[^0-9a-zA-Z_-]+", "", str(tag or "").strip())[:30]
    name = f"tistory_publish_{safe_reg}_{stamp}"
    if safe_tag:
        name += f"_{safe_tag}"
    out = audit_dir / f"{name}.json"
    payload = {
        "status": status,
        "registration_no": registration_no,
        "preview": payload_preview,
        "error": str(error or ""),
        "tag": str(tag or ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "extra": extra or {},
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


class TistoryBrowserPublisher:
    def __init__(
        self,
        blog_domain: str,
        debugger: str = "",
        user_data_dir: str = "",
        profile_dir: str = "",
        timeout_sec: int = 30,
        draft_policy: str = "discard",
    ):
        self.blog_domain = str(blog_domain).strip()
        self.debugger = str(debugger or "").strip()
        self.user_data_dir = str(user_data_dir or "").strip()
        self.profile_dir = str(profile_dir or "").strip()
        self.timeout_sec = int(timeout_sec)
        self.draft_policy = str(draft_policy or "discard").strip().lower()
        self.driver: webdriver.Chrome | None = None

    def __enter__(self):
        self.driver = self._create_driver()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.driver and not self.debugger:
            self.driver.quit()
        self.driver = None

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.debugger:
            options.add_experimental_option("debuggerAddress", self.debugger)
            return webdriver.Chrome(options=options)
        if self.user_data_dir:
            options.add_argument(f"--user-data-dir={self.user_data_dir}")
        if self.profile_dir:
            options.add_argument(f"--profile-directory={self.profile_dir}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _wait(self, sec: int | None = None):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        return WebDriverWait(self.driver, sec or self.timeout_sec)

    def open_editor(self):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        url = f"https://{self.blog_domain}/manage/newpost/"
        self.driver.get(url)
        self._wait().until(lambda d: d.execute_script("return document.readyState") == "complete")
        self.resolve_draft_alert()

    def resolve_draft_alert(self) -> bool:
        if not self.driver:
            return False
        try:
            alert = self.driver.switch_to.alert
            text = str(alert.text or "").strip()
        except (NoAlertPresentException, Exception):
            return False

        policy = self.draft_policy if self.draft_policy in {"discard", "resume"} else "discard"
        try:
            if policy == "resume":
                alert.accept()
                print(f"[info] draft alert handled: resume ({text[:80]})")
            else:
                alert.dismiss()
                print(f"[info] draft alert handled: discard ({text[:80]})")
        except Exception:
            try:
                alert.accept()
                print(f"[warn] draft alert fallback to accept ({text[:80]})")
            except Exception:
                return False
        time.sleep(0.3)
        return True

    def _set_input_value(self, selectors: list[tuple[str, str]], value: str) -> bool:
        if not self.driver:
            return False
        text = str(value or "")
        el = self._find_first(selectors)
        if not el:
            return False
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", el)
        except Exception:
            try:
                el.click()
            except Exception:
                pass
        try:
            el.clear()
        except Exception:
            pass
        try:
            el.send_keys(Keys.CONTROL, "a")
            el.send_keys(Keys.DELETE)
            el.send_keys(text)
            return True
        except Exception:
            pass
        try:
            return bool(
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    const val = String(arguments[1] || "");
                    if (!el) return false;
                    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
                      el.value = val;
                      el.dispatchEvent(new Event("input", { bubbles: true }));
                      el.dispatchEvent(new Event("change", { bubbles: true }));
                      return true;
                    }
                    return false;
                    """,
                    el,
                    text,
                )
            )
        except Exception:
            return False

    def try_auto_login(self, login_id: str, login_password: str, login_url: str = "", login_wait_sec: int = 30) -> bool:
        if not self.driver:
            return False
        uid = str(login_id or "").strip()
        pwd = str(login_password or "").strip()
        if not uid or not pwd:
            return False

        if "/manage/" in str(self.driver.current_url or ""):
            return True

        url = str(login_url or "").strip() or "https://www.tistory.com/auth/login"
        manage_url = f"https://{self.blog_domain}/manage/newpost/"
        try:
            self.driver.get(url)
            self._wait().until(lambda d: d.execute_script("return document.readyState") == "complete")
        except Exception:
            return False

        id_selectors = [
            (By.CSS_SELECTOR, "input[name='loginId']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[id*='login']"),
            (By.CSS_SELECTOR, "input[id*='email']"),
        ]
        pw_selectors = [
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]

        # Tistory login often starts with a Kakao gateway button before ID/PW fields.
        ready_deadline = time.time() + min(40, max(8, int(login_wait_sec)))
        clicked_gateway = False
        clicked_simple_login = False
        while time.time() < ready_deadline:
            id_el = self._find_first(id_selectors)
            pw_el = self._find_first(pw_selectors)
            if id_el and pw_el:
                break
            if not clicked_simple_login:
                try:
                    profiles = self.driver.find_elements(By.CSS_SELECTOR, "a.wrap_profile")
                except Exception:
                    profiles = []
                if profiles:
                    target = None
                    uid_lower = uid.lower()
                    for row in profiles:
                        text = str(row.text or "").strip().lower()
                        if uid_lower and uid_lower in text:
                            target = row
                            break
                    if target is None:
                        for row in profiles:
                            text = str(row.text or "").strip().lower()
                            if "@" in text:
                                target = row
                                break
                    if target is None:
                        target = profiles[0]
                    clicked = False
                    try:
                        target.click()
                        clicked = True
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", target)
                            clicked = True
                        except Exception:
                            pass
                    if clicked:
                        clicked_simple_login = True
            if not clicked_gateway:
                gateway = self._find_first(
                    [
                        (By.CSS_SELECTOR, "a.btn_login.link_kakao_id"),
                        (By.CSS_SELECTOR, "a[href*='accounts.kakao.com/login']"),
                        (By.CSS_SELECTOR, "button.btn_login"),
                    ]
                )
                if gateway:
                    clicked = False
                    try:
                        gateway.click()
                        clicked = True
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", gateway)
                            clicked = True
                        except Exception:
                            pass
                    if clicked:
                        clicked_gateway = True
            time.sleep(0.6)

        try:
            handles = list(self.driver.window_handles or [])
            if handles:
                self.driver.switch_to.window(handles[-1])
        except Exception:
            pass

        id_ok = self._set_input_value(id_selectors, uid)
        pw_ok = self._set_input_value(pw_selectors, pwd)
        if not (id_ok and pw_ok):
            try:
                self.driver.get(manage_url)
                self._wait().until(lambda d: d.execute_script("return document.readyState") == "complete")
                self.resolve_draft_alert()
                if "/manage/" in str(self.driver.current_url or ""):
                    return True
            except UnexpectedAlertPresentException:
                self.resolve_draft_alert()
                try:
                    if "/manage/" in str(self.driver.current_url or ""):
                        return True
                except Exception:
                    pass
            except Exception:
                pass
            return False

        submit = self._find_first(
            [
                (By.CSS_SELECTOR, "button.btn_g.highlight.submit"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
            ]
        )
        if submit:
            submit_clicked = False
            try:
                submit.click()
                submit_clicked = True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", submit)
                    submit_clicked = True
                except Exception:
                    pass
            if not submit_clicked:
                try:
                    pw_el = self._find_first(pw_selectors)
                    if pw_el:
                        pw_el.send_keys(Keys.ENTER)
                except Exception:
                    pass
        else:
            try:
                pw_el = self._find_first(pw_selectors)
                if pw_el:
                    pw_el.send_keys(Keys.ENTER)
            except Exception:
                pass

        end_ts = time.time() + max(5, int(login_wait_sec))
        while time.time() < end_ts:
            try:
                cur = str(self.driver.current_url or "")
            except UnexpectedAlertPresentException:
                self.resolve_draft_alert()
                try:
                    cur = str(self.driver.current_url or "")
                except Exception:
                    cur = ""
            except Exception:
                cur = ""
            if "/manage/" in cur:
                return True
            time.sleep(1.5)

        try:
            self.driver.get(manage_url)
            self._wait().until(lambda d: d.execute_script("return document.readyState") == "complete")
            self.resolve_draft_alert()
            if "/manage/" in str(self.driver.current_url or ""):
                return True
        except UnexpectedAlertPresentException:
            self.resolve_draft_alert()
            try:
                if "/manage/" in str(self.driver.current_url or ""):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def wait_for_login(
        self,
        interactive: bool,
        login_wait_sec: int = 180,
        auto_login: bool = False,
        login_id: str = "",
        login_password: str = "",
        login_url: str = "",
    ):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        if "/manage/" in (self.driver.current_url or ""):
            return

        if auto_login:
            if self.try_auto_login(login_id=login_id, login_password=login_password, login_url=login_url, login_wait_sec=min(90, max(10, int(login_wait_sec)))):
                print("[info] auto-login success")
                return
            if interactive:
                print("[warn] auto-login failed; switching to interactive wait")
            else:
                print("[warn] auto-login failed; interactive fallback disabled")

        if interactive:
            wait_sec = max(10, int(login_wait_sec))
            print(f"[action] 브라우저에서 티스토리 로그인 완료를 기다립니다. (최대 {wait_sec}초)")
            manage_url = f"https://{self.blog_domain}/manage/newpost/"
            try:
                self.driver.get(manage_url)
                self._wait().until(lambda d: d.execute_script("return document.readyState") == "complete")
            except Exception:
                pass
            end_ts = time.time() + wait_sec
            while time.time() < end_ts:
                try:
                    handles = list(self.driver.window_handles or [])
                    if handles:
                        try:
                            cur_handle = self.driver.current_window_handle
                        except Exception:
                            cur_handle = ""
                        if cur_handle not in handles:
                            self.driver.switch_to.window(handles[0])
                    cur = str(self.driver.current_url or "")
                    if "/manage/" in cur:
                        return
                except NoSuchWindowException:
                    handles = list(self.driver.window_handles or [])
                    if handles:
                        self.driver.switch_to.window(handles[0])
                time.sleep(2)
            raise RuntimeError(f"not logged in after waiting {wait_sec}s")
        else:
            raise RuntimeError("not logged in. rerun with --interactive-login or use debugger session.")

    def _find_first(self, selectors: list[tuple[str, str]]):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        for by, query in selectors:
            try:
                rows = self.driver.find_elements(by, query)
            except UnexpectedAlertPresentException:
                self.resolve_draft_alert()
                rows = self.driver.find_elements(by, query)
            if rows:
                for row in rows:
                    try:
                        if row.is_displayed() and row.is_enabled():
                            return row
                    except Exception:
                        continue
                return rows[0]
        return None

    def set_title(self, title: str):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        self.resolve_draft_alert()
        selectors = [
            (By.CSS_SELECTOR, "input[name='title']"),
            (By.CSS_SELECTOR, "textarea[name='title']"),
            (By.CSS_SELECTOR, "#post-title-inp"),
            (By.CSS_SELECTOR, "input[id*='title']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][data-role='title']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][placeholder*='제목']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][aria-label*='제목']"),
        ]
        el = None
        for by, query in selectors:
            rows = []
            for _ in range(3):
                try:
                    rows = self.driver.find_elements(by, query)
                    break
                except UnexpectedAlertPresentException:
                    self.resolve_draft_alert()
                    time.sleep(0.2)
            if not rows:
                continue
            # Prefer interactable element first, then first fallback.
            interactive = []
            for r in rows:
                try:
                    if r.is_displayed() and r.is_enabled():
                        interactive.append(r)
                except UnexpectedAlertPresentException:
                    self.resolve_draft_alert()
                except Exception:
                    pass
            el = interactive[0] if interactive else rows[0]
            if el:
                break
        if not el:
            raise RuntimeError("title input not found")

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", el)
        except Exception:
            try:
                el.click()
            except Exception:
                pass

        # 1) Standard input path
        try:
            el.clear()
        except Exception:
            pass
        try:
            el.send_keys(Keys.CONTROL, "a")
            el.send_keys(Keys.DELETE)
            el.send_keys(title)
            return
        except Exception:
            pass

        # 2) JS fallback for input/textarea/contenteditable
        js_ok = bool(
            self.driver.execute_script(
                """
                const el = arguments[0];
                const val = String(arguments[1] || "");
                if (!el) return false;
                if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
                  el.value = val;
                  el.dispatchEvent(new Event("input", { bubbles: true }));
                  el.dispatchEvent(new Event("change", { bubbles: true }));
                  return true;
                }
                if (el.isContentEditable || el.getAttribute("contenteditable") === "true") {
                  el.innerText = val;
                  el.dispatchEvent(new Event("input", { bubbles: true }));
                  return true;
                }
                return false;
                """,
                el,
                title,
            )
        )
        if js_ok:
            return
        raise RuntimeError("title input found but not interactable")


    def set_content_html(self, content_html: str):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        self.resolve_draft_alert()

        ready_script = (
            "return (function(){"
            "var out={tinymce:false, iframe:false, prose:false, textarea:false};"
            "try{out.tinymce=!!(window.tinymce&&tinymce.get('editor-tistory'));}catch(_e){}"
            "try{var f=document.querySelector('#editor-tistory_ifr'); out.iframe=!!(f&&f.contentDocument&&f.contentDocument.body);}catch(_e){}"
            "try{out.prose=!!document.querySelector('.ProseMirror');}catch(_e){}"
            "try{out.textarea=!!document.querySelector('#editor-tistory, textarea[name=\"content\"]');}catch(_e){}"
            "return out;"
            "})();"
        )
        editor_state: dict[str, Any] = {}
        for _ in range(40):
            editor_state = self.driver.execute_script(ready_script) or {}
            if any(bool(editor_state.get(k)) for k in ("tinymce", "iframe", "prose", "textarea")):
                break
            time.sleep(0.15)

        # TinyMCE API is the authoritative path for Tistory; other buffers are sync/fallback.
        write_script = (
            "return (function(html){"
            "html=String(html||'');"
            "var out={tinymce:false, iframe:false, prose:false, editable:false, textarea:false, any:false};"
            "try{if(window.tinymce&&tinymce.get('editor-tistory')){var ed=tinymce.get('editor-tistory'); ed.setContent(html,{format:'raw'}); try{ed.save();}catch(_e){} out.tinymce=true; out.any=true; return out;}}catch(_e){}"
            "try{var f=document.querySelector('#editor-tistory_ifr'); if(f&&f.contentDocument&&f.contentDocument.body){var b=f.contentDocument.body; b.innerHTML=html; try{b.dispatchEvent(new Event('input',{bubbles:true})); b.dispatchEvent(new Event('change',{bubbles:true}));}catch(_e){} out.iframe=true; out.any=true;}}catch(_e){}"
            "try{var ta=document.querySelector('#editor-tistory, textarea[name=\"content\"]'); if(ta){ta.value=html; try{ta.dispatchEvent(new Event('input',{bubbles:true})); ta.dispatchEvent(new Event('change',{bubbles:true}));}catch(_e){} out.textarea=true; out.any=true;}}catch(_e){}"
            "try{var p=document.querySelector('.ProseMirror'); if(p){p.focus(); try{document.execCommand('selectAll',false,null);}catch(_e){} try{document.execCommand('insertHTML',false,html);}catch(_e){p.innerHTML=html;} try{p.dispatchEvent(new Event('input',{bubbles:true})); p.dispatchEvent(new Event('change',{bubbles:true}));}catch(_e){} out.prose=true; out.any=true;}}catch(_e){}"
            "try{var list=Array.prototype.slice.call(document.querySelectorAll('div[contenteditable=\"true\"]')).filter(function(el){var hint=((el.getAttribute('data-role')||'')+' '+(el.getAttribute('placeholder')||'')+' '+(el.getAttribute('aria-label')||'')).toLowerCase(); return hint.indexOf('title')===-1;}); if(list.length){list.sort(function(a,b){return (b.clientWidth*b.clientHeight)-(a.clientWidth*a.clientHeight);}); var e=list[0]; e.focus(); e.innerHTML=html; try{e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));}catch(_e){} out.editable=true; out.any=true;}}catch(_e){}"
            "return out;"
            "})(arguments[0]);"
        )
        write_res = self.driver.execute_script(write_script, content_html) or {}
        if not bool((write_res or {}).get("any", False)):
            raise RuntimeError(f"content editor not found: state={editor_state}")

        plain = re.sub(r"<[^>]+>", " ", str(content_html or ""))
        plain = re.sub(r"\s+", " ", plain).strip()
        expected_min = max(12, min(120, int(len(plain) * 0.18)))
        reg_match = re.search(r"seoulmna\.co\.kr/mna/(\d+)", str(content_html or ""), flags=re.I)
        probe_tokens: list[str] = []
        if reg_match:
            reg = str(reg_match.group(1))
            probe_tokens = [
                f"https://seoulmna.co.kr/mna/{reg}",
                f"http://seoulmna.co.kr/mna/{reg}",
                f"seoulmna.co.kr/mna/{reg}",
                f"/mna/{reg}",
            ]
        verify_script = (
            "return (function(tokens){"
            "function _t(v){return String(v||'').replace(/\\s+/g,' ').trim().length;}"
            "function _hAny(v,tokens){var s=String(v||'').toLowerCase(); for(var i=0;i<tokens.length;i++){var t=String(tokens[i]||'').toLowerCase(); if(t && s.indexOf(t)>=0){return true;}} return false; }"
            "var __codex_editor_text_len__=0; var __codex_editor_has_probe__=false; var __codex_editor_probe_iframe__=false; var __codex_editor_probe_tinymce__=false; var __codex_editor_probe_ta__=false; var __codex_editor_has_iframe__=false; var __codex_editor_has_tinymce__=false;"
            "var __tokens__=Array.isArray(tokens)?tokens:[];"
            "try{if(window.tinymce&&tinymce.get('editor-tistory')){__codex_editor_has_tinymce__=true; var ed=tinymce.get('editor-tistory'); var h=ed.getContent(); var t=ed.getContent({format:'text'}); __codex_editor_text_len__=Math.max(__codex_editor_text_len__, _t(t)); __codex_editor_probe_tinymce__=_hAny(h,__tokens__); __codex_editor_has_probe__=__codex_editor_has_probe__||__codex_editor_probe_tinymce__;}}catch(_e){}"
            "try{var f=document.querySelector('#editor-tistory_ifr'); if(f&&f.contentDocument&&f.contentDocument.body){__codex_editor_has_iframe__=true; var b=f.contentDocument.body; __codex_editor_text_len__=Math.max(__codex_editor_text_len__, _t(b.innerText||b.textContent)); __codex_editor_probe_iframe__=_hAny(b.innerHTML,__tokens__); __codex_editor_has_probe__=__codex_editor_has_probe__||__codex_editor_probe_iframe__;}}catch(_e){}"
            "try{var p=document.querySelector('.ProseMirror'); if(p){__codex_editor_text_len__=Math.max(__codex_editor_text_len__, _t(p.innerText||p.textContent)); __codex_editor_has_probe__=__codex_editor_has_probe__||_hAny(p.innerHTML,__tokens__);}}catch(_e){}"
            "try{var list=Array.prototype.slice.call(document.querySelectorAll('div[contenteditable=\"true\"]')).filter(function(el){var hint=((el.getAttribute('data-role')||'')+' '+(el.getAttribute('placeholder')||'')+' '+(el.getAttribute('aria-label')||'')).toLowerCase(); return hint.indexOf('title')===-1;}); for(var i=0;i<list.length;i++){var c=list[i]; __codex_editor_text_len__=Math.max(__codex_editor_text_len__, _t(c.innerText||c.textContent)); __codex_editor_has_probe__=__codex_editor_has_probe__||_hAny(c.innerHTML,__tokens__);}}catch(_e){}"
            "try{var ta=document.querySelector('#editor-tistory, textarea[name=\"content\"]'); if(ta){__codex_editor_text_len__=Math.max(__codex_editor_text_len__, _t(ta.value)); __codex_editor_probe_ta__=_hAny(ta.value,__tokens__); __codex_editor_has_probe__=__codex_editor_has_probe__||__codex_editor_probe_ta__;}}catch(_e){}"
            "return {__codex_editor_text_len__:__codex_editor_text_len__, __codex_editor_has_probe__:__codex_editor_has_probe__, __codex_editor_probe_iframe__:__codex_editor_probe_iframe__, __codex_editor_probe_tinymce__:__codex_editor_probe_tinymce__, __codex_editor_probe_ta__:__codex_editor_probe_ta__, __codex_editor_has_iframe__:__codex_editor_has_iframe__, __codex_editor_has_tinymce__:__codex_editor_has_tinymce__};"
            "})(arguments[0]);"
        )
        last_len = 0
        last_probe = False
        stable = 0
        for _ in range(24):
            verify_res = self.driver.execute_script(verify_script, probe_tokens)
            written_len = int((verify_res or {}).get("__codex_editor_text_len__", 0))
            has_probe = bool((verify_res or {}).get("__codex_editor_has_probe__", False))
            probe_iframe = bool((verify_res or {}).get("__codex_editor_probe_iframe__", False))
            probe_tinymce = bool((verify_res or {}).get("__codex_editor_probe_tinymce__", False))
            last_len = written_len
            last_probe = has_probe
            ok_len = written_len >= expected_min
            if probe_tokens:
                ok_probe = has_probe or probe_iframe or probe_tinymce
                stable = stable + 1 if (ok_len and ok_probe) else 0
            else:
                stable = stable + 1 if ok_len else 0
            if stable >= 2:
                return
            time.sleep(0.15)
        if probe_tokens and (not last_probe):
            raise RuntimeError("content write verification failed: probe URL not found in editor buffer")
        if last_len < expected_min:
            raise RuntimeError(
                f"content write verification failed: written_len={last_len} < expected_min={expected_min}"
            )

    def click_publish(self, delay_sec: float = 0.6):
        if not self.driver:
            raise RuntimeError("driver is not initialized")
        self.resolve_draft_alert()
        btn = self._find_first(
            [
                (By.CSS_SELECTOR, "#publish-layer-btn"),
                (By.CSS_SELECTOR, "button.publish"),
                (By.CSS_SELECTOR, "button.btn-publish"),
                (By.CSS_SELECTOR, "button[class*='publish']"),
                (By.XPATH, "//button[contains(., '발행')]"),
                (By.XPATH, "//button[contains(., '완료')]"),
            ]
        )
        if not btn:
            raise RuntimeError("publish button not found")
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        except Exception:
            pass
        try:
            btn.click()
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", btn)
            except Exception as exc:
                raise RuntimeError(f"publish button click failed: {exc}") from exc
        time.sleep(max(0.1, float(delay_sec)))
        confirm = self._find_first(
            [
                (By.XPATH, "//button[contains(., '공개 발행')]"),
                (By.XPATH, "//button[contains(., '발행')]"),
                (By.CSS_SELECTOR, "button.confirm, button.btn-confirm"),
            ]
        )
        if confirm:
            confirm.click()

    def screenshot(self, path: str):
        if self.driver:
            self.driver.save_screenshot(path)


def run(args: argparse.Namespace) -> int:
    data = _load_listing_data(args)
    registration_no = _extract_registration_no(data, explicit=args.registration)
    image_urls = [str(x).strip() for x in (args.image_url or []) if str(x).strip()]
    env_auto_images = _to_bool(CONFIG.get("TISTORY_AUTO_IMAGES", "1"), True)
    auto_images = env_auto_images if args.auto_images is None else bool(args.auto_images)
    image_count = _to_int(args.image_count or CONFIG.get("TISTORY_IMAGE_COUNT", "2"), 2)
    package = build_post_package(
        data,
        title_override=args.title,
        source_url=args.source_url,
        image_urls=image_urls,
        auto_images=bool(auto_images),
        image_count=max(0, int(image_count)),
    )

    blog_domain_raw = str(args.blog_domain or CONFIG.get("TISTORY_BLOG_DOMAIN", "")).strip()
    blog_domain = _validate_blog_domain(blog_domain_raw, override_domains=args.allowed_blog_domain)
    content_digest = _content_digest(package["title"], package["content"], package["source_url"])
    content_signature = _content_signature(package["content"])
    payload_preview = {
        "title": package["title"],
        "registration_no": registration_no,
        "blog_domain": blog_domain,
        "source_url": package["source_url"],
        "content_length": len(package["content"]),
        "content_digest": content_digest,
        "content_signature": content_signature,
        "dry_run": bool(args.dry_run),
        "republish_changed": bool(args.republish_changed),
        "auto_images": bool(auto_images),
        "image_count": int(image_count),
    }
    seo_report = evaluate_seo_quality(package["title"], package["content"], registration_no)
    legal_report = evaluate_legal_quality(package["title"], package["content"], registration_no)
    cx_report = evaluate_cx_quality(package["title"], package["content"], registration_no)
    payload_preview["seo_score"] = int(seo_report.get("score", 0))
    payload_preview["seo_ok"] = bool(seo_report.get("ok", False))
    payload_preview["legal_score"] = int(legal_report.get("score", 0))
    payload_preview["legal_ok"] = bool(legal_report.get("ok", False))
    payload_preview["cx_score"] = int(cx_report.get("score", 0))
    payload_preview["cx_ok"] = bool(cx_report.get("ok", False))
    payload_preview["review_agents"] = {
        "seo": {"score": int(seo_report.get("score", 0)), "ok": bool(seo_report.get("ok", False))},
        "legal": {"score": int(legal_report.get("score", 0)), "ok": bool(legal_report.get("ok", False))},
        "cx": {"score": int(cx_report.get("score", 0)), "ok": bool(cx_report.get("ok", False))},
    }
    if args.print_payload:
        print(json.dumps(payload_preview, ensure_ascii=False, indent=2))

    min_seo_score = _to_int(args.seo_min_score or CONFIG.get("TISTORY_SEO_MIN_SCORE", "90"), 90)
    min_legal_score = _to_int(args.legal_min_score or CONFIG.get("TISTORY_LEGAL_MIN_SCORE", "85"), 85)
    min_cx_score = _to_int(args.cx_min_score or CONFIG.get("TISTORY_CX_MIN_SCORE", "85"), 85)
    if bool(args.seo_gate) and int(seo_report.get("score", 0)) < int(min_seo_score):
        audit_dir = Path(str(args.audit_dir or CONFIG.get("TISTORY_PUBLISH_AUDIT_DIR", "logs/tistory_publish_audit")).strip())
        if not audit_dir.is_absolute():
            audit_dir = ROOT / audit_dir
        audit_path = _write_audit(
            audit_dir=audit_dir,
            status="blocked_seo_gate",
            registration_no=registration_no,
            payload_preview=payload_preview,
            error=f"seo_score<{min_seo_score}",
            tag=args.audit_tag,
            extra={"seo_report": seo_report, "legal_report": legal_report, "cx_report": cx_report},
        )
        print(f"[saved] audit: {audit_path}")
        raise RuntimeError(
            f"seo gate blocked publish: score={seo_report.get('score')} < min={min_seo_score}"
        )

    if bool(args.legal_gate) and int(legal_report.get("score", 0)) < int(min_legal_score):
        audit_dir = Path(str(args.audit_dir or CONFIG.get("TISTORY_PUBLISH_AUDIT_DIR", "logs/tistory_publish_audit")).strip())
        if not audit_dir.is_absolute():
            audit_dir = ROOT / audit_dir
        audit_path = _write_audit(
            audit_dir=audit_dir,
            status="blocked_legal_gate",
            registration_no=registration_no,
            payload_preview=payload_preview,
            error=f"legal_score<{min_legal_score}",
            tag=args.audit_tag,
            extra={"seo_report": seo_report, "legal_report": legal_report, "cx_report": cx_report},
        )
        print(f"[saved] audit: {audit_path}")
        raise RuntimeError(
            f"legal gate blocked publish: score={legal_report.get('score')} < min={min_legal_score}"
        )

    if bool(args.cx_gate) and int(cx_report.get("score", 0)) < int(min_cx_score):
        audit_dir = Path(str(args.audit_dir or CONFIG.get("TISTORY_PUBLISH_AUDIT_DIR", "logs/tistory_publish_audit")).strip())
        if not audit_dir.is_absolute():
            audit_dir = ROOT / audit_dir
        audit_path = _write_audit(
            audit_dir=audit_dir,
            status="blocked_cx_gate",
            registration_no=registration_no,
            payload_preview=payload_preview,
            error=f"cx_score<{min_cx_score}",
            tag=args.audit_tag,
            extra={"seo_report": seo_report, "legal_report": legal_report, "cx_report": cx_report},
        )
        print(f"[saved] audit: {audit_path}")
        raise RuntimeError(
            f"cx gate blocked publish: score={cx_report.get('score')} < min={min_cx_score}"
        )

    out_html = str(args.out_html or "").strip()
    if out_html:
        out = Path(out_html)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(package["content"], encoding="utf-8")
        print(f"[saved] html: {out}")
        full_out = out.with_name(f"{out.stem}_full{out.suffix or '.html'}")
        full_out.write_text(_wrap_preview_html_document(package["content"], package["title"]), encoding="utf-8")
        print(f"[saved] html(full): {full_out}")

    state_file = Path(str(args.state_file or CONFIG.get("TISTORY_PUBLISH_STATE_FILE", "logs/tistory_publish_state.json")).strip())
    if not state_file.is_absolute():
        state_file = ROOT / state_file
    audit_dir = Path(str(args.audit_dir or CONFIG.get("TISTORY_PUBLISH_AUDIT_DIR", "logs/tistory_publish_audit")).strip())
    if not audit_dir.is_absolute():
        audit_dir = ROOT / audit_dir

    if registration_no and (not args.force):
        state = _load_state(state_file)
        action, previous = _duplicate_decision(
            state=state,
            registration_no=registration_no,
            content_digest=content_digest,
            content_signature=content_signature,
            republish_changed=bool(args.republish_changed),
        )
        if action in {"skip_duplicate", "skip_changed", "skip_duplicate_signature"} and (not args.dry_run):
            status_map = {
                "skip_duplicate": "skipped_duplicate",
                "skip_changed": "skipped_changed",
                "skip_duplicate_signature": "skipped_duplicate_signature",
            }
            status = status_map.get(action, "skipped_duplicate")
            audit_path = _write_audit(
                audit_dir=audit_dir,
                status=status,
                registration_no=registration_no,
                payload_preview=payload_preview,
                tag=args.audit_tag,
                extra={"decision": action, "previous": previous or {}},
            )
            print(f"[skip] publish blocked by state policy: {registration_no} ({action})")
            print(f"[saved] audit: {audit_path}")
            print(
                json.dumps(
                    {
                        "ok": True,
                        "published": False,
                        "skipped": status,
                        "decision": action,
                        "registration_no": registration_no,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if action == "allow_changed":
            when = str((previous or {}).get("published_at") or "").strip()
            print(f"[info] content changed since last publish ({when}); republish allowed.")

    if args.dry_run and not args.open_browser:
        audit_path = _write_audit(
            audit_dir=audit_dir,
            status="dry_run",
            registration_no=registration_no,
            payload_preview=payload_preview,
            tag=args.audit_tag,
            extra={"decision": "dry_run_only"},
        )
        print("[dry-run] browser publish skipped")
        print(f"[saved] audit: {audit_path}")
        return 0

    debugger = str(args.debugger or CONFIG.get("TISTORY_CHROME_DEBUGGER", "")).strip()
    user_data_dir = str(args.user_data_dir or CONFIG.get("TISTORY_CHROME_USER_DATA_DIR", "")).strip()
    if (not debugger) and (not user_data_dir):
        user_data_dir = _default_chrome_user_data_dir()
    profile_dir = str(args.profile_dir or CONFIG.get("TISTORY_CHROME_PROFILE_DIR", "Default")).strip()
    timeout_sec = _to_int(args.timeout_sec or CONFIG.get("TISTORY_PAGE_TIMEOUT_SEC", "30"), 30)
    delay_sec = float(args.publish_delay_sec or CONFIG.get("TISTORY_PUBLISH_DELAY_SEC", "0.6"))
    env_auto_login = _to_bool(CONFIG.get("TISTORY_AUTO_LOGIN", "0"), False)
    auto_login = env_auto_login if args.auto_login is None else bool(args.auto_login)
    login_id = str(args.login_id or CONFIG.get("TISTORY_LOGIN_ID", "")).strip()
    login_password = str(args.login_password or CONFIG.get("TISTORY_LOGIN_PASSWORD", "")).strip()
    login_url = str(args.login_url or CONFIG.get("TISTORY_LOGIN_URL", "https://www.tistory.com/auth/login")).strip()
    payload_preview["auto_login"] = bool(auto_login)

    with TistoryBrowserPublisher(
        blog_domain=blog_domain,
        debugger=debugger,
        user_data_dir=user_data_dir,
        profile_dir=profile_dir,
        timeout_sec=timeout_sec,
        draft_policy=args.draft_policy,
    ) as pub:
        try:
            pub.open_editor()
            pub.wait_for_login(
                interactive=bool(args.interactive_login),
                login_wait_sec=int(args.login_wait_sec),
                auto_login=bool(auto_login),
                login_id=login_id,
                login_password=login_password,
                login_url=login_url,
            )
            pub.resolve_draft_alert()
            pub.set_title(package["title"])
            pub.set_content_html(package["content"])
            screenshot_path = Path(str(args.screenshot or "").strip()) if str(args.screenshot or "").strip() else (ROOT / "logs" / "tistory_browser_preview.png")
            if not screenshot_path.is_absolute():
                screenshot_path = ROOT / screenshot_path
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            pub.screenshot(str(screenshot_path))
            print(f"[saved] screenshot: {screenshot_path}")
            if args.dry_run:
                audit_path = _write_audit(
                    audit_dir=audit_dir,
                    status="browser_dry_run",
                    registration_no=registration_no,
                    payload_preview=payload_preview,
                    tag=args.audit_tag,
                    extra={"screenshot": str(screenshot_path)},
                )
                print("[dry-run] editor filled, publish click skipped")
                print(f"[saved] audit: {audit_path}")
                return 0
            pub.click_publish(delay_sec=delay_sec)
            if registration_no:
                state = _load_state(state_file)
                state = _mark_published(
                    state,
                    registration_no,
                    package["title"],
                    blog_domain,
                    package["source_url"],
                    content_digest=content_digest,
                    content_signature=content_signature,
                )
                _save_state(state_file, state)
                print(f"[saved] state: {state_file}")
            audit_path = _write_audit(
                audit_dir=audit_dir,
                status="published",
                registration_no=registration_no,
                payload_preview=payload_preview,
                tag=args.audit_tag,
                extra={"screenshot": str(screenshot_path), "state_file": str(state_file)},
            )
            print(f"[saved] audit: {audit_path}")
            print(json.dumps({"ok": True, "published": True, "blog_domain": blog_domain}, ensure_ascii=False, indent=2))
            return 0
        except TimeoutException as exc:
            audit_path = _write_audit(
                audit_dir=audit_dir,
                status="failed",
                registration_no=registration_no,
                payload_preview=payload_preview,
                error=f"timeout:{exc}",
                tag=args.audit_tag,
                extra={"exception": "TimeoutException"},
            )
            print(f"[saved] audit: {audit_path}")
            raise RuntimeError(f"timeout during tistory editor automation: {exc}") from exc
        except Exception as exc:
            audit_path = _write_audit(
                audit_dir=audit_dir,
                status="failed",
                registration_no=registration_no,
                payload_preview=payload_preview,
                error=str(exc),
                tag=args.audit_tag,
                extra={"exception": exc.__class__.__name__},
            )
            print(f"[saved] audit: {audit_path}")
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish to Tistory via browser automation (Open API fallback)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--registration", help="sheet registration number (e.g. 7540)")
    group.add_argument("--json-input", help="gabji-like json input path")
    group.add_argument("--image", help="gabji screenshot image path (Gemini key required)")

    parser.add_argument("--blog-domain", default="", help="tistory blog domain (e.g. seoulmna.tistory.com)")
    parser.add_argument("--title", default="", help="override post title")
    parser.add_argument("--source-url", default="", help="source url override")
    parser.add_argument("--image-url", action="append", default=[], help="image URL to include in content (repeatable)")
    parser.add_argument("--out-html", default="", help="save rendered html for preview")
    parser.add_argument("--print-payload", action="store_true", help="print payload preview")
    parser.add_argument("--auto-images", dest="auto_images", action="store_true", default=None, help="auto-generate listing images when --image-url is not provided")
    parser.add_argument("--no-auto-images", dest="auto_images", action="store_false", help="disable auto-generated listing images")
    parser.add_argument("--image-count", default="", help="auto image count (default: 2)")
    parser.add_argument("--seo-min-score", default="", help="minimum SEO score to publish (default: 90)")
    parser.add_argument("--seo-gate", dest="seo_gate", action="store_true", default=True, help="enforce SEO quality gate before publish")
    parser.add_argument("--no-seo-gate", dest="seo_gate", action="store_false", help="disable SEO quality gate")
    parser.add_argument("--legal-min-score", default="", help="minimum legal score to publish (default: 85)")
    parser.add_argument("--legal-gate", dest="legal_gate", action="store_true", default=True, help="enforce legal quality gate before publish")
    parser.add_argument("--no-legal-gate", dest="legal_gate", action="store_false", help="disable legal quality gate")
    parser.add_argument("--cx-min-score", default="", help="minimum CX score to publish (default: 85)")
    parser.add_argument("--cx-gate", dest="cx_gate", action="store_true", default=True, help="enforce customer-experience quality gate before publish")
    parser.add_argument("--no-cx-gate", dest="cx_gate", action="store_false", help="disable customer-experience quality gate")

    parser.add_argument("--dry-run", action="store_true", help="do not click publish")
    parser.add_argument("--open-browser", action="store_true", help="even in dry-run, open browser and fill editor")
    parser.add_argument("--interactive-login", action="store_true", help="wait for manual login in browser")
    parser.add_argument("--login-wait-sec", default="180", help="max seconds to wait for manual login when --interactive-login is used")
    parser.add_argument("--auto-login", dest="auto_login", action="store_true", default=None, help="try auto-login first (uses --login-id/--login-password or env)")
    parser.add_argument("--no-auto-login", dest="auto_login", action="store_false", help="disable auto-login")
    parser.add_argument("--login-id", default="", help="tistory/kakao login id (optional)")
    parser.add_argument("--login-password", default="", help="tistory/kakao login password (optional)")
    parser.add_argument("--login-url", default="", help="login URL override (default: https://www.tistory.com/auth/login)")
    parser.add_argument("--debugger", default="", help="chrome debugger address, e.g. 127.0.0.1:9222")
    parser.add_argument("--user-data-dir", default="", help="chrome user data dir for non-debugger mode")
    parser.add_argument("--profile-dir", default="", help="chrome profile directory")
    parser.add_argument("--timeout-sec", default="", help="page timeout seconds")
    parser.add_argument("--publish-delay-sec", default="", help="delay between publish clicks")
    parser.add_argument("--state-file", default="", help="state file path for duplicate prevention")
    parser.add_argument("--audit-dir", default="", help="audit json directory")
    parser.add_argument("--audit-tag", default="", help="short tag for audit file names")
    parser.add_argument(
        "--draft-policy",
        choices=["discard", "resume"],
        default="discard",
        help="how to handle tistory draft resume popup (default: discard)",
    )
    parser.add_argument("--force", action="store_true", help="ignore duplicate publish guard")
    parser.add_argument("--screenshot", default="", help="screenshot path")
    parser.add_argument(
        "--republish-changed",
        dest="republish_changed",
        action="store_true",
        default=True,
        help="allow republish when same registration has changed content digest (default: true)",
    )
    parser.add_argument(
        "--no-republish-changed",
        dest="republish_changed",
        action="store_false",
        help="block republish when registration already exists in state, even if content changed",
    )
    parser.add_argument(
        "--allowed-blog-domain",
        action="append",
        default=[],
        help="allowed blog domain override for safety gate (repeatable)",
    )
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
