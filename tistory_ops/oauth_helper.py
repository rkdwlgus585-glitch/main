from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import load_config, require_config

CONFIG = load_config(
    {
        "TISTORY_OAUTH_BASE": "https://www.tistory.com/oauth",
        "TISTORY_APP_ID": "",
        "TISTORY_APP_SECRET": "",
        "TISTORY_REDIRECT_URI": "",
    }
)


def build_authorize_url(app_id: str, redirect_uri: str, state: str = "") -> str:
    query = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }
    if str(state or "").strip():
        query["state"] = str(state).strip()
    base = str(CONFIG.get("TISTORY_OAUTH_BASE", "https://www.tistory.com/oauth")).rstrip("/")
    return f"{base}/authorize?{urlencode(query)}"


def exchange_code_for_token(app_id: str, app_secret: str, redirect_uri: str, code: str) -> str:
    base = str(CONFIG.get("TISTORY_OAUTH_BASE", "https://www.tistory.com/oauth")).rstrip("/")
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
    }
    resp = requests.get(f"{base}/access_token", params=params, timeout=20)
    if resp.status_code >= 400:
        raise RuntimeError(f"token exchange failed: status={resp.status_code}, body={resp.text[:500]}")
    token = str(resp.text or "").strip()
    if not token:
        raise RuntimeError("token exchange failed: empty token response")
    if token.startswith("{"):
        # Some flows may return JSON error payload.
        try:
            payload = json.loads(token)
            raise RuntimeError(f"token exchange failed: {payload}")
        except Exception:
            pass
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Tistory OAuth helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("authorize-url", help="print OAuth authorize URL")
    p_auth.add_argument("--state", default="", help="optional state value")

    p_token = sub.add_parser("exchange-code", help="exchange auth code for access token")
    p_token.add_argument("--code", required=True, help="authorization code")

    args = parser.parse_args()

    app_id = str(CONFIG.get("TISTORY_APP_ID", "")).strip()
    app_secret = str(CONFIG.get("TISTORY_APP_SECRET", "")).strip()
    redirect_uri = str(CONFIG.get("TISTORY_REDIRECT_URI", "")).strip()

    if args.command == "authorize-url":
        require_config(
            {"TISTORY_APP_ID": app_id, "TISTORY_REDIRECT_URI": redirect_uri},
            ["TISTORY_APP_ID", "TISTORY_REDIRECT_URI"],
            context="tistory-oauth",
        )
        state = str(args.state or "").strip() or secrets.token_hex(8)
        url = build_authorize_url(app_id, redirect_uri, state=state)
        print(json.dumps({"authorize_url": url, "state": state}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "exchange-code":
        require_config(
            {
                "TISTORY_APP_ID": app_id,
                "TISTORY_APP_SECRET": app_secret,
                "TISTORY_REDIRECT_URI": redirect_uri,
            },
            ["TISTORY_APP_ID", "TISTORY_APP_SECRET", "TISTORY_REDIRECT_URI"],
            context="tistory-oauth",
        )
        token = exchange_code_for_token(app_id, app_secret, redirect_uri, code=args.code)
        print(json.dumps({"access_token": token}, ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

