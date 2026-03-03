#!/usr/bin/env python3
"""Bootstrap search context inputs used by mnakr.py."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse


SEARCH_CONSOLE_HEADERS = [
    "query",
    "impressions",
    "clicks",
    "ctr",
    "position",
    "page",
    "source",
]

NAVER_HEADERS = [
    "query",
    "impressions",
    "clicks",
    "ctr",
    "position",
    "source",
]


def _read_env(path: Path) -> Tuple[List[str], Dict[str, str]]:
    if not path.exists():
        return [], {}

    lines = path.read_text(encoding="utf-8").splitlines()
    env: Dict[str, str] = {}
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return lines, env


def _write_env(path: Path, lines: List[str]) -> None:
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def _upsert_env(lines: List[str], key: str, value: str) -> bool:
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}="):
            old = line.split("=", 1)[1].strip()
            if old == value:
                return False
            lines[idx] = f"{key}={value}"
            return True
    lines.append(f"{key}={value}")
    return True


def _normalize_site_prefix(raw: str) -> str:
    src = str(raw or "").strip()
    if not src:
        return ""

    if "://" not in src:
        src = f"https://{src}"
    parsed = urlparse(src)
    if not parsed.netloc:
        return ""
    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.netloc}/"


def _infer_gsc_property(env: Dict[str, str]) -> str:
    current = str(env.get("GSC_PROPERTY_URL", "")).strip()
    if current:
        return current

    # Domain guard: infer only from WP_URL to avoid mixing blog(.kr) and listing(.co.kr).
    candidate = _normalize_site_prefix(env.get("WP_URL", ""))
    if candidate:
        return candidate
    return ""


def _ensure_csv(path: Path, headers: List[str]) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
    return True


def _check_gsc(sa_file: Path, property_url: str) -> Dict[str, object]:
    status = {
        "ok": "false",
        "reason": "",
        "service_account_email": "",
        "service_account_project_id": "",
        "accessible_sites_count": 0,
        "accessible_sites": [],
        "property_in_accessible_sites": False,
    }
    if not sa_file.exists():
        status["reason"] = f"service account file not found: {sa_file}"
        return status
    if not property_url:
        status["reason"] = "GSC_PROPERTY_URL is empty"
        return status

    try:
        sa_json = json.loads(sa_file.read_text(encoding="utf-8"))
        status["service_account_email"] = str(sa_json.get("client_email", "")).strip()
        status["service_account_project_id"] = str(sa_json.get("project_id", "")).strip()
    except Exception:
        pass

    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except Exception as exc:  # pragma: no cover
        status["reason"] = f"google api client missing: {exc}"
        return status

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(sa_file),
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        sites_res = service.sites().list().execute() or {}
        site_entries = sites_res.get("siteEntry", []) or []
        accessible_sites = sorted(
            {
                str(row.get("siteUrl", "")).strip()
                for row in site_entries
                if str(row.get("siteUrl", "")).strip()
            }
        )
        status["accessible_sites_count"] = len(accessible_sites)
        status["accessible_sites"] = accessible_sites
        status["property_in_accessible_sites"] = property_url in accessible_sites
        service.searchanalytics().query(
            siteUrl=property_url,
            body={
                "startDate": "2026-01-01",
                "endDate": "2026-01-31",
                "dimensions": ["query"],
                "rowLimit": 1,
            },
        ).execute()
        status["ok"] = "true"
        status["reason"] = "query_success"
        return status
    except Exception as exc:
        status["reason"] = str(exc)
        return status


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap search context files and env defaults."
    )
    parser.add_argument("--env", default=".env", help="Path to .env")
    parser.add_argument(
        "--check-gsc",
        action="store_true",
        help="Run a lightweight Search Console API health check",
    )
    args = parser.parse_args()

    env_path = Path(args.env).resolve()
    lines, env = _read_env(env_path)
    if not lines:
        print(json.dumps({"ok": False, "error": f".env not found: {env_path}"}, ensure_ascii=False))
        return 1

    updates = []

    property_url = _infer_gsc_property(env)
    if property_url and not str(env.get("GSC_PROPERTY_URL", "")).strip():
        if _upsert_env(lines, "GSC_PROPERTY_URL", property_url):
            updates.append(("GSC_PROPERTY_URL", property_url))
            env["GSC_PROPERTY_URL"] = property_url

    sc_path = Path(env.get("SEARCH_CONSOLE_CSV_PATH", "search_console_queries.csv"))
    naver_path = Path(env.get("NAVER_QUERY_CSV_PATH", "naver_queries.csv"))
    if not sc_path.is_absolute():
        sc_path = env_path.parent / sc_path
    if not naver_path.is_absolute():
        naver_path = env_path.parent / naver_path

    created_search_csv = _ensure_csv(sc_path, SEARCH_CONSOLE_HEADERS)
    created_naver_csv = _ensure_csv(naver_path, NAVER_HEADERS)

    if updates:
        _write_env(env_path, lines)

    result = {
        "ok": True,
        "env_path": str(env_path),
        "updates": [{"key": k, "value": v} for k, v in updates],
        "search_console_csv": str(sc_path),
        "search_console_csv_created": created_search_csv,
        "naver_csv": str(naver_path),
        "naver_csv_created": created_naver_csv,
        "gsc_check": None,
    }

    if args.check_gsc:
        sa_file = Path(env.get("GSC_SERVICE_ACCOUNT_FILE", "service_account.json"))
        if not sa_file.is_absolute():
            sa_file = env_path.parent / sa_file
        result["gsc_check"] = _check_gsc(sa_file, env.get("GSC_PROPERTY_URL", ""))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
