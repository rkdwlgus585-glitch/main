#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_RUNTIME_VALIDATION = ROOT / "logs" / "wp_surface_lab_runtime_validation_latest.json"
DEFAULT_WP_APPLY = ROOT / "logs" / "wp_surface_lab_apply_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fetch(url: str) -> Dict[str, Any]:
    last_result: Dict[str, Any] = {"ok": False, "status": 0, "body": ""}
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                body = response.read().decode("utf-8", errors="replace")
                return {
                    "ok": True,
                    "status": int(getattr(response, "status", 200) or 200),
                    "body": body,
                }
        except urllib.error.HTTPError as exc:
            last_result = {"ok": False, "status": int(exc.code), "body": exc.read().decode("utf-8", errors="replace")}
            if exc.code < 500 or attempt == 3:
                return last_result
        except Exception as exc:
            last_result = {"ok": False, "status": 0, "body": "", "error": str(exc)}
            if attempt == 3:
                return last_result
        time.sleep(0.6 * (attempt + 1))
    return last_result


def _extract_title(body: str) -> str:
    match = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def _extract_h1(body: str) -> str:
    match = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def _query_fallback_url(base_url: str, wordpress_page_slug: str) -> str:
    slug = wordpress_page_slug.strip().strip("/")
    if not slug:
        return base_url
    return f"{base_url}/?pagename={slug}"


def build_wp_surface_lab_page_verification(
    *,
    ia_path: Path,
    runtime_validation_path: Path,
    wp_apply_path: Path,
) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    runtime_validation = _load_json(runtime_validation_path)
    wp_apply = _load_json(wp_apply_path)

    handoff = runtime_validation.get("handoff") if isinstance(runtime_validation.get("handoff"), dict) else {}
    localhost_url = str(handoff.get("localhost_url") or "http://127.0.0.1:18080").rstrip("/")
    runtime_ready = bool((runtime_validation.get("summary") or {}).get("runtime_ready"))
    runtime_running = bool((runtime_validation.get("summary") or {}).get("runtime_running"))
    if runtime_ready and not runtime_running:
        live_probe = _fetch(localhost_url)
        if bool(live_probe.get("ok")):
            runtime_running = True
    pages: List[Dict[str, Any]] = []
    all_ok = True
    blockers: List[str] = []

    for row in ia.get("pages", []):
        if not isinstance(row, dict):
            continue
        public_slug = str(row.get("slug") or "/").strip() or "/"
        url = localhost_url if public_slug == "/" else f"{localhost_url}{public_slug}"
        expects_gate = str(row.get("calculator_policy") or "") == "lazy_gate_shortcode"
        expects_no_iframe = True
        check: Dict[str, Any] = {
            "page_id": str(row.get("page_id") or ""),
            "public_slug": public_slug,
            "wordpress_page_slug": str(row.get("wordpress_page_slug") or ""),
            "expected_title": str(row.get("title") or ""),
            "url": url,
            "expects_gate": expects_gate,
            "expects_no_iframe_initial": expects_no_iframe,
        }
        if runtime_running:
            fetched = _fetch(url)
            check["reachable"] = bool(fetched.get("ok"))
            check["status"] = int(fetched.get("status") or 0)
            body = str(fetched.get("body") or "")
            check["html_title"] = _extract_title(body)
            check["h1"] = _extract_h1(body)
            check["contains_iframe_initial"] = "<iframe" in body.lower()
            check["contains_calc_gate"] = "data-smna-calc-gate=\"true\"" in body
            check["contains_market_link"] = "https://seoulmna.co.kr" in body
            expected_title = str(check.get("expected_title") or "").strip()
            check["route_matches_expected"] = (
                expected_title != ""
                and (expected_title in check["html_title"] or expected_title == check["h1"])
            )
            check["query_fallback_matches_expected"] = False
            check["route_issue"] = ""
            if not check["route_matches_expected"] and check["wordpress_page_slug"]:
                fallback_url = _query_fallback_url(localhost_url, check["wordpress_page_slug"])
                check["query_fallback_url"] = fallback_url
                fallback = _fetch(fallback_url)
                fallback_body = str(fallback.get("body") or "")
                fallback_title = _extract_title(fallback_body)
                fallback_h1 = _extract_h1(fallback_body)
                check["query_fallback_reachable"] = bool(fallback.get("ok"))
                check["query_fallback_title"] = fallback_title
                check["query_fallback_h1"] = fallback_h1
                check["query_fallback_matches_expected"] = (
                    expected_title != ""
                    and bool(fallback.get("ok"))
                    and (expected_title in fallback_title or expected_title == fallback_h1)
                )
                if check["query_fallback_matches_expected"]:
                    check["route_issue"] = "pretty_permalink_mismatch"
                else:
                    check["route_issue"] = "page_content_mismatch"
            if not check["reachable"]:
                all_ok = False
            if expects_no_iframe and check["contains_iframe_initial"]:
                all_ok = False
            if expects_gate and not check["contains_calc_gate"]:
                all_ok = False
            if row.get("page_id") == "market_bridge" and not check["contains_market_link"]:
                all_ok = False
            if row.get("page_id") in {"home", "knowledge"} and check["contains_calc_gate"]:
                all_ok = False
            if not check["route_matches_expected"]:
                all_ok = False
        pages.append(check)

    if not runtime_ready:
        blockers.append("runtime_not_ready")
        all_ok = False
    elif not runtime_running:
        blockers.append("runtime_not_running")
        all_ok = False

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "verification_ready": runtime_ready,
            "verification_ok": all_ok and runtime_ready,
            "page_count": len(pages),
            "service_page_count": len([row for row in pages if row.get("expects_gate")]),
            "blockers": blockers,
            "apply_bundle_ready": bool((wp_apply.get("summary") or {}).get("bundle_ready")),
        },
        "runtime": {
            "localhost_url": localhost_url,
            "runtime_ready": runtime_ready,
        },
        "page_checks": pages,
        "next_actions": (
            ["Prepare either the Docker runtime or the PHP fallback bootstrap before HTTP verification."]
            if not runtime_ready
            else ["Start the selected local runtime before HTTP verification."]
            if not runtime_running
            else [
                "Open the homepage and confirm there is no iframe before user action.",
                "Open /yangdo and /permit and confirm the lazy gate appears before any iframe is created.",
            ]
        ),
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    lines = [
        "# WordPress Surface Lab Page Verification",
        "",
        f"- verification_ready: {summary.get('verification_ready')}",
        f"- verification_ok: {summary.get('verification_ok')}",
        f"- localhost_url: {runtime.get('localhost_url') or '(none)'}",
        f"- blockers: {', '.join(summary.get('blockers') or []) or '(none)'}",
        "",
        "## Page Checks",
    ]
    for row in payload.get("page_checks", []):
        lines.append(
            f"- {row.get('public_slug')} gate={row.get('expects_gate')} iframe_initial={row.get('contains_iframe_initial', '(n/a)')} reachable={row.get('reachable', '(n/a)')}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the local WordPress surface lab pages after blueprint apply.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--runtime-validation", type=Path, default=DEFAULT_RUNTIME_VALIDATION)
    parser.add_argument("--wp-apply", type=Path, default=DEFAULT_WP_APPLY)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_page_verify_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_page_verify_latest.md")
    args = parser.parse_args()

    payload = build_wp_surface_lab_page_verification(
        ia_path=args.ia,
        runtime_validation_path=args.runtime_validation,
        wp_apply_path=args.wp_apply,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if not payload.get("summary", {}).get("blockers") else 0


if __name__ == "__main__":
    raise SystemExit(main())
