import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]

AI_TRACE_PATTERNS = [
    r"co_id=ai_calc",
    r"co_id=ai_acq",
    r"yangdo-ai-customer",
    r"ai-license-acquisition-calculator",
    r"SMNA_BRIDGE_CUSTOMER",
    r"SMNA_BRIDGE_ACQUISITION",
    r"AI\s*양도가",
    r"AI\s*인허가",
    r"AI\s*계산기",
]


def _is_kr_only_mode() -> bool:
    raw = str(os.getenv("SMNA_KR_ONLY_DEV", "")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    return (ROOT / "logs/kr_only_mode.lock").exists()


def _env_map(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    text = ""
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            text = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _login_admin(sess: requests.Session, base: str, admin_id: str, admin_pw: str) -> None:
    ua = {"User-Agent": "Mozilla/5.0"}
    page = sess.get(f"{base}/bbs/login.php?url=%2Fadm%2F", headers=ua, timeout=20, allow_redirects=True)
    page.raise_for_status()
    final_url = str(getattr(page, "url", "") or "")
    if "gethompy.com/503" in final_url:
        raise RuntimeError("hosting daily transfer cap reached (redirected to gethompy 503 page)")
    soup = BeautifulSoup(page.text, "html.parser")
    form = soup.select_one("form[action*='login_check.php']")
    if not form:
        raise RuntimeError("admin login form not found")
    payload: Dict[str, str] = {}
    for inp in form.select("input[name]"):
        payload[inp.get("name")] = inp.get("value", "")
    payload["mb_id"] = admin_id
    payload["mb_password"] = admin_pw
    action = urljoin(page.url, form.get("action") or "/bbs/login_check.php")
    res = sess.post(action, data=payload, headers={**ua, "Referer": page.url}, timeout=20, allow_redirects=True)
    res.raise_for_status()


def _form_payload(form: BeautifulSoup) -> Dict[str, str]:
    payload: Dict[str, str] = {}
    for el in form.select("input[name], textarea[name], select[name]"):
        name = el.get("name")
        if not name or el.has_attr("disabled"):
            continue
        tag = el.name.lower()
        if tag == "input":
            typ = (el.get("type") or "text").lower()
            if typ in {"submit", "button", "image", "file"}:
                continue
            if typ in {"checkbox", "radio"} and not el.has_attr("checked"):
                continue
            payload[name] = el.get("value", "")
        elif tag == "textarea":
            payload[name] = el.text or ""
        elif tag == "select":
            selected = el.select_one("option[selected]") or el.select_one("option")
            payload[name] = selected.get("value", "") if selected else ""
    return payload


def _fetch_admin_token(sess: requests.Session, base: str, html: str, referer: str) -> str:
    key_match = re.search(r"admin_csrf_token_key\s*=\s*['\"]([^'\"]+)['\"]", html)
    if not key_match:
        raise RuntimeError("admin csrf key not found")
    csrf_key = key_match.group(1)
    ua = {"User-Agent": "Mozilla/5.0"}
    tok_res = sess.post(
        f"{base}/adm/ajax.token.php",
        data={"admin_csrf_token_key": csrf_key},
        headers={**ua, "Referer": referer, "X-Requested-With": "XMLHttpRequest"},
        timeout=20,
    )
    tok_res.raise_for_status()
    token = str((tok_res.json() or {}).get("token", "")).strip()
    if not token:
        raise RuntimeError("admin csrf token is empty")
    return token


def _strip_legacy_test_chunks(text: str) -> str:
    src = str(text or "").replace("\ufeff", "").replace("\u200b", "")
    if not src:
        return ""
    patterns = [
        r"<!--\s*DUMMY_START\s*-->.*?<!--\s*DUMMY_END\s*-->",
        r"<!--\s*TC START\s*-->.*?<!--\s*TC END\s*-->",
        r"<script[^>]*>\s*.*?smna-fav-guide-style.*?</script>",
        r"<script[^>]*>\s*.*?smna-fav-guide.*?</script>",
        r"<section[^>]*id=['\"]smna-fav-guide['\"][^>]*>.*?</section>",
        r"<style[^>]*id=['\"]smna-fav-guide-style['\"][^>]*>.*?</style>",
    ]
    out = src
    for patt in patterns:
        out = re.sub(patt, "", out, flags=re.I | re.S)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def _ai_hits(text: str) -> List[str]:
    src = str(text or "")
    hits: List[str] = []
    for patt in AI_TRACE_PATTERNS:
        if re.search(patt, src, flags=re.I):
            hits.append(patt)
    return hits


def _sanitize_cf_add_script(before_text: str, clean_snippet: str) -> Tuple[str, List[str], List[str]]:
    before = _strip_legacy_test_chunks(before_text)
    hits_before = _ai_hits(before)
    after = str(before)
    marker_start = "<!-- SEOULMNA GLOBAL BANNER START -->"
    marker_end = "<!-- SEOULMNA GLOBAL BANNER END -->"
    global_pattern = re.compile(
        r"<!-- SEOULMNA GLOBAL BANNER START -->.*?<!-- SEOULMNA GLOBAL BANNER END -->",
        flags=re.S,
    )
    if hits_before:
        if marker_start in after and marker_end in after:
            # Keep the non-AI approved banner script while purging old AI-aware block.
            after = global_pattern.sub(lambda _m: clean_snippet, after).strip()
        elif marker_start in after and marker_end not in after:
            prefix = after.split(marker_start, 1)[0].strip()
            after = (prefix + "\n" + clean_snippet).strip() if prefix else clean_snippet
        for patt in [
            r"https?://seoulmna\.co\.kr/bbs/content\.php\?co_id=ai_calc",
            r"https?://seoulmna\.co\.kr/bbs/content\.php\?co_id=ai_acq",
            r"https?://seoulmna\.kr/yangdo-ai-customer/?",
            r"https?://seoulmna\.kr/ai-license-acquisition-calculator/?",
        ]:
            after = re.sub(patt, "https://seoulmna.co.kr/", after, flags=re.I)
    hits_after = _ai_hits(after)
    return after, hits_before, hits_after


def _upsert_content_page(
    sess: requests.Session,
    base: str,
    co_id: str,
    subject: str,
    content_text: str,
) -> Dict[str, str]:
    ua = {"User-Agent": "Mozilla/5.0"}
    edit_url = f"{base}/adm/contentform.php?w=u&co_id={co_id}"
    res = sess.get(edit_url, headers={**ua, "Referer": f"{base}/adm/contentlist.php"}, timeout=20)
    res.raise_for_status()
    html = str(res.text or "")
    exists = "name=\"co_id\"" in html and f"value=\"{co_id}\"" in html
    if not exists:
        create_url = f"{base}/adm/contentform.php"
        res = sess.get(create_url, headers={**ua, "Referer": f"{base}/adm/contentlist.php"}, timeout=20)
        res.raise_for_status()
        html = str(res.text or "")
        form_url = create_url
    else:
        form_url = edit_url

    soup = BeautifulSoup(html, "html.parser")
    form = soup.select_one("form[action*='contentformupdate.php']")
    if not form:
        raise RuntimeError(f"content form not found: {co_id}")
    payload = _form_payload(form)
    payload["token"] = _fetch_admin_token(sess, base, html, referer=form_url)
    payload["w"] = "u" if exists else ""
    payload["co_html"] = "1"
    payload["co_id"] = co_id
    payload["co_subject"] = subject
    payload["co_content"] = content_text
    payload["co_mobile_content"] = content_text

    action = urljoin(form_url, form.get("action") or "./contentformupdate.php")
    upd = sess.post(
        action,
        data=payload,
        headers={**ua, "Referer": form_url},
        timeout=30,
        allow_redirects=True,
    )
    upd.raise_for_status()

    verify_admin = sess.get(
        f"{base}/adm/contentform.php?w=u&co_id={co_id}",
        headers={**ua, "Referer": f"{base}/adm/contentlist.php"},
        timeout=20,
    )
    verify_admin.raise_for_status()
    verify_soup = BeautifulSoup(verify_admin.text, "html.parser")
    subj_node = verify_soup.select_one("input[name=co_subject]")
    body_node = verify_soup.select_one("textarea[name=co_content]")
    final_subject = str(subj_node.get("value", "") if subj_node else "")
    final_content = str(body_node.text if body_node else "")
    ai_left = _ai_hits(final_content + "\n" + final_subject)
    content_marker_ok = ("제공이 종료되었습니다" in final_content) or ("service suspended" in final_content.lower())
    return {
        "co_id": co_id,
        "mode": "update" if exists else "create",
        "subject_ok": str(subject).strip() in final_subject,
        "content_ok": bool(content_marker_ok),
        "ai_hits_left": ",".join(ai_left),
        "url": f"{base}/bbs/content.php?co_id={co_id}",
        "admin_url": f"{base}/adm/contentform.php?w=u&co_id={co_id}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge AI calculator traces from seoulmna.co.kr admin config/pages")
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--clean-snippet", default="snapshots/co_global_banner_test_working.html")
    parser.add_argument("--confirm-live", default="", help="실서비스 반영 승인 토큰. `--confirm-live YES` 필요")
    parser.add_argument("--force", action="store_true", help="Bypass KR-only lock if explicitly requested")
    parser.add_argument("--report", default="logs/co_ai_trace_purge_latest.json")
    args = parser.parse_args()

    base = str(args.base_url or "").strip().rstrip("/")
    report_path = (ROOT / str(args.report)).resolve()
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": False,
        "base_url": base,
        "changed": False,
        "config": {
            "before_len": 0,
            "after_len": 0,
            "ai_hits_before": [],
            "ai_hits_after": [],
            "updated": False,
        },
        "content_pages": [],
        "error": "",
        "blocking_issues": [],
    }

    if str(args.confirm_live or "").strip().upper() != "YES":
        report["error"] = "live apply blocked: add --confirm-live YES"
        report["blocking_issues"].append("confirm_live_missing")
        _save_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[ok] False")
        print(f"[error] {report['error']}")
        return 2

    if _is_kr_only_mode() and ("seoulmna.co.kr" in base.lower()) and (not bool(args.force)):
        report["error"] = "kr-only mode enabled: co.kr purge blocked"
        report["blocking_issues"].append("kr_only_mode_enabled")
        _save_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[ok] False")
        print(f"[error] {report['error']}")
        return 2

    env = _env_map(ROOT / ".env")
    admin_id = str(env.get("ADMIN_ID", "")).strip()
    admin_pw = str(env.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        report["error"] = "ADMIN_ID/ADMIN_PW missing in .env"
        report["blocking_issues"].append("admin_credentials_missing")
        _save_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[ok] False")
        print(f"[error] {report['error']}")
        return 2

    clean_snippet_path = (ROOT / str(args.clean_snippet)).resolve()
    if not clean_snippet_path.exists():
        report["error"] = f"clean snippet file not found: {clean_snippet_path}"
        report["blocking_issues"].append("clean_snippet_missing")
        _save_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[ok] False")
        print(f"[error] {report['error']}")
        return 2
    clean_snippet = clean_snippet_path.read_text(encoding="utf-8", errors="replace").strip()
    clean_hits = _ai_hits(clean_snippet)
    if clean_hits:
        report["error"] = "clean snippet contains AI patterns; abort"
        report["blocking_issues"].append("clean_snippet_has_ai_tokens")
        report["config"]["ai_hits_after"] = clean_hits
        _save_json(report_path, report)
        print(f"[saved] {report_path}")
        print("[ok] False")
        print(f"[error] {report['error']}")
        return 2

    sess = requests.Session()
    ua = {"User-Agent": "Mozilla/5.0"}
    try:
        _login_admin(sess, base, admin_id, admin_pw)

        cfg = sess.get(f"{base}/adm/config_form.php", headers={**ua, "Referer": f"{base}/adm/"}, timeout=20)
        cfg.raise_for_status()
        soup = BeautifulSoup(cfg.text, "html.parser")
        form = soup.select_one("form[name=fconfigform], form[action*='config_form_update.php']")
        if not form:
            raise RuntimeError("config form not found")
        payload = _form_payload(form)
        before = str(payload.get("cf_add_script", "") or "")
        after, hits_before, hits_after = _sanitize_cf_add_script(before, clean_snippet)
        report["config"]["before_len"] = len(before)
        report["config"]["after_len"] = len(after)
        report["config"]["ai_hits_before"] = hits_before
        report["config"]["ai_hits_after"] = hits_after

        if after != before:
            payload["cf_add_script"] = after
            payload["token"] = _fetch_admin_token(sess, base, cfg.text, referer=f"{base}/adm/config_form.php")
            action = form.get("action") or "/adm/config_form_update.php"
            if action.startswith("/"):
                action = base + action
            upd = sess.post(
                action,
                data=payload,
                headers={**ua, "Referer": f"{base}/adm/config_form.php"},
                timeout=30,
                allow_redirects=True,
            )
            upd.raise_for_status()
            report["config"]["updated"] = True
            report["changed"] = True

        neutral_subject = "서비스 안내"
        neutral_content = (
            "<div style=\"max-width:980px;margin:36px auto;padding:22px;border:1px solid #dbe3ec;border-radius:12px;"
            "font-size:15px;line-height:1.7;color:#1f2937;background:#ffffff;\">"
            "<strong style=\"display:block;font-size:18px;margin:0 0 10px;\">안내</strong>"
            "<div>해당 페이지는 운영 정책에 따라 제공이 종료되었습니다.</div>"
            "</div>"
        )
        for co_id in ("ai_calc", "ai_acq"):
            result = _upsert_content_page(
                sess=sess,
                base=base,
                co_id=co_id,
                subject=neutral_subject,
                content_text=neutral_content,
            )
            report["content_pages"].append(result)
            if result.get("mode") in {"update", "create"}:
                report["changed"] = True

        report["ok"] = (
            not bool(report["config"]["ai_hits_after"])
            and all(bool(item.get("subject_ok")) and bool(item.get("content_ok")) and not str(item.get("ai_hits_left") or "") for item in report["content_pages"])
        )
        if not report["ok"] and not report["error"]:
            report["error"] = "verification failed: AI traces still present or content update mismatch"
    except Exception as e:
        report["ok"] = False
        report["error"] = str(e)

    _save_json(report_path, report)
    print(f"[saved] {report_path}")
    print(f"[ok] {report.get('ok')}")
    if report.get("error"):
        print(f"[error] {report.get('error')}")
    print(f"[changed] {report.get('changed')}")
    print(f"[config_ai_before] {len(report.get('config', {}).get('ai_hits_before', []))}")
    print(f"[config_ai_after] {len(report.get('config', {}).get('ai_hits_after', []))}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
