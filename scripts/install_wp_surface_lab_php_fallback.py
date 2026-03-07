#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / "logs" / "wp_surface_lab_runtime_latest.json"
DEFAULT_PHP_FALLBACK = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _http_open(opener: urllib.request.OpenerDirector, url: str, *, data: Dict[str, str] | None = None) -> str:
    encoded = None
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=encoded)
    with opener.open(request, timeout=10) as response:
        return response.read().decode("utf-8", errors="replace")


def _default_password(value: str) -> str:
    text = str(value or "").strip()
    if not text or text == "change-me-before-sharing":
        return "Codex!Lab2026#Ready"
    return text


def build_wp_surface_lab_php_install(*, runtime_path: Path, php_fallback_path: Path) -> Dict[str, Any]:
    runtime = _load_json(runtime_path)
    php_fallback = _load_json(php_fallback_path)

    runtime_root = Path(str(runtime.get("runtime_root") or ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab" / "runtime"))
    env = _load_env_file(runtime_root / ".env.local")
    site_url = str(
        (
            php_fallback.get("site_url")
            or (php_fallback.get("commands") or {}).get("install_url")
            or "http://127.0.0.1:18081/wp-admin/install.php"
        )
    ).replace("/wp-admin/install.php", "").rstrip("/")
    install_url = f"{site_url}/wp-admin/install.php"
    admin_user = str(env.get("WP_ADMIN_USER") or "admin")
    admin_password = _default_password(env.get("WP_ADMIN_PASSWORD") or "")
    admin_email = str(env.get("WP_ADMIN_EMAIL") or "lab@example.com")
    site_title = str(env.get("WP_SITE_TITLE") or "SeoulMNA Platform Lab")

    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    install_page = _http_open(opener, install_url)
    already_installed = any(
        token in install_page for token in ("이미 설치되었습니다", "이미 설치됨", "Already Installed", "wp-login.php")
    ) and "환영합니다" not in install_page
    if already_installed:
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "site_url": site_url,
            "summary": {
                "attempted": False,
                "already_installed": True,
                "install_ok": True,
            },
            "credentials": {
                "admin_user": admin_user,
                "admin_password": admin_password,
                "admin_email": admin_email,
            },
            "next_actions": [
                "Run the apply bundle against the installed local WordPress instance.",
                "Proceed to page verification while keeping the runtime bound to 127.0.0.1 only.",
            ],
        }

    if "language" in install_page and "step=1" in install_page:
        _http_open(opener, f"{install_url}?step=1", data={"language": "ko_KR"})

    response = _http_open(
        opener,
        f"{install_url}?step=2",
        data={
            "weblog_title": site_title,
            "user_name": admin_user,
            "admin_password": admin_password,
            "admin_password2": admin_password,
            "admin_email": admin_email,
            "blog_public": "0",
            "language": "ko_KR",
            "Submit": "워드프레스 설치",
        },
    )
    install_ok = ("성공!" in response) or ("Success!" in response) or bool(re.search(r"wp-login\.php", response))

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "site_url": site_url,
        "summary": {
            "attempted": True,
            "already_installed": False,
            "install_ok": install_ok,
        },
        "credentials": {
            "admin_user": admin_user,
            "admin_password": admin_password,
            "admin_email": admin_email,
        },
        "next_actions": [
            "Run the apply bundle against the installed local WordPress instance.",
            "Proceed to page verification while keeping the runtime bound to 127.0.0.1 only.",
        ],
        "response_excerpt": response[:400],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    creds = payload.get("credentials") if isinstance(payload.get("credentials"), dict) else {}
    lines = [
        "# WordPress Surface Lab PHP Install",
        "",
        f"- site_url: {payload.get('site_url') or '(none)'}",
        f"- attempted: {summary.get('attempted')}",
        f"- already_installed: {summary.get('already_installed')}",
        f"- install_ok: {summary.get('install_ok')}",
        f"- admin_user: {creds.get('admin_user') or '(none)'}",
        f"- admin_email: {creds.get('admin_email') or '(none)'}",
        "",
        "## Next Actions",
    ]
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the local WordPress surface lab over the PHP fallback runtime.")
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--php-fallback", type=Path, default=DEFAULT_PHP_FALLBACK)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_php_install_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_php_install_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab_php_install(runtime_path=args.runtime, php_fallback_path=args.php_fallback)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("install_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
