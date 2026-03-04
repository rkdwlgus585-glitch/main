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


def _normalize_root_url(url: str) -> str:
    src = str(url or "").strip()
    if not src:
        return ""
    if "://" not in src:
        src = "https://" + src
    parsed = urlparse(src)
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _read_config() -> Dict[str, Any]:
    return load_config(
        {
            "WP_URL": "https://seoulmna.kr/wp-json/wp/v2",
            "WP_USER": "",
            "WP_PASSWORD": "",
            "WP_APP_PASSWORD": "",
        }
    )


def _auth_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    user = str(cfg.get("WP_USER", "")).strip()
    app_password = str(cfg.get("WP_APP_PASSWORD", "")).strip()
    password = str(cfg.get("WP_PASSWORD", "")).strip()
    pw = app_password or password
    if not (user and pw):
        raise RuntimeError("WP_USER/WP_APP_PASSWORD (or WP_PASSWORD) is required.")
    # App passwords are valid with spaces removed in Basic Auth.
    pw = re.sub(r"\s+", "", pw)
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _request_json(method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any] | None = None, timeout_sec: int = 25) -> Dict[str, Any]:
    res = requests.request(method, url, headers=headers, json=payload, timeout=max(5, int(timeout_sec)))
    out = {
        "ok": 200 <= int(res.status_code) < 300,
        "status_code": int(res.status_code),
        "text_preview": (res.text or "")[:600],
    }
    try:
        out["json"] = res.json()
    except Exception:
        out["json"] = None
    return out


def _rankmath_update_settings(
    wp_root: str,
    headers: Dict[str, str],
    section_type: str,
    settings: Dict[str, Any],
    updated_keys: List[str],
    timeout_sec: int,
) -> Dict[str, Any]:
    payload = {
        "type": section_type,
        "settings": settings,
        "fieldTypes": {},
        "updated": updated_keys,
        "isReset": False,
    }
    return _request_json(
        "POST",
        f"{wp_root}/rankmath/v1/updateSettings",
        headers,
        payload=payload,
        timeout_sec=timeout_sec,
    )


def _get_section_settings(wp_root: str, headers: Dict[str, str], section_type: str, timeout_sec: int) -> Dict[str, Any]:
    res = _rankmath_update_settings(
        wp_root=wp_root,
        headers=headers,
        section_type=section_type,
        settings={},
        updated_keys=[],
        timeout_sec=timeout_sec,
    )
    if not res.get("ok"):
        raise RuntimeError(f"RankMath {section_type} fetch failed: status={res.get('status_code')} body={res.get('text_preview')}")
    data = dict((res.get("json") or {}).get("settings") or {})
    return data


def _get_media_source_url(wp_api_root: str, headers: Dict[str, str], media_id: int, timeout_sec: int) -> str:
    res = _request_json(
        "GET",
        f"{wp_api_root}/media/{int(media_id)}",
        headers=headers,
        timeout_sec=timeout_sec,
    )
    if not res.get("ok"):
        return ""
    return str((res.get("json") or {}).get("source_url") or "").strip()


def _maybe_fix_legacy_url(setting_key: str, settings: Dict[str, Any], wp_api_root: str, headers: Dict[str, str], timeout_sec: int) -> str:
    src = str(settings.get(setting_key) or "").strip()
    if not src:
        return ""
    host = _host_of(src)
    if host in {"seoulmna.kr", "www.seoulmna.kr"}:
        return ""

    media_id_key = f"{setting_key}_id"
    media_id = settings.get(media_id_key)
    if media_id:
        resolved = _get_media_source_url(wp_api_root, headers, int(media_id), timeout_sec)
        if _host_of(resolved) in {"seoulmna.kr", "www.seoulmna.kr"}:
            return resolved
    return ""


