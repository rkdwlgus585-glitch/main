import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def _is_kr_only_mode() -> bool:
    raw = str(os.getenv("SMNA_KR_ONLY_DEV", "")).strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    return (ROOT / "logs/kr_only_mode.lock").exists()


def _env_map(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip().lstrip("\ufeff")
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _login_admin(sess: requests.Session, base: str, admin_id: str, admin_pw: str) -> str:
    ua = {"User-Agent": "Mozilla/5.0"}
    page = sess.get(f"{base}/bbs/login.php?url=%2Fadm%2F", headers=ua, timeout=20)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")
    form = soup.select_one("form[action*='login_check.php']")
    if not form:
        raise RuntimeError("admin login form not found")

    payload = {}
    for inp in form.select("input[name]"):
        payload[inp.get("name")] = inp.get("value", "")
    payload["mb_id"] = admin_id
    payload["mb_password"] = admin_pw

    action = urljoin(page.url, form.get("action") or "/bbs/login_check.php")
    res = sess.post(action, data=payload, headers={**ua, "Referer": page.url}, timeout=20, allow_redirects=True)
    res.raise_for_status()
    return res.url


def _form_payload(form: BeautifulSoup) -> Dict[str, str]:
    payload = {}
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


def _upsert_content_page(
    sess: requests.Session,
    base: str,
    co_id: str,
    subject: str,
    content_text: str,
    verify_keywords: Tuple[str, ...] = (),
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

    content_ok = str(content_text).strip() in final_content
    if (not content_ok) and verify_keywords:
        content_ok = all(str(k or "").strip() in final_content for k in verify_keywords if str(k or "").strip())

    return {
        "co_id": co_id,
        "mode": "update" if exists else "create",
        "subject_ok": str(subject).strip() in final_subject,
        "content_ok": bool(content_ok),
        "url": f"{base}/bbs/content.php?co_id={co_id}",
        "admin_url": f"{base}/adm/contentform.php?w=u&co_id={co_id}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure seoulmna.co.kr content pages for B-plan calculator routing")
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--customer-co-id", default="ai_calc")
    parser.add_argument("--acquisition-co-id", default="ai_acq")
    parser.add_argument("--customer-subject", default="AI 양도가 산정 계산기")
    parser.add_argument("--acquisition-subject", default="AI 인허가 사전검토 진단기(신규등록)")
    parser.add_argument("--confirm-live", default="", help="실서비스 반영 승인 토큰 (`--confirm-live YES`)")
    parser.add_argument("--report", default="logs/co_content_pages_deploy_latest.json")
    args = parser.parse_args()
    base = str(args.base_url).rstrip("/")
    if str(args.confirm_live or "").strip().upper() != "YES":
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "base_url": base,
            "results": [],
            "error": "live apply blocked: add --confirm-live YES",
            "blocking_issues": ["confirm_live_missing"],
        }
        _save_json((ROOT / args.report).resolve(), blocked)
        print(f"[saved] {(ROOT / args.report).resolve()}")
        print("[ok] False")
        print("[error] live apply blocked: add --confirm-live YES")
        return 2

    out_path = (ROOT / args.report).resolve()
    if _is_kr_only_mode() and "seoulmna.co.kr" in base.lower():
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "base_url": base,
            "results": [],
            "error": "kr-only mode enabled: co.kr content deploy is blocked.",
            "blocking_issues": ["kr_only_mode_enabled"],
        }
        _save_json(out_path, blocked)
        print(f"[saved] {out_path}")
        print("[ok] False")
        print("[error] kr-only mode enabled: co.kr content deploy is blocked.")
        return 2

    env = _env_map(ROOT / ".env")
    admin_id = str(env.get("ADMIN_ID", "")).strip()
    admin_pw = str(env.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        raise SystemExit("ADMIN_ID/ADMIN_PW missing in .env")

    customer_text = (
        "<div id=\"smna-content-fallback-customer\" style=\"max-width:1180px;margin:0 auto;\">"
        "<div style=\"font-size:15px;color:#334155;line-height:1.6;margin:0 0 10px;\">"
        "AI 양도가 산정 계산기 페이지입니다. 페이지 로딩 후 계산기 UI가 자동 표시됩니다. (SMNA_BRIDGE_CUSTOMER)"
        "</div>"
        "<div style=\"margin:0 0 10px;\">"
        "<a href=\"https://seoulmna.kr/yangdo-ai-customer/\" target=\"_blank\" rel=\"noopener noreferrer\" "
        "style=\"display:inline-block;padding:11px 15px;border-radius:10px;background:#003764;color:#fff;text-decoration:none;font-weight:800;\">"
        "계산기 바로 열기"
        "</a>"
        "</div>"
        "<div style=\"font-size:13px;color:#64748b;\">"
        "바로열기 링크: <a href=\"https://seoulmna.kr/yangdo-ai-customer/\" target=\"_blank\" rel=\"noopener noreferrer\">https://seoulmna.kr/yangdo-ai-customer/</a>"
        "</div>"
        "</div>"
    )
    acquisition_text = (
        "<div id=\"smna-content-fallback-acquisition\" style=\"max-width:1180px;margin:0 auto;\">"
        "<div style=\"font-size:15px;color:#334155;line-height:1.6;margin:0 0 10px;\">"
        "AI 인허가 사전검토 진단기(신규등록) 페이지입니다. 페이지 로딩 후 계산기 UI가 자동 표시됩니다. (SMNA_BRIDGE_ACQUISITION)"
        "</div>"
        "<div style=\"margin:0 0 10px;\">"
        "<a href=\"https://seoulmna.kr/ai-license-acquisition-calculator/\" target=\"_blank\" rel=\"noopener noreferrer\" "
        "style=\"display:inline-block;padding:11px 15px;border-radius:10px;background:#003764;color:#fff;text-decoration:none;font-weight:800;\">"
        "계산기 바로 열기"
        "</a>"
        "</div>"
        "<div style=\"font-size:13px;color:#64748b;\">"
        "바로열기 링크: <a href=\"https://seoulmna.kr/ai-license-acquisition-calculator/\" target=\"_blank\" rel=\"noopener noreferrer\">https://seoulmna.kr/ai-license-acquisition-calculator/</a>"
        "</div>"
        "</div>"
    )
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": False,
        "base_url": base,
        "results": [],
        "error": "",
    }

    sess = requests.Session()
    try:
        _login_admin(sess, base, admin_id, admin_pw)
        report["results"].append(
            _upsert_content_page(
                sess,
                base,
                co_id=str(args.customer_co_id).strip(),
                subject=str(args.customer_subject).strip(),
                content_text=customer_text,
                verify_keywords=("SMNA_BRIDGE_CUSTOMER", "seoulmna.kr/yangdo-ai-customer"),
            )
        )
        report["results"].append(
            _upsert_content_page(
                sess,
                base,
                co_id=str(args.acquisition_co_id).strip(),
                subject=str(args.acquisition_subject).strip(),
                content_text=acquisition_text,
                verify_keywords=("SMNA_BRIDGE_ACQUISITION", "seoulmna.kr/ai-license-acquisition-calculator"),
            )
        )

        report["ok"] = all(
            bool(item.get("subject_ok")) and bool(item.get("content_ok")) for item in report["results"]
        )
        if not report["ok"]:
            report["error"] = "content verification mismatch"
    except Exception as e:
        report["ok"] = False
        report["error"] = str(e)

    out_path = (ROOT / args.report).resolve()
    _save_json(out_path, report)
    print(f"[saved] {out_path}")
    print(f"[ok] {report.get('ok')}")
    if report.get("error"):
        print(f"[error] {report.get('error')}")
    for item in report.get("results", []):
        print(
            f"- {item.get('co_id')} mode={item.get('mode')} "
            f"subject_ok={item.get('subject_ok')} content_ok={item.get('content_ok')}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())



