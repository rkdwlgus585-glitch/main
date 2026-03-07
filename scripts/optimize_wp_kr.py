import argparse
import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import load_config

ALLOWED_BLOG_HOSTS = {"seoulmna.kr", "www.seoulmna.kr"}
RANKMATH_RECOMMENDED_MODULES = [
    "link-counter",
    "sitemap",
    "rich-snippet",
    "local-seo",
    "404-monitor",
    "redirections",
    "image-seo",
    "seo-analysis",
    "instant-indexing",
]

WP_TARGET_SETTINGS: Dict[str, Any] = {
    "timezone": "Asia/Seoul",
    "start_of_week": 1,
    "posts_per_page": 10,
    "default_ping_status": "closed",
    "default_comment_status": "closed",
}


def _host_of(url: str) -> str:
    src = str(url or "").strip()
    if not src:
        return ""
    if "://" not in src:
        src = "https://" + src
    host = urlparse(src).netloc.lower()
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def _read_config() -> Dict[str, Any]:
    return load_config(
        {
            "WP_URL": "https://seoulmna.kr/wp-json/wp/v2",
            "WP_USER": "",
            "WP_PASSWORD": "",
            "WP_APP_PASSWORD": "",
            "WP_JWT_TOKEN": "",
            "MAIN_SITE": "https://seoulmna.kr",
            "PHONE": "010-9926-8661",
            "KAKAO_OPENCHAT_URL": "https://open.kakao.com/o/syWr1hIe",
        }
    )


def _resolve_auth_headers(config: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
    jwt_token = str(config.get("WP_JWT_TOKEN", "")).strip()
    if jwt_token:
        return "jwt", {"Authorization": f"Bearer {jwt_token}"}

    user = str(config.get("WP_USER", "")).strip()
    app_password = str(config.get("WP_APP_PASSWORD", "")).strip()
    password = str(config.get("WP_PASSWORD", "")).strip()
    selected_password = app_password or password
    if user and selected_password:
        if app_password:
            selected_password = re.sub(r"\s+", "", selected_password)
        encoded = base64.b64encode(f"{user}:{selected_password}".encode()).decode()
        return "basic", {"Authorization": f"Basic {encoded}"}

    raise RuntimeError("WordPress auth is missing: set WP_JWT_TOKEN or WP_USER + WP_APP_PASSWORD.")


def _request_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any] | None = None,
    timeout_sec: int = 20,
) -> Dict[str, Any]:
    req_headers = dict(headers)
    req_headers.setdefault("Content-Type", "application/json")
    res = requests.request(method, url, headers=req_headers, json=payload, timeout=max(5, int(timeout_sec)))
    out: Dict[str, Any] = {
        "ok": 200 <= int(res.status_code) < 300,
        "status_code": int(res.status_code),
        "url": url,
        "text_preview": (res.text or "")[:400],
    }
    try:
        out["json"] = res.json()
    except Exception:
        out["json"] = None
    return out


def _normalize_wp_root(wp_url: str) -> str:
    src = str(wp_url or "").strip().rstrip("/")
    if not src:
        raise RuntimeError("WP_URL is empty.")
    if "/wp/v2" not in src:
        raise RuntimeError("WP_URL must include '/wp/v2'.")
    return src.split("/wp/v2")[0].rstrip("/")


