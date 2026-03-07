#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONT_APP = ROOT / "workspace_partitions" / "site_session" / "kr_platform_front"
DEFAULT_THEME_HTML = ROOT / "tmp" / "adm_theme.html"
DEFAULT_SERVICE_HTML = ROOT / "tmp" / "adm_service.html"
DEFAULT_PLATFORM_AUDIT = ROOT / "logs" / "platform_front_audit_latest.json"
DEFAULT_WP_LAB = ROOT / "logs" / "wp_surface_lab_latest.json"
DEFAULT_KR_URL = "https://seoulmna.kr"
DEFAULT_CO_URL = "https://seoulmna.co.kr"

GNUBOARD_MARKERS = (
    "/bbs/",
    "g5_url",
    "gnuboard",
    "/adm/",
)

WEAVER_MARKERS = (
    "/plugin/weaver_plugin/",
    "weaver.css",
    "weaver_gnuboard.css",
)

WORDPRESS_MARKERS = (
    "/wp-content/",
    "/wp-admin/",
    "wordpress",
    "wp-json",
)

ASTRA_MARKERS = (
    "astra-theme-css",
    "/themes/astra/",
    "wp-theme-astra",
    "astra-4.",
    "wpastra.com",
)

WP_PLUGIN_MARKERS = {
    "astra": ("astra",),
    "yoast_seo": ("wordpress-seo", "yoast"),
    "rank_math": ("rank math", "seo-by-rank-math", "rank-math"),
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _contains_markers(text: str, markers: List[str] | tuple[str, ...]) -> List[str]:
    lower = (text or "").lower()
    found: List[str] = []
    for marker in markers:
        token = str(marker or "").strip().lower()
        if token and token in lower and marker not in found:
            found.append(marker)
    return found


def _fetch_html(url: str) -> Dict[str, Any]:
    target = str(url or "").strip()
    if not target:
        return {"url": "", "ok": False, "status_code": 0, "server": "", "html": "", "title": "", "error": "empty_url"}
    out: Dict[str, Any] = {"url": target, "ok": False, "status_code": 0, "server": "", "html": "", "title": "", "error": ""}
    try:
        response = requests.get(target, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        out["status_code"] = int(response.status_code)
        out["server"] = str(response.headers.get("server") or response.headers.get("Server") or "").strip()
        if getattr(response, "apparent_encoding", None):
            try:
                response.encoding = response.apparent_encoding
            except Exception:
                pass
        html = response.text or ""
        out["html"] = html
        if "<title>" in html and "</title>" in html:
            out["title"] = html.split("<title>", 1)[1].split("</title>", 1)[0].strip()
        out["ok"] = response.status_code == 200
        if response.status_code != 200:
            out["error"] = f"http_{response.status_code}"
        return out
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out


def _load_package_meta(front_app_path: Path) -> Dict[str, Any]:
    package_json = front_app_path / "package.json"
    payload = _load_json(package_json)
    deps = payload.get("dependencies") if isinstance(payload.get("dependencies"), dict) else {}
    dev_deps = payload.get("devDependencies") if isinstance(payload.get("devDependencies"), dict) else {}
    scripts = payload.get("scripts") if isinstance(payload.get("scripts"), dict) else {}
    return {
        "path": str(front_app_path),
        "exists": front_app_path.exists(),
        "next_version": str(deps.get("next") or ""),
        "react_version": str(deps.get("react") or ""),
        "typescript_version": str(dev_deps.get("typescript") or ""),
        "build_script": str(scripts.get("build") or ""),
        "vercel_config_ready": (front_app_path / "vercel.json").exists(),
        "build_artifacts_ready": (front_app_path / ".next" / "build-manifest.json").exists(),
    }


def build_surface_stack_audit(
    *,
    front_app_path: Path,
    theme_html_path: Path,
    service_html_path: Path,
    platform_audit_path: Path,
    wp_lab_path: Path,
    kr_url: str = DEFAULT_KR_URL,
    co_url: str = DEFAULT_CO_URL,
) -> Dict[str, Any]:
    theme_html = _read_text(theme_html_path)
    service_html = _read_text(service_html_path)
    live_kr = _fetch_html(kr_url)
    live_co = _fetch_html(co_url)
    kr_html = str(live_kr.get("html") or "")
    co_html = "\n".join(filter(None, [str(live_co.get("html") or ""), theme_html, service_html]))
    platform_audit = _load_json(platform_audit_path)
    wp_lab = _load_json(wp_lab_path)
    package_meta = _load_package_meta(front_app_path)

    kr_wordpress_markers = _contains_markers(kr_html, WORDPRESS_MARKERS)
    kr_astra_markers = _contains_markers(kr_html, ASTRA_MARKERS)
    kr_surface = {
        "host": "seoulmna.kr",
        "role": "live_public_site",
        "stack": (
            "wordpress_astra_live"
            if kr_wordpress_markers and kr_astra_markers
            else ("wordpress_live" if kr_wordpress_markers else "unknown")
        ),
        "evidence": {
            "server": str(live_kr.get("server") or ""),
            "title": str(live_kr.get("title") or ""),
            "wordpress_markers": kr_wordpress_markers,
            "astra_markers": kr_astra_markers,
        },
        "target_platform_stack": "nextjs_vercel_front" if package_meta["next_version"] else "",
        "target_platform_ready": bool(package_meta["build_artifacts_ready"]) and bool(package_meta["vercel_config_ready"]),
        "wordpress_applicable_live": bool(kr_wordpress_markers),
        "wordpress_reason": (
            "Live HTML contains WordPress core markers and Astra theme markers."
            if kr_wordpress_markers and kr_astra_markers
            else ("Live HTML contains WordPress core markers." if kr_wordpress_markers else "Live WordPress markers were not detected.")
        ),
    }

    gnuboard_markers = _contains_markers(co_html, GNUBOARD_MARKERS)
    weaver_markers = _contains_markers(co_html, WEAVER_MARKERS)
    wordpress_markers = _contains_markers(co_html, WORDPRESS_MARKERS)

    co_surface = {
        "host": "seoulmna.co.kr",
        "role": "listing_market_site",
        "stack": (
            "gnuboard_weaver_like"
            if gnuboard_markers or weaver_markers
            else ("wordpress_live" if wordpress_markers else "unknown")
        ),
        "evidence": {
            "server": str(live_co.get("server") or ""),
            "title": str(live_co.get("title") or ""),
            "gnuboard_markers": gnuboard_markers,
            "weaver_markers": weaver_markers,
            "wordpress_markers": wordpress_markers,
        },
        "wordpress_applicable_live": bool(wordpress_markers),
        "wordpress_reason": (
            "Live evidence contains WordPress markers."
            if wordpress_markers
            else "Current admin snapshots show GnuBoard/Weaver-style markers, not live WordPress markers."
        ),
    }

    rankmath_residue = {
        "rankmath_src_exists": (ROOT / "tmp" / "rankmath_src").exists(),
        "rankmath_export_settings_exists": (ROOT / "tmp" / "rankmath_export_settings.json").exists(),
    }

    candidate_packages = (
        wp_lab.get("packages")
        if isinstance(wp_lab.get("packages"), list)
        else []
    )
    candidate_slugs = [str(row.get("slug") or "") for row in candidate_packages if isinstance(row, dict)]

    audit = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "surfaces": {
            "kr": kr_surface,
            "co": co_surface,
            "engine": {
                "host": str((platform_audit.get("front") or {}).get("engine_origin") or ""),
                "role": "private_internal_engine",
                "public_brand_exposure_allowed": False,
            },
        },
        "wordpress": {
            "live_applicability": {
                "kr": bool(kr_wordpress_markers),
                "co": bool(wordpress_markers),
                "decision": "sandbox_only",
                "reason": "Astra/plugins can be evaluated only in an isolated WordPress lab before any live adoption decision.",
            },
            "candidate_packages_ready": bool(candidate_packages),
            "candidate_package_slugs": [slug for slug in candidate_slugs if slug],
            "local_residue": rankmath_residue,
        },
        "decisions": {
            "kr_live_stack": kr_surface["stack"],
            "kr_platform_strategy": "wordpress_live_with_next_cutover_target",
            "co_strategy": "listing_market_only",
            "plugin_theme_strategy": "wordpress_assets_sandbox_only",
            "astra_live_decision": "blocked_outside_wordpress_sandbox",
        },
        "recommended_actions": [
            "Treat current seoulmna.kr as the live WordPress/Astra surface until a cutover is explicitly executed.",
            "Use the Next.js front as the migration target for seoulmna.kr, not as the current live stack.",
            "Treat seoulmna.co.kr as the listing market site and link calculator demand back to seoulmna.kr service pages.",
            "Download Astra and SEO plugins only into the isolated WordPress lab.",
            "Do not attach WordPress theme/plugin assets to the live kr or co surfaces before sandbox validation passes.",
        ],
    }
    return audit


def _to_markdown(payload: Dict[str, Any]) -> str:
    kr = payload.get("surfaces", {}).get("kr", {})
    co = payload.get("surfaces", {}).get("co", {})
    wp = payload.get("wordpress", {})
    lines = [
        "# Surface Stack Audit",
        "",
        "## KR Surface",
        f"- host: {kr.get('host') or '(none)'}",
        f"- stack: {kr.get('stack') or '(none)'}",
        f"- server: {kr.get('evidence', {}).get('server') or '(none)'}",
        f"- title: {kr.get('evidence', {}).get('title') or '(none)'}",
        f"- wordpress_applicable_live: {kr.get('wordpress_applicable_live')}",
        f"- target_platform_stack: {kr.get('target_platform_stack') or '(none)'}",
        f"- target_platform_ready: {kr.get('target_platform_ready')}",
        f"- wordpress_markers: {', '.join(kr.get('evidence', {}).get('wordpress_markers') or []) or '(none)'}",
        f"- astra_markers: {', '.join(kr.get('evidence', {}).get('astra_markers') or []) or '(none)'}",
        f"- reason: {kr.get('wordpress_reason') or '(none)'}",
        "",
        "## CO Surface",
        f"- host: {co.get('host') or '(none)'}",
        f"- stack: {co.get('stack') or '(none)'}",
        f"- wordpress_applicable_live: {co.get('wordpress_applicable_live')}",
        f"- gnuboard_markers: {', '.join(co.get('evidence', {}).get('gnuboard_markers') or []) or '(none)'}",
        f"- weaver_markers: {', '.join(co.get('evidence', {}).get('weaver_markers') or []) or '(none)'}",
        f"- wordpress_markers: {', '.join(co.get('evidence', {}).get('wordpress_markers') or []) or '(none)'}",
        "",
        "## WordPress Sandbox Decision",
        f"- decision: {wp.get('live_applicability', {}).get('decision') or '(none)'}",
        f"- reason: {wp.get('live_applicability', {}).get('reason') or '(none)'}",
        f"- candidate_package_slugs: {', '.join(wp.get('candidate_package_slugs') or []) or '(none)'}",
        f"- local_rankmath_residue: {wp.get('local_residue', {})}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit live surface stacks and WordPress applicability.")
    parser.add_argument("--front-app", type=Path, default=DEFAULT_FRONT_APP)
    parser.add_argument("--theme-html", type=Path, default=DEFAULT_THEME_HTML)
    parser.add_argument("--service-html", type=Path, default=DEFAULT_SERVICE_HTML)
    parser.add_argument("--platform-audit", type=Path, default=DEFAULT_PLATFORM_AUDIT)
    parser.add_argument("--wp-lab", type=Path, default=DEFAULT_WP_LAB)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "surface_stack_audit_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "surface_stack_audit_latest.md")
    args = parser.parse_args()

    payload = build_surface_stack_audit(
        front_app_path=args.front_app,
        theme_html_path=args.theme_html,
        service_html_path=args.service_html,
        platform_audit_path=args.platform_audit,
        wp_lab_path=args.wp_lab,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
