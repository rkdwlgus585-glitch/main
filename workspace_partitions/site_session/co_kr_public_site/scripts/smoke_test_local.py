#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "imported"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def first_id(filename: str) -> str:
    payload = load_json(DATA_DIR / filename)
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"No records found in {filename}")
    first = payload[0]
    if not isinstance(first, dict) or not str(first.get("id", "")).strip():
        raise RuntimeError(f"First record in {filename} does not have an id")
    return str(first["id"]).strip()


def build_routes() -> list[str]:
    return [
        "/",
        "/archive",
        "/mna",
        f"/mna/{first_id('listing-sheet-rows.json')}",
        f"/notice/{first_id('notice-posts.json')}",
        f"/premium/{first_id('premium-posts.json')}",
        "/support",
        "/registration",
    ]


def fetch_route(base_url: str, route: str, timeout_sec: int) -> dict[str, Any]:
    response = requests.get(f"{base_url}{route}", timeout=timeout_sec)
    soup = BeautifulSoup(response.text, "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    h1 = soup.find("h1")
    h1_text = h1.get_text(" ", strip=True) if h1 else ""
    return {
        "route": route,
        "status": response.status_code,
        "title": title,
        "h1": h1_text,
        "ok": response.status_code == 200,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test the co_kr_public_site local server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--timeout-sec", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = str(args.base_url or "").rstrip("/")
    if not base_url:
        raise SystemExit("Base URL is required")

    results = [fetch_route(base_url, route, max(10, int(args.timeout_sec or 90))) for route in build_routes()]
    failed = [item for item in results if not item["ok"]]

    print(
        json.dumps(
            {
                "baseUrl": base_url,
                "results": results,
                "ok": not failed,
                "failedRoutes": [item["route"] for item in failed],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