def _compare_settings(current: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    drift: Dict[str, Dict[str, Any]] = {}
    for key, expected in target.items():
        actual = current.get(key)
        if actual != expected:
            drift[key] = {"current": actual, "target": expected}
    return drift


def _enforce_rankmath(
    wp_root: str,
    auth_headers: Dict[str, str],
    timeout_sec: int,
    mode: str,
    modules: List[str],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"mode": {}, "modules": []}
    mode_res = _request_json(
        "POST",
        f"{wp_root}/rankmath/v1/updateMode",
        auth_headers,
        payload={"mode": mode},
        timeout_sec=timeout_sec,
    )
    out["mode"] = {
        "ok": mode_res.get("ok", False),
        "status_code": mode_res.get("status_code"),
        "result": mode_res.get("json"),
        "text_preview": mode_res.get("text_preview", ""),
    }
    for module in modules:
        mod_res = _request_json(
            "POST",
            f"{wp_root}/rankmath/v1/saveModule",
            auth_headers,
            payload={"module": module, "state": "on"},
            timeout_sec=timeout_sec,
        )
        out["modules"].append(
            {
                "module": module,
                "ok": mod_res.get("ok", False),
                "status_code": mod_res.get("status_code"),
                "result": mod_res.get("json"),
                "text_preview": mod_res.get("text_preview", ""),
            }
        )
    out["ok_count"] = sum(1 for row in out["modules"] if row.get("ok"))
    out["total_count"] = len(out["modules"])
    out["all_ok"] = bool(out["mode"].get("ok")) and out["ok_count"] == out["total_count"]
    return out


def _check_patterns(text: str, patterns: List[str], mode: str) -> Tuple[bool, Dict[str, bool]]:
    found: Dict[str, bool] = {}
    for pat in patterns:
        if pat.startswith("re:"):
            ok = bool(re.search(pat[3:], text, flags=re.IGNORECASE))
        else:
            ok = pat.lower() in text.lower()
        found[pat] = ok
    if mode == "all":
        return all(found.values()), found
    return any(found.values()), found


def _audit_site(url: str, rules: List[Dict[str, Any]], timeout_sec: int) -> Dict[str, Any]:
    row: Dict[str, Any] = {"url": url, "ok": False, "status_code": 0, "rules": [], "error": ""}
    try:
        res = requests.get(
            url,
            timeout=max(5, int(timeout_sec)),
            headers={"User-Agent": "Mozilla/5.0 (compatible; SeoulMNA-SiteGuard/1.0)"},
        )
        body = res.text or ""
        row["status_code"] = int(res.status_code)
        row["html_len"] = len(body)
        for rule in rules:
            hit, found_map = _check_patterns(body, list(rule.get("patterns", [])), str(rule.get("mode", "any")))
            required = bool(rule.get("required", True))
            row["rules"].append(
                {
                    "id": str(rule.get("id", "")),
                    "ok": bool(hit),
                    "required": required,
                    "mode": str(rule.get("mode", "any")),
                    "found": found_map,
                }
            )
        row["ok"] = int(res.status_code) == 200 and all(
            bool(rule.get("ok"))
            for rule in row["rules"]
            if bool(rule.get("required", True))
        )
    except Exception as exc:
        row["error"] = str(exc)
    return row


def _write_reports(report: Dict[str, Any], latest_rel_path: str) -> Tuple[Path, Path]:
    latest_path = (ROOT / str(latest_rel_path)).resolve()
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stamped_name = latest_path.stem + "_" + stamp + latest_path.suffix
    stamped_path = latest_path.with_name(stamped_name)
    stamped_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest_path, stamped_path


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _save_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize and guard seoulmna.kr WordPress settings.")
    parser.add_argument("--apply", action="store_true", help="Apply safe WP settings and RankMath module mode.")
    parser.add_argument(
        "--description",
        default="",
        help="If set, enforce WordPress site tagline/description to this value.",
    )
    parser.add_argument("--skip-rankmath", action="store_true", help="Skip RankMath mode/module actions.")
    parser.add_argument("--skip-co-audit", action="store_true", help="Skip seoulmna.co.kr page marker audit.")
    parser.add_argument("--report", default="logs/wp_site_guard_latest.json")
    parser.add_argument("--state-file", default="logs/wp_site_guard_state.json")
    parser.add_argument("--skip-if-ok-today", action="store_true", help="Skip passive guard runs after one successful run today.")
    parser.add_argument("--force", action="store_true", help="Ignore passive guard skip state.")
    parser.add_argument("--timeout-sec", type=int, default=20)
    args = parser.parse_args()

    config = _read_config()
    wp_url = str(config.get("WP_URL", "")).strip().rstrip("/")
    wp_host = _host_of(wp_url)
    if wp_host not in ALLOWED_BLOG_HOSTS:
        raise SystemExit(f"WP_URL host must be seoulmna.kr. current={wp_host or '(empty)'}")

    state_path = (ROOT / str(args.state_file)).resolve()
    today_key = datetime.now().strftime("%Y-%m-%d")
    if bool(args.skip_if_ok_today) and (not bool(args.apply)) and (not bool(args.force)):
        state = _load_state(state_path)
        if bool(state.get("ok")) and str(state.get("run_date", "")) == today_key:
            print("[summary] skipped=true reason=ok_today")
            return 0

    wp_root = _normalize_wp_root(wp_url)
    auth_mode, auth_headers = _resolve_auth_headers(config)

    report: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "apply_mode": bool(args.apply),
        "wp_url": wp_url,
        "wp_host": wp_host,
        "auth_mode": auth_mode,
        "actions": {},
        "site_audit": [],
    }

    settings_get = _request_json("GET", f"{wp_url}/settings", auth_headers, timeout_sec=int(args.timeout_sec))
    report["actions"]["settings_get"] = {
        "ok": settings_get.get("ok", False),
        "status_code": settings_get.get("status_code"),
    }
    if not settings_get.get("ok"):
        report["actions"]["settings_get"]["error_preview"] = settings_get.get("text_preview", "")
        report["ok"] = False
        latest_path, stamped_path = _write_reports(report, args.report)
        print(f"[saved] {latest_path}")
        print(f"[saved] {stamped_path}")
        print("[summary] settings fetch failed")
        return 2

    settings_current = dict(settings_get.get("json") or {})
    target_settings = dict(WP_TARGET_SETTINGS)
    if str(args.description or "").strip():
        target_settings["description"] = str(args.description).strip()
    report["actions"]["settings_current"] = {k: settings_current.get(k) for k in sorted(target_settings)}

    drift = _compare_settings(settings_current, target_settings)
    report["actions"]["settings_drift"] = drift
    report["actions"]["settings_apply"] = {"attempted": bool(args.apply and bool(drift)), "ok": True}

    if args.apply and drift:
        payload = {k: row["target"] for k, row in drift.items()}
        settings_post = _request_json(
            "POST",
            f"{wp_url}/settings",
            auth_headers,
            payload=payload,
            timeout_sec=int(args.timeout_sec),
        )
        report["actions"]["settings_apply"] = {
            "attempted": True,
            "ok": settings_post.get("ok", False),
            "status_code": settings_post.get("status_code"),
            "payload": payload,
            "response_preview": settings_post.get("text_preview", ""),
        }

    if args.skip_rankmath:
        report["actions"]["rankmath"] = {"skipped": True}
    else:
        if args.apply:
            rankmath = _enforce_rankmath(
                wp_root=wp_root,
                auth_headers=auth_headers,
                timeout_sec=int(args.timeout_sec),
                mode="advanced",
                modules=RANKMATH_RECOMMENDED_MODULES,
            )
        else:
            rankmath = {
                "skipped_apply": True,
                "note": "Run with --apply to enforce RankMath mode/modules.",
                "recommended_modules": list(RANKMATH_RECOMMENDED_MODULES),
            }
        report["actions"]["rankmath"] = rankmath

    phone = str(config.get("PHONE", "")).strip()
    kakao = str(config.get("KAKAO_OPENCHAT_URL", "")).strip()
    kr_rules = [
        {"id": "footer_exists", "mode": "any", "patterns": ["<footer", "re:id=[\"']ft[\"']", "re:class=[\"'][^\"']*footer"]},
        {"id": "contact_signal", "mode": "any", "patterns": [phone] if phone else ["re:\\d{2,4}-\\d{3,4}-\\d{4}"]},
        {"id": "login_signal", "mode": "any", "patterns": ["/wp-login.php", "로그인", "login"]},
        {
            "id": "kakao_or_quick_signal",
            "mode": "any",
            "required": False,
            "patterns": ([kakao] if kakao else []) + ["open.kakao.com", "quick", "퀵"],
        },
    ]
    co_rules = [
        {"id": "quickmenu_signal", "mode": "any", "patterns": ["quick_menu", "id=\"quicks\"", "smna-quick"]},
        {"id": "login_signal", "mode": "any", "patterns": ["/bbs/login.php", "로그인", "login"]},
        {"id": "global_banner_signal", "mode": "any", "patterns": ["smna-global-banner", "SEOULMNA GLOBAL BANNER START"]},
        {"id": "traffic_counter_signal", "mode": "any", "patterns": ["SEOULMNA TRAFFIC COUNTER START", "__smna_tc__"]},
        {"id": "footer_or_address_signal", "mode": "any", "patterns": ["주소", "대표전화", "사업자", "footer"]},
    ]

    report["site_audit"].append(_audit_site("https://seoulmna.kr/", kr_rules, timeout_sec=int(args.timeout_sec)))
    if not args.skip_co_audit:
        report["site_audit"].append(_audit_site("https://seoulmna.co.kr/", co_rules, timeout_sec=int(args.timeout_sec)))

    site_ok = all(bool(row.get("ok")) for row in report["site_audit"])
    settings_apply_ok = bool(report["actions"]["settings_apply"].get("ok", True))
    report["ok"] = bool(settings_get.get("ok")) and site_ok and settings_apply_ok

    latest_path, stamped_path = _write_reports(report, args.report)
    _save_state(
        state_path,
        {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "run_date": today_key,
            "ok": bool(report["ok"]),
            "apply_mode": bool(args.apply),
            "settings_drift_count": len(drift),
            "site_check_count": len(report["site_audit"]),
        },
    )
    print(f"[saved] {latest_path}")
    print(f"[saved] {stamped_path}")
    print(
        "[summary] "
        + f"ok={report['ok']} "
        + f"settings_drift={len(drift)} "
        + f"settings_applied={report['actions']['settings_apply'].get('attempted', False)} "
        + f"site_checks={len(report['site_audit'])}"
    )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
