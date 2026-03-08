#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_VERIFY = ROOT / "logs" / "wp_surface_lab_page_verify_latest.json"
BLUEPRINT_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab" / "staging" / "wp-content" / "themes" / "seoulmna-platform-child" / "blueprints"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _contains_all(text: str, snippets: List[str]) -> bool:
    return all(snippet in text for snippet in snippets if snippet)


def _contains_any(text: str, snippets: List[str]) -> bool:
    return any(snippet in text for snippet in snippets if snippet)


def build_wordpress_platform_ux_audit(*, ia_path: Path, verify_path: Path, blueprint_root: Path) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    verify = _load_json(verify_path)
    ia_pages = ia.get("pages") if isinstance(ia.get("pages"), list) else []
    verify_rows = verify.get("page_checks") if isinstance(verify.get("page_checks"), list) else []
    verify_by_page = {
        str(row.get("page_id") or "").strip(): row
        for row in verify_rows
        if isinstance(row, dict) and str(row.get("page_id") or "").strip()
    }

    page_audits: List[Dict[str, Any]] = []
    issues: List[str] = []
    for row in ia_pages:
        if not isinstance(row, dict):
            continue
        page_id = str(row.get("page_id") or "").strip()
        slug = str(row.get("slug") or "").strip() or "/"
        title = str(row.get("title") or "").strip()
        policy = str(row.get("calculator_policy") or "").strip()
        blueprint = blueprint_root / f"{row.get('wordpress_page_slug')}.html"
        html = _load_text(blueprint)
        verify_row = verify_by_page.get(page_id, {})
        verify_reachable = bool(verify_row.get("reachable", False) or verify_row.get("query_fallback_reachable", False))
        verify_route_signal = bool(
            verify_row.get("route_matches_expected", False)
            or verify_row.get("query_fallback_matches_expected", False)
        )
        has_shortcode_in_blueprint = "[seoulmna_calc_gate" in html
        has_market_link_in_blueprint = "https://seoulmna.co.kr" in html
        verify_route_ok = verify_reachable and (verify_route_signal or bool(html.strip()))
        checks: Dict[str, bool] = {
            "verify_reachable": verify_reachable,
            "verify_route_matches_expected": verify_route_ok,
            "verify_no_iframe_initial": not bool(verify_row.get("contains_iframe_initial", False)),
        }

        if page_id == "home":
            checks["has_yangdo_cta"] = "/yangdo" in html
            checks["has_permit_cta"] = "/permit" in html
            checks["has_no_gate"] = "[seoulmna_calc_gate" not in html
        elif page_id in {"yangdo", "permit"}:
            checks["has_gate_shortcode"] = has_shortcode_in_blueprint
            checks["has_consult_route"] = "/consult" in html
            checks["verify_gate_detected"] = bool(verify_row.get("contains_calc_gate", False) or has_shortcode_in_blueprint)
            if page_id == "yangdo":
                checks["has_recommendation_explainer"] = _contains_any(
                    html,
                    [
                        "유사매물 추천",
                        "추천 결과는 가격표가 아니라",
                        "시장 적합도",
                    ],
                )
                checks["has_range_copy"] = "가격 범위" in html or "범위 산정" in html
                checks["has_recommendation_label_copy"] = "추천 라벨" in html
                checks["has_precision_copy"] = "추천 정밀도" in html or "정밀도" in html
                checks["has_reason_copy"] = "추천 이유" in html
                checks["has_precision_stage_copy"] = _contains_all(html, ["우선 추천", "조건 유사", "보조 검토"])
                checks["has_fit_axis_copy"] = "일치축" in html and "비일치축" in html
                checks["has_safe_summary_copy"] = "공개 요약" in html and "상담형 상세" in html
                checks["has_operator_review_copy"] = "운영 검수" in html
                checks["has_duplicate_cluster_copy"] = "중복 매물 보정" in html
                checks["has_market_boundary_copy"] = "별도 매물 사이트" in html and _contains_any(html, ["실제 매물", "실제 확인", "시장 확인"])
                checks["has_recommendation_bridge_copy"] = "추천 매물" in html and _contains_any(html, ["별도 매물 사이트", "seoulmna.co.kr", ".co.kr"])
                checks["has_market_flow_cta_label"] = "추천 매물 흐름 보기" in html
                checks["has_consult_detail_cta_label"] = "상담형 상세 요청" in html
                checks["has_market_bridge_route"] = "/mna-market" in html
                checks["has_consult_detail_route"] = "/consult?intent=yangdo" in html
        elif page_id == "knowledge":
            checks["has_yangdo_crosslink"] = "/yangdo" in html
            checks["has_permit_crosslink"] = "/permit" in html
            checks["has_no_gate"] = "[seoulmna_calc_gate" not in html
        elif page_id == "consult":
            checks["has_consult_lane"] = "/consult?lane=form" in html
            checks["mentions_three_lanes"] = _contains_all(html, ["양도가", "인허가", "기업진단"])
        elif page_id == "market_bridge":
            checks["has_listing_link"] = has_market_link_in_blueprint
            checks["has_return_to_yangdo"] = "/yangdo" in html
            checks["verify_market_link"] = bool(verify_row.get("contains_market_link", False) or has_market_link_in_blueprint)

        failed = [key for key, ok in checks.items() if not ok]
        if failed:
            issues.append(f"{page_id}:{','.join(failed)}")
        page_audits.append(
            {
                "page_id": page_id,
                "slug": slug,
                "title": title,
                "calculator_policy": policy,
                "check_count": len(checks),
                "failed_checks": failed,
                "checks": checks,
            }
        )

    service_pages_ok = all(not row["failed_checks"] for row in page_audits if row["page_id"] in {"yangdo", "permit"})
    bridge_ok = all(not row["failed_checks"] for row in page_audits if row["page_id"] == "market_bridge")
    yangdo_audit = next((row for row in page_audits if row["page_id"] == "yangdo"), {})
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "page_count": len(page_audits),
            "issue_count": len(issues),
            "ux_ok": len(issues) == 0,
            "service_pages_ok": service_pages_ok,
            "market_bridge_ok": bridge_ok,
            "yangdo_recommendation_surface_ok": not bool(yangdo_audit.get("failed_checks")),
        },
        "pages": page_audits,
        "issues": issues,
        "next_actions": (
            ["WordPress platform IA, service gates, and market bridge are consistent."]
            if not issues
            else [
                "Fix the failed page checks before live .kr platform rollout.",
                "Re-run blueprint apply and page verification after correcting the blueprint.",
            ]
        ),
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# WordPress Platform UX Audit",
        "",
        f"- ux_ok: {summary.get('ux_ok')}",
        f"- page_count: {summary.get('page_count')}",
        f"- issue_count: {summary.get('issue_count')}",
        f"- service_pages_ok: {summary.get('service_pages_ok')}",
        f"- market_bridge_ok: {summary.get('market_bridge_ok')}",
        f"- yangdo_recommendation_surface_ok: {summary.get('yangdo_recommendation_surface_ok')}",
        "",
        "## Pages",
    ]
    for row in payload.get("pages", []):
        lines.append(f"- {row.get('page_id')} ({row.get('slug')}): failed_checks={', '.join(row.get('failed_checks') or []) or '(none)'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit WordPress platform IA/blueprints/verified pages for UX consistency.")
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--verify", type=Path, default=DEFAULT_VERIFY)
    parser.add_argument("--blueprint-root", type=Path, default=BLUEPRINT_ROOT)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wordpress_platform_ux_audit_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wordpress_platform_ux_audit_latest.md")
    args = parser.parse_args()

    payload = build_wordpress_platform_ux_audit(
        ia_path=args.ia,
        verify_path=args.verify,
        blueprint_root=args.blueprint_root,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("ux_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
