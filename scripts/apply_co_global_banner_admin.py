import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict

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
    page = sess.get(f"{base}/bbs/login.php?url=%2Fadm%2F", headers=ua, timeout=20)
    page.raise_for_status()
    final_url = str(getattr(page, "url", "") or "")
    if "gethompy.com/503" in final_url:
        raise RuntimeError("hosting daily transfer cap reached (redirected to gethompy 503 page)")
    soup = BeautifulSoup(page.text, "html.parser")
    form = soup.select_one("form[action*='login_check.php']")
    if not form:
        title = ""
        tnode = soup.select_one("title")
        if tnode:
            title = str(tnode.text or "").strip()
        if "전송량" in title:
            raise RuntimeError("hosting transfer limit page detected; admin login unavailable")
        raise RuntimeError("admin login form not found")
    payload = {}
    for inp in form.select("input[name]"):
        payload[inp.get("name")] = inp.get("value", "")
    payload["mb_id"] = admin_id
    payload["mb_password"] = admin_pw
    action = form.get("action") or f"{base}/bbs/login_check.php"
    if action.startswith("/"):
        action = base + action
    res = sess.post(action, data=payload, headers={**ua, "Referer": page.url}, timeout=20, allow_redirects=True)
    res.raise_for_status()


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


def _strip_legacy_test_chunks(text: str) -> str:
    src = str(text or "").replace("\ufeff", "").replace("\u200b", "")
    if not src:
        return ""
    patterns = [
        r"<!--\s*DUMMY_START\s*-->.*?<!--\s*DUMMY_END\s*-->",
        r"<!--\s*TC START\s*-->.*?<!--\s*TC END\s*-->",
        r"<script>\s*.*?smna-fav-guide-style.*?</script>",
    ]
    out = src
    for patt in patterns:
        out = re.sub(patt, "", out, flags=re.I | re.S)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply global banner script to seoulmna.co.kr admin config")
    parser.add_argument("--base-url", default="https://seoulmna.co.kr")
    parser.add_argument("--snippet-file", default="logs/co_global_banner_snippet.html")
    parser.add_argument("--remove", action="store_true")
    parser.add_argument(
        "--max-snippet-chars",
        type=int,
        default=120000,
        help="Block apply when snippet length exceeds this threshold (prevents cf_add_script truncation).",
    )
    parser.add_argument(
        "--max-total-chars",
        type=int,
        default=130000,
        help="Block apply when computed cf_add_script total length exceeds this threshold.",
    )
    parser.add_argument(
        "--confirm-live",
        default="",
        help="실서비스 반영 승인 토큰. 실제 반영 시 `--confirm-live YES` 필요.",
    )
    parser.add_argument("--force", action="store_true", help="Force apply even when KR-only lock is enabled")
    parser.add_argument("--report", default="logs/co_global_banner_apply_latest.json")
    args = parser.parse_args()
    confirm_live = str(args.confirm_live or "").strip().upper()
    if confirm_live != "YES":
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "base_url": str(args.base_url).rstrip("/"),
            "remove_mode": bool(args.remove),
            "force_mode": bool(args.force),
            "changed": False,
            "error": "live apply blocked: add --confirm-live YES",
            "blocking_issues": ["confirm_live_missing"],
        }
        _save_json((ROOT / args.report).resolve(), blocked)
        print(f"[saved] {(ROOT / args.report).resolve()}")
        print("[ok] False")
        print("[error] live apply blocked: add --confirm-live YES")
        return 2

    base = str(args.base_url).rstrip("/")
    out_path = (ROOT / args.report).resolve()
    if _is_kr_only_mode() and "seoulmna.co.kr" in base.lower() and not bool(args.force):
        blocked = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ok": False,
            "base_url": base,
            "remove_mode": bool(args.remove),
            "force_mode": bool(args.force),
            "changed": False,
            "cf_add_script_before_len": 0,
            "cf_add_script_after_len": 0,
            "marker_found_after": False,
            "error": "kr-only mode enabled: co.kr banner apply is blocked.",
            "blocking_issues": ["kr_only_mode_enabled"],
        }
        _save_json(out_path, blocked)
        print(f"[saved] {out_path}")
        print("[ok] False")
        print("[error] kr-only mode enabled: co.kr banner apply is blocked.")
        return 2

    env = _env_map(ROOT / ".env")
    admin_id = str(env.get("ADMIN_ID", "")).strip()
    admin_pw = str(env.get("ADMIN_PW", "")).strip()
    if not admin_id or not admin_pw:
        raise SystemExit("ADMIN_ID/ADMIN_PW missing in .env")

    snippet_path = (ROOT / args.snippet_file).resolve()
    if not snippet_path.exists():
        raise SystemExit(f"snippet file not found: {snippet_path}")
    snippet = snippet_path.read_text(encoding="utf-8", errors="replace")

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": False,
        "base_url": args.base_url,
        "remove_mode": bool(args.remove),
        "force_mode": bool(args.force),
        "changed": False,
        "legacy_cleanup_removed": False,
        "cf_add_script_before_len": 0,
        "cf_add_script_after_len": 0,
        "snippet_len": len(snippet),
        "max_snippet_chars": int(args.max_snippet_chars),
        "max_total_chars": int(args.max_total_chars),
        "marker_found_after": False,
        "error": "",
    }
    if (not args.remove) and int(len(snippet)) > int(args.max_snippet_chars):
        report["ok"] = False
        report["error"] = (
            f"snippet length {len(snippet)} exceeds safe threshold {int(args.max_snippet_chars)}; "
            "abort apply to prevent cf_add_script truncation"
        )
        _save_json((ROOT / args.report).resolve(), report)
        print(f"[saved] {(ROOT / args.report).resolve()}")
        print(f"[ok] {report.get('ok')}")
        print(f"[error] {report.get('error')}")
        return 2

    sess = requests.Session()
    ua = {"User-Agent": "Mozilla/5.0"}

    try:
        base = str(args.base_url).rstrip("/")
        _login_admin(sess, base, admin_id, admin_pw)
        cfg = sess.get(f"{base}/adm/config_form.php", headers={**ua, "Referer": f"{base}/adm/"}, timeout=20)
        cfg.raise_for_status()

        key_match = re.search(r"admin_csrf_token_key\s*=\s*['\"]([^'\"]+)['\"]", cfg.text)
        if not key_match:
            raise RuntimeError("admin csrf key not found")
        csrf_key = key_match.group(1)
        tok_res = sess.post(
            f"{base}/adm/ajax.token.php",
            data={"admin_csrf_token_key": csrf_key},
            headers={**ua, "Referer": f"{base}/adm/config_form.php", "X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        tok_res.raise_for_status()
        token = str((tok_res.json() or {}).get("token", "")).strip()
        if not token:
            raise RuntimeError("admin csrf token is empty")

        soup = BeautifulSoup(cfg.text, "html.parser")
        form = soup.select_one("form[name=fconfigform], form[action*='config_form_update.php']")
        if not form:
            raise RuntimeError("config form not found")
        payload = _form_payload(form)
        before_raw = str(payload.get("cf_add_script", "") or "")
        before = _strip_legacy_test_chunks(before_raw)
        if before != before_raw:
            report["legacy_cleanup_removed"] = True
            payload["cf_add_script"] = before

        # 과거 실행에서 누적된 트래픽 카운터 블록을 먼저 정리해 중복/절단을 방지한다.
        traffic_marker_start = "<!-- SEOULMNA TRAFFIC COUNTER START -->"
        traffic_marker_end = "<!-- SEOULMNA TRAFFIC COUNTER END -->"
        traffic_pattern = re.compile(
            r"<!-- SEOULMNA TRAFFIC COUNTER START -->.*?<!-- SEOULMNA TRAFFIC COUNTER END -->",
            flags=re.S,
        )
        before = traffic_pattern.sub("", before).strip()
        if traffic_marker_start in before and traffic_marker_end not in before:
            before = before.split(traffic_marker_start, 1)[0].strip()
        elif traffic_marker_start in before:
            # START만 남은 손상 조각 정리
            before = before.split(traffic_marker_start, 1)[0].strip()
        report["cf_add_script_before_len"] = len(before)

        marker_start = "<!-- SEOULMNA GLOBAL BANNER START -->"
        marker_end = "<!-- SEOULMNA GLOBAL BANNER END -->"

        after = before
        if args.remove:
            pattern = re.compile(
                r"<!-- SEOULMNA GLOBAL BANNER START -->.*?<!-- SEOULMNA GLOBAL BANNER END -->",
                flags=re.S,
            )
            if marker_start in before and marker_end not in before:
                # 손상 상태(END 마커 절단) 복구: START 이후를 전부 제거
                after = before.split(marker_start, 1)[0].strip()
            else:
                after = pattern.sub("", before).strip()
        else:
            pattern = re.compile(
                r"<!-- SEOULMNA GLOBAL BANNER START -->.*?<!-- SEOULMNA GLOBAL BANNER END -->",
                flags=re.S,
            )
            if marker_start in before and marker_end in before:
                after = pattern.sub(lambda _m: snippet, before).strip()
            elif marker_start in before and marker_end not in before:
                # 손상 상태(END 마커 절단) 복구 후 신규 스니펫 삽입
                prefix = before.split(marker_start, 1)[0].strip()
                after = (prefix + "\n" + snippet).strip() if prefix else snippet
            else:
                after = (before + "\n" + snippet).strip() if before.strip() else snippet

        if (not args.remove) and int(len(after)) > int(args.max_total_chars):
            report["ok"] = False
            report["changed"] = False
            report["cf_add_script_after_len"] = len(after)
            report["error"] = (
                f"computed cf_add_script length {len(after)} exceeds safe threshold {int(args.max_total_chars)}; "
                "abort apply to prevent truncation"
            )
            _save_json((ROOT / args.report).resolve(), report)
            print(f"[saved] {(ROOT / args.report).resolve()}")
            print(f"[ok] {report.get('ok')}")
            print(f"[error] {report.get('error')}")
            return 2

        if after != before:
            report["changed"] = True
            payload["cf_add_script"] = after

        payload["token"] = token
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

        verify = sess.get(f"{base}/adm/config_form.php", headers={**ua, "Referer": f"{base}/adm/"}, timeout=20)
        verify.raise_for_status()
        verify_soup = BeautifulSoup(verify.text, "html.parser")
        verify_textarea = verify_soup.select_one("textarea[name=cf_add_script]")
        verify_script_text = verify_textarea.text if verify_textarea else ""
        marker_found_after = (marker_start in verify_script_text) and (marker_end in verify_script_text)
        report["marker_found_after"] = marker_found_after
        report["cf_add_script_after_len"] = len(verify_script_text or "")
        report["ok"] = True if (args.remove and not marker_found_after) or ((not args.remove) and marker_found_after) else False
        if not report["ok"]:
            report["error"] = "verification failed: marker state mismatch"
    except Exception as e:
        report["ok"] = False
        report["error"] = str(e)

    _save_json((ROOT / args.report).resolve(), report)
    print(f"[saved] {(ROOT / args.report).resolve()}")
    print(f"[ok] {report.get('ok')}")
    if report.get("error"):
        print(f"[error] {report.get('error')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

