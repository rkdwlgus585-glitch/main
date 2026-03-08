#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "logs" / "listing_platform_bridge_policy_latest.json"
DEFAULT_SNIPPETS = ROOT / "logs" / "co_listing_bridge_snippets_latest.json"
DEFAULT_OPERATOR = ROOT / "logs" / "co_listing_bridge_operator_checklist_latest.json"
DEFAULT_HOME_HTML = ROOT / "tmp" / "live_seoulmna_co_kr.html"
DEFAULT_LIST_HTML = ROOT / "tmp" / "live_seoulmna_co_kr_mna.html"
DEFAULT_DETAIL_HTML = ROOT / "tmp" / "live_seoulmna_co_kr_mna_detail_7768.html"
DEFAULT_JSON = ROOT / "logs" / "co_listing_live_injection_plan_latest.json"
DEFAULT_MD = ROOT / "logs" / "co_listing_live_injection_plan_latest.md"

PLACEMENT_RULES: Dict[str, Dict[str, str]] = {
    "listing_nav_service": {
        "selector": "header#header ul.gnb",
        "mode": "append_nav_item",
        "source": "home",
    },
    "listing_nav_permit": {
        "selector": "header#header ul.gnb",
        "mode": "append_nav_item",
        "source": "home",
    },
    "listing_detail_primary": {
        "selector": "article#bo_v .tbl_frm01.vtbl_wraps",
        "mode": "insert_after",
        "source": "detail",
    },
    "listing_detail_secondary": {
        "selector": "article#bo_v .bo_v_innr",
        "mode": "append_after_primary_block",
        "source": "detail",
    },
    "listing_empty_state": {
        "selector": "#bo_list .bo_list_innr",
        "mode": "render_when_no_detail_rows",
        "source": "list",
    },
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
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _selector_present(source_text: str, selector: str) -> bool:
    selector_map = {
        "header#header ul.gnb": 'class="gnb"',
        "#bo_list .bo_list_innr": 'id="bo_list"',
        "article#bo_v .tbl_frm01.vtbl_wraps": 'class="tbl_frm01 vtbl_wraps"',
        "article#bo_v .bo_v_innr": 'class="bo_v_innr"',
    }
    marker = selector_map.get(selector, "")
    return bool(marker and marker in source_text)


def build_co_listing_live_injection_plan(
    *,
    policy_path: Path,
    snippets_path: Path,
    operator_path: Path,
    home_html_path: Path,
    list_html_path: Path,
    detail_html_path: Path,
) -> Dict[str, Any]:
    policy = _load_json(policy_path)
    snippets = _load_json(snippets_path)
    operator = _load_json(operator_path)
    home_html = _read_text(home_html_path)
    list_html = _read_text(list_html_path)
    detail_html = _read_text(detail_html_path)

    snippet_files = {
        str(row.get("placement") or "").strip(): str(row.get("path") or "").strip()
        for row in (snippets.get("files") or [])
        if isinstance(row, dict)
    }
    ctas = policy.get("ctas") if isinstance(policy.get("ctas"), list) else []
    operator_ready = bool((operator.get("summary") or {}).get("checklist_ready"))

    placements: List[Dict[str, Any]] = []
    for row in ctas:
        if not isinstance(row, dict):
            continue
        placement = str(row.get("placement") or "").strip()
        rule = PLACEMENT_RULES.get(placement, {})
        selector = rule.get("selector", "")
        source = rule.get("source", "")
        source_text = home_html if source == "home" else detail_html if source == "detail" else list_html
        placements.append(
            {
                "placement": placement,
                "selector": selector,
                "insertion_mode": rule.get("mode", ""),
                "source_page": source,
                "selector_verified": _selector_present(source_text, selector),
                "snippet_file": snippet_files.get(placement, ""),
                "target_url": str(row.get("target_url") or ""),
                "copy": str(row.get("copy") or ""),
            }
        )

    verified_count = len([row for row in placements if row.get("selector_verified")])
    snippet_ready_count = len(
        [
            row
            for row in placements
            if str(row.get("snippet_file") or "").strip() and str(row.get("target_url") or "").strip()
        ]
    )
    artifact_ready = bool(placements) and operator_ready and snippet_ready_count == len(placements)
    strict_live_ready = artifact_ready and verified_count == len(placements)
    detail_sample_url = ""
    if "https://seoulmna.co.kr/mna/7768" in detail_html or 'id="bo_v"' in detail_html:
        detail_sample_url = "https://seoulmna.co.kr/mna/7768"

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "listing_host": str((policy.get("summary") or {}).get("listing_host") or "seoulmna.co.kr"),
            "platform_host": str((policy.get("summary") or {}).get("platform_host") or "seoulmna.kr"),
            "placement_count": len(placements),
            "selector_verified_count": verified_count,
            "snippet_ready_count": snippet_ready_count,
            "operator_ready": operator_ready,
            "artifact_ready": artifact_ready,
            "strict_live_ready": strict_live_ready,
            "plan_ready": artifact_ready,
            "detail_sample_url": detail_sample_url,
        },
        "placements": placements,
        "notes": [
            "Global navigation insertions are anchored to header#header ul.gnb.",
            "Detail-page CTAs are inserted only inside the verified article#bo_v area.",
            "The empty-state CTA is rendered only when list markup is present and detail markup is absent.",
            "All links point back to seoulmna.kr service pages; no calculator iframe is created on seoulmna.co.kr.",
        ],
        "next_actions": [
            "Match each verified selector to its placement-specific snippet or JS injection entry.",
            "Verify that every CTA points to the correct .kr URL with the required UTM parameters.",
            "Confirm that no /_calc iframe is created anywhere in the .co.kr DOM before publishing.",
            "Treat selector verification as a strict live-apply gate, not a canonical artifact refresh blocker.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# CO Listing Live Injection Plan",
        "",
        f"- listing_host: {summary.get('listing_host') or '(none)'}",
        f"- platform_host: {summary.get('platform_host') or '(none)'}",
        f"- placement_count: {summary.get('placement_count')}",
        f"- selector_verified_count: {summary.get('selector_verified_count')}",
        f"- snippet_ready_count: {summary.get('snippet_ready_count')}",
        f"- operator_ready: {summary.get('operator_ready')}",
        f"- artifact_ready: {summary.get('artifact_ready')}",
        f"- strict_live_ready: {summary.get('strict_live_ready')}",
        f"- plan_ready: {summary.get('plan_ready')}",
        f"- detail_sample_url: {summary.get('detail_sample_url') or '(none)'}",
        "",
        "## Placements",
    ]
    for row in payload.get("placements", []):
        lines.append(f"- {row.get('placement')}: selector={row.get('selector')} verified={row.get('selector_verified')}")
        lines.append(f"  - insertion_mode: {row.get('insertion_mode')}")
        lines.append(f"  - snippet_file: {row.get('snippet_file')}")
        lines.append(f"  - target_url: {row.get('target_url')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a selector-level live insertion plan for .co.kr -> .kr bridge placements.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--snippets", type=Path, default=DEFAULT_SNIPPETS)
    parser.add_argument("--operator", type=Path, default=DEFAULT_OPERATOR)
    parser.add_argument("--home-html", type=Path, default=DEFAULT_HOME_HTML)
    parser.add_argument("--list-html", type=Path, default=DEFAULT_LIST_HTML)
    parser.add_argument("--detail-html", type=Path, default=DEFAULT_DETAIL_HTML)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--strict", action="store_true", help="Fail unless all selectors are verified for live apply.")
    args = parser.parse_args()

    payload = build_co_listing_live_injection_plan(
        policy_path=args.policy,
        snippets_path=args.snippets,
        operator_path=args.operator,
        home_html_path=args.home_html,
        list_html_path=args.list_html,
        detail_html_path=args.detail_html,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    ready_flag = bool(summary.get("strict_live_ready")) if args.strict else bool(summary.get("plan_ready"))
    return 0 if ready_flag else 1


if __name__ == "__main__":
    raise SystemExit(main())
