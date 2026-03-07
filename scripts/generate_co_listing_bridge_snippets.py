#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "logs" / "listing_platform_bridge_policy_latest.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "co_listing_bridge_snippets"
DEFAULT_JSON = ROOT / "logs" / "co_listing_bridge_snippets_latest.json"
DEFAULT_MD = ROOT / "logs" / "co_listing_bridge_snippets_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _safe_slug(value: str) -> str:
    text = str(value or "").strip().lower().replace(" ", "-")
    return "".join(ch for ch in text if ch.isalnum() or ch in {"-", "_"}) or "snippet"


def _button_class(placement: str) -> str:
    if placement in {"listing_detail_primary", "listing_nav_service"}:
        return "smna-bridge-btn smna-bridge-btn--primary"
    if placement == "listing_nav_permit":
        return "smna-bridge-btn smna-bridge-btn--accent"
    return "smna-bridge-btn smna-bridge-btn--ghost"


def _build_snippet(row: Dict[str, Any]) -> str:
    placement = str(row.get("placement") or "")
    target_url = str(row.get("target_url") or "")
    copy = str(row.get("copy") or "바로가기")
    target_service = str(row.get("target_service") or "service")
    reason = str(row.get("reason") or "")
    cls = _button_class(placement)
    return (
        f'<!-- SeoulMNA bridge: {placement} -->\n'
        f'<div class="smna-bridge smna-bridge--{placement}">\n'
        f'  <a class="{cls}" href="{target_url}" '
        f'data-smna-bridge-placement="{placement}" '
        f'data-smna-target-service="{target_service}">{copy}</a>\n'
        f'  <p class="smna-bridge__reason">{reason}</p>\n'
        f'</div>\n'
    )


def build_co_listing_bridge_snippets(*, policy_path: Path, output_dir: Path) -> Dict[str, Any]:
    policy = _load_json(policy_path)
    ctas = policy.get("ctas") if isinstance(policy.get("ctas"), list) else []
    summary = policy.get("summary") if isinstance(policy.get("summary"), dict) else {}

    output_dir.mkdir(parents=True, exist_ok=True)
    files: List[Dict[str, str]] = []
    combined_parts: List[str] = []

    css = """.smna-bridge{display:flex;flex-direction:column;gap:8px;margin:14px 0}.smna-bridge__reason{margin:0;color:#5b6572;font-size:13px;line-height:1.45}.smna-bridge-btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 16px;border-radius:12px;text-decoration:none;font-weight:800;line-height:1.25}.smna-bridge-btn--primary{background:#0e3a66;color:#fff}.smna-bridge-btn--accent{background:#b8742b;color:#fff}.smna-bridge-btn--ghost{background:#f1f4f8;color:#17324a;border:1px solid #d5dce5}"""
    css_path = output_dir / "bridge-snippets.css"
    _write(css_path, css)
    files.append({"placement": "styles", "path": str(css_path)})

    for row in ctas:
        placement = str(row.get("placement") or "snippet")
        snippet = _build_snippet(row)
        path = output_dir / f"{_safe_slug(placement)}.html"
        _write(path, snippet)
        files.append({"placement": placement, "path": str(path)})
        combined_parts.append(snippet)

    combined_path = output_dir / "all-placements.html"
    _write(combined_path, "\n".join(combined_parts))
    files.append({"placement": "all", "path": str(combined_path)})

    guide_lines = [
        "# CO Listing Bridge Snippets",
        "",
        f"- listing_host: {summary.get('listing_host') or 'seoulmna.co.kr'}",
        f"- platform_host: {summary.get('platform_host') or 'seoulmna.kr'}",
        "",
        "## Apply Order",
        "- 1. 공통 CSS를 추가한다.",
        "- 2. placement에 맞는 HTML 스니펫만 넣는다.",
        "- 3. .co.kr에는 계산기를 임베드하지 않는다.",
        "- 4. 모든 링크는 .kr 서비스 페이지로만 보낸다.",
        "",
        "## Files",
    ]
    for row in files:
        guide_lines.append(f"- {row['placement']}: {row['path']}")
    guide_path = output_dir / "README.md"
    _write(guide_path, "\n".join(guide_lines) + "\n")
    files.append({"placement": "guide", "path": str(guide_path)})

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "listing_host": summary.get("listing_host") or "seoulmna.co.kr",
            "platform_host": summary.get("platform_host") or "seoulmna.kr",
            "placement_count": len(ctas),
            "snippet_file_count": len(files),
            "output_dir": str(output_dir),
            "combined_file": str(combined_path),
        },
        "files": files,
        "next_actions": [
            "Add bridge-snippets.css to the .co.kr theme or banner injection path.",
            "Insert only the placement-specific HTML snippet where needed.",
            "Keep all calculator runtime on .kr service pages and never embed tools on .co.kr.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# CO Listing Bridge Snippets",
        "",
        f"- listing_host: {summary.get('listing_host') or '(none)'}",
        f"- platform_host: {summary.get('platform_host') or '(none)'}",
        f"- placement_count: {summary.get('placement_count')}",
        f"- snippet_file_count: {summary.get('snippet_file_count')}",
        f"- output_dir: {summary.get('output_dir') or '(none)'}",
        "",
        "## Files",
    ]
    for row in payload.get("files", []):
        lines.append(f"- {row.get('placement')}: {row.get('path')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ready-to-apply .co.kr -> .kr bridge snippets from the canonical bridge policy.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_co_listing_bridge_snippets(policy_path=args.policy, output_dir=args.output_dir)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