def _write_report(report: Dict[str, Any], out_rel: str) -> Tuple[Path, Path]:
    latest = (ROOT / str(out_rel)).resolve()
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stamped = latest.with_name(f"{latest.stem}_{stamp}{latest.suffix}")
    stamped.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return latest, stamped


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply detailed RankMath settings safely via updateSettings API.")
    parser.add_argument("--dry-run", action="store_true", help="Only calculate diffs without applying changes.")
    parser.add_argument("--report", default="logs/rankmath_detail_opt_latest.json")
    parser.add_argument("--timeout-sec", type=int, default=25)
    args = parser.parse_args()

    cfg = _read_config()
    wp_api_root = str(cfg.get("WP_URL", "")).strip().rstrip("/")
    if "/wp/v2" not in wp_api_root:
        raise SystemExit("WP_URL must include '/wp/v2'.")
    wp_root = wp_api_root.split("/wp/v2")[0].rstrip("/")
    site_root = _normalize_root_url(wp_root)
    headers = _auth_headers(cfg)

    report: Dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dry_run": bool(args.dry_run),
        "wp_root": wp_root,
        "changes": [],
    }

    general_before = _get_section_settings(wp_root, headers, "general", int(args.timeout_sec))
    titles_before = _get_section_settings(wp_root, headers, "titles", int(args.timeout_sec))

    general_patch: Dict[str, Any] = {}
    titles_patch: Dict[str, Any] = {}

    # High-impact fixes:
    # 1) Breadcrumbs on for UX + SEO.
    # 2) Breadcrumb home URL must match live domain.
    if general_before.get("breadcrumbs") is not True:
        general_patch["breadcrumbs"] = True
    if str(general_before.get("breadcrumbs_home_link") or "").rstrip("/") != site_root:
        general_patch["breadcrumbs_home_link"] = site_root

    # Legacy-domain cleanup in key social/knowledge graph image fields.
    for key in ("knowledgegraph_logo", "open_graph_image"):
        fixed = _maybe_fix_legacy_url(key, titles_before, wp_api_root, headers, int(args.timeout_sec))
        if fixed:
            titles_patch[key] = fixed

    # Correct obvious token typo (%term%).
    tag_desc = str(titles_before.get("tax_post_tag_description") or "")
    if tag_desc and "term%" in tag_desc and "%term%" not in tag_desc:
        titles_patch["tax_post_tag_description"] = tag_desc.replace("term%", "%term%")

    report["planned"] = {
        "general": general_patch,
        "titles": titles_patch,
    }

    if args.dry_run:
        report["ok"] = True
        latest, stamped = _write_report(report, args.report)
        print(f"[saved] {latest}")
        print(f"[saved] {stamped}")
        print(f"[summary] dry_run=true general_changes={len(general_patch)} titles_changes={len(titles_patch)}")
        return 0

    if general_patch:
        res = _rankmath_update_settings(
            wp_root=wp_root,
            headers=headers,
            section_type="general",
            settings=general_patch,
            updated_keys=list(general_patch.keys()),
            timeout_sec=int(args.timeout_sec),
        )
        report["changes"].append(
            {
                "section": "general",
                "applied_keys": list(general_patch.keys()),
                "ok": res.get("ok", False),
                "status_code": res.get("status_code"),
                "response_preview": res.get("text_preview", ""),
            }
        )

    if titles_patch:
        res = _rankmath_update_settings(
            wp_root=wp_root,
            headers=headers,
            section_type="titles",
            settings=titles_patch,
            updated_keys=list(titles_patch.keys()),
            timeout_sec=int(args.timeout_sec),
        )
        report["changes"].append(
            {
                "section": "titles",
                "applied_keys": list(titles_patch.keys()),
                "ok": res.get("ok", False),
                "status_code": res.get("status_code"),
                "response_preview": res.get("text_preview", ""),
            }
        )

    general_after = _get_section_settings(wp_root, headers, "general", int(args.timeout_sec))
    titles_after = _get_section_settings(wp_root, headers, "titles", int(args.timeout_sec))
    report["verify"] = {
        "general": {
            "breadcrumbs": general_after.get("breadcrumbs"),
            "breadcrumbs_home_link": general_after.get("breadcrumbs_home_link"),
        },
        "titles": {
            "knowledgegraph_logo": titles_after.get("knowledgegraph_logo"),
            "open_graph_image": titles_after.get("open_graph_image"),
            "tax_post_tag_description": titles_after.get("tax_post_tag_description"),
        },
    }

    report["ok"] = all(bool(ch.get("ok")) for ch in report["changes"]) if report["changes"] else True
    latest, stamped = _write_report(report, args.report)
    print(f"[saved] {latest}")
    print(f"[saved] {stamped}")
    print(
        "[summary] "
        + f"ok={report['ok']} "
        + f"general_changes={len(general_patch)} "
        + f"titles_changes={len(titles_patch)}"
    )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
