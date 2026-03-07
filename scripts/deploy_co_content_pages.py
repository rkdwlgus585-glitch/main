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
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_MANIFEST = ROOT / "output" / "widget" / "bundles" / "seoul_widget_internal" / "manifest.json"


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


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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


def _load_widget_bundle_entry(manifest_path: Path, widget: str) -> Dict[str, str]:
    manifest = _load_json(manifest_path, {}) or {}
    rows = manifest.get("widgets") if isinstance(manifest, dict) else []
    wanted = str(widget or "").strip().lower()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("widget") or "").strip().lower() != wanted:
            continue
        return {
            "widget": wanted,
            "ok": bool(row.get("ok")),
            "widget_url": str(row.get("widget_url") or "").strip(),
            "iframe_path": str(row.get("iframe_path") or "").strip(),
            "launcher_path": str(row.get("launcher_path") or "").strip(),
        }
    return {}


def _read_text(path: str) -> str:
    src = str(path or "").strip()
    if not src:
        return ""
    file_path = Path(src)
    if not file_path.is_absolute():
        file_path = (ROOT / src).resolve()
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def _build_bridge_content_html(
    *,
    marker: str,
    title: str,
    description: str,
    widget_url: str,
    iframe_html: str,
    open_label: str,
) -> str:
    safe_iframe = str(iframe_html or "").strip()
    if not safe_iframe and widget_url:
        safe_iframe = (
            f'<iframe src="{widget_url}" title="{title}" '
            'style="width:100%;min-height:1320px;border:0" '
            'sandbox="allow-scripts allow-forms allow-same-origin allow-popups allow-popups-to-escape-sandbox" '
            'allow="clipboard-write" loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe>'
        )
    return (
        f"<!-- {marker} -->"
        f'<div id="smna-calc-bridge" data-smna-marker="{marker}" '
        'style="box-sizing:border-box;font-family:Pretendard,\'Noto Sans KR\',\'Malgun Gothic\',Arial,sans-serif;'
        'background:#f4f7fb;border:1px solid #d7e2ee;border-radius:14px;padding:10px;max-width:1120px;margin:0 auto;">'
        '<div class="head" style="display:flex;align-items:center;justify-content:space-between;gap:12px;'
        'padding:10px 14px;min-height:62px;margin-bottom:8px;'
        'background:linear-gradient(124deg,#003764 0%,#014477 72%,#0d4f84 100%);border-radius:10px;">'
        '<div class="head-copy" style="flex:1 1 auto;min-width:0;display:flex;flex-direction:column;justify-content:center;">'
        f'<div class="title" style="margin:0;font-size:20px;line-height:1.16;font-weight:900;color:#f8fbff;">{title}</div>'
        f'<div class="meta" style="margin:3px 0 0;font-size:13px;line-height:1.35;color:#e3f0fc;">{description}</div>'
        '</div>'
        f'<a class="open" href="{widget_url}" target="_blank" rel="noopener noreferrer" '
        'style="display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;padding:8px 12px;'
        'min-height:40px;height:40px;line-height:1;border-radius:9px;background:#ffffff;color:#003764;'
        f'text-decoration:none;font-weight:800;white-space:nowrap;">{open_label}</a>'
        '</div>'
        f"{safe_iframe}"
        '<div style="font-size:12px;line-height:1.5;color:#5b7086;margin-top:8px;">'
        'iframe sandbox/referrerpolicy 적용, 서울건설정보 내부 위젯 엔진 경로를 사용합니다.'
        '</div>'
        '</div>'
    )


def _with_bridge_params(widget_url: str, mode: str) -> str:
    src = str(widget_url or "").strip()
    if not src:
        return ""
    parsed = urlparse(src)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("from", "co")
    if mode:
        query.setdefault("mode", str(mode).strip())
    return urlunparse(parsed._replace(query=urlencode(query)))


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
    parser.add_argument("--acquisition-subject", default="AI 인허가 사전검토 진단기(신규등록 전용)")
    parser.add_argument("--bundle-manifest", default=str(DEFAULT_BUNDLE_MANIFEST))
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

    manifest_path = Path(str(args.bundle_manifest)).resolve()
    customer_widget = _load_widget_bundle_entry(manifest_path, "yangdo")
    acquisition_widget = _load_widget_bundle_entry(manifest_path, "permit")
    customer_url = _with_bridge_params(
        str(customer_widget.get("widget_url") or "https://calc.seoulmna.co.kr/widgets/yangdo?tenant_id=seoul_widget_unlimited").strip(),
        "customer",
    )
    acquisition_url = _with_bridge_params(
        str(acquisition_widget.get("widget_url") or "https://calc.seoulmna.co.kr/widgets/permit?tenant_id=seoul_widget_unlimited").strip(),
        "acquisition",
    )
    customer_text = _build_bridge_content_html(
        marker="SMNA_BRIDGE_CUSTOMER SMNA_WIDGET_BRIDGE_CUSTOMER",
        title="\u0041\u0049 \uc591\ub3c4\uac00 \uc0b0\uc815 \uacc4\uc0b0\uae30",
        description="\uc11c\uc6b8\uac74\uc124\uc815\ubcf4 \uc591\ub3c4\uc591\uc218 \uace0\uac1d\uc6a9 \uacc4\uc0b0\uae30\ub97c \uc774 \ud398\uc774\uc9c0\uc5d0\uc11c \ubc14\ub85c \uc2e4\ud589\ud569\ub2c8\ub2e4.",
        widget_url=customer_url,
        iframe_html=_read_text(str(customer_widget.get("iframe_path") or "")),
        open_label="\uacc4\uc0b0\uae30 \ubc14\ub85c \uc5f4\uae30",
    )
    acquisition_text = _build_bridge_content_html(
        marker="SMNA_BRIDGE_ACQUISITION SMNA_WIDGET_BRIDGE_ACQUISITION",
        title="\u0041\u0049 \uc778\ud5c8\uac00 \uc0ac\uc804\uac80\ud1a0 \uc9c4\ub2e8\uae30(\uc2e0\uaddc\ub4f1\ub85d \uc804\uc6a9)",
        description="\ub4f1\ub85d\uae30\uc900 \ucda9\uc871 \uc5ec\ubd80\uc640 \uc900\ube44 \ud56d\ubaa9\uc744 \uc774 \ud398\uc774\uc9c0\uc5d0\uc11c \ubc14\ub85c \uc810\uac80\ud569\ub2c8\ub2e4.",
        widget_url=acquisition_url,
        iframe_html=_read_text(str(acquisition_widget.get("iframe_path") or "")),
        open_label="\uc0ac\uc804\uac80\ud1a0 \uc2dc\uc791",
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
                verify_keywords=("SMNA_BRIDGE_CUSTOMER", "smna-calc-bridge", customer_url),
            )
        )
        report["results"].append(
            _upsert_content_page(
                sess,
                base,
                co_id=str(args.acquisition_co_id).strip(),
                subject=str(args.acquisition_subject).strip(),
                content_text=acquisition_text,
                verify_keywords=("SMNA_BRIDGE_ACQUISITION", "smna-calc-bridge", acquisition_url),
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




