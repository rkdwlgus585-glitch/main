#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "logs" / "co_listing_live_injection_plan_latest.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "co_listing_injection_bundle"
DEFAULT_JSON = ROOT / "logs" / "co_listing_injection_bundle_latest.json"
DEFAULT_MD = ROOT / "logs" / "co_listing_injection_bundle_latest.md"


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


def _js_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def build_co_listing_injection_bundle(*, plan_path: Path, output_dir: Path) -> Dict[str, Any]:
    plan = _load_json(plan_path)
    placements = plan.get("placements") if isinstance(plan.get("placements"), list) else []
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = output_dir / "manifest.json"
    js_file = output_dir / "co-listing-bridge-inject.js"
    readme_file = output_dir / "README.md"

    placement_js_rows: List[str] = []
    for row in placements:
        if not isinstance(row, dict):
            continue
        placement_js_rows.append(
            "{"
            f"placement:{_js_string(row.get('placement') or '')},"
            f"selector:{_js_string(row.get('selector') or '')},"
            f"insertionMode:{_js_string(row.get('insertion_mode') or '')},"
            f"snippetFile:{_js_string(row.get('snippet_file') or '')},"
            f"targetUrl:{_js_string(row.get('target_url') or '')},"
            f"copy:{_js_string(row.get('copy') or '')}"
            "}"
        )

    js = f"""(function() {{
  const placements = [{','.join(placement_js_rows)}];
  const injected = new Set();

  function createCard(row) {{
    const wrap = document.createElement('div');
    wrap.className = 'smna-bridge smna-bridge--' + row.placement;
    const link = document.createElement('a');
    link.className = 'smna-bridge-btn smna-bridge-btn--primary';
    link.href = row.targetUrl;
    link.textContent = row.copy;
    link.setAttribute('data-smna-bridge-placement', row.placement);
    link.setAttribute('data-smna-target-service', row.placement.indexOf('permit') >= 0 ? 'permit' : 'yangdo');
    wrap.appendChild(link);
    return wrap;
  }}

  function hasDetailRows() {{
    return document.querySelectorAll('article#bo_v a[href*="seoulmna.kr"], article#bo_v .smna-bridge').length > 0
      || document.querySelector('article#bo_v .tbl_frm01.vtbl_wraps') !== null;
  }}

  function shouldSkip(row) {{
    if (row.placement === 'listing_empty_state' && hasDetailRows()) return true;
    return false;
  }}

  function injectOne(row) {{
    if (injected.has(row.placement) || shouldSkip(row)) return;
    const anchor = document.querySelector(row.selector);
    if (!anchor) return;
    const card = createCard(row);
    if (row.insertionMode === 'insert_after') {{
      anchor.insertAdjacentElement('afterend', card);
    }} else {{
      anchor.appendChild(card);
    }}
    injected.add(row.placement);
  }}

  function run() {{
    placements.forEach(injectOne);
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', run);
  }} else {{
    run();
  }}
}})();
"""

    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "placements": placements,
        "script": str(js_file),
    }

    _write(js_file, js)
    _write(manifest_file, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    _write(
        readme_file,
        "# CO Listing Injection Bundle\n\n"
        "- This bundle inserts CTA links only; it must not create calculator iframes on .co.kr.\n"
        "- Load bridge-snippets.css first, then attach the JS bundle.\n"
        "- After injection, verify that every CTA points to the correct .kr service page with UTM parameters.\n",
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "bundle_ready": bool(placements),
            "placement_count": len(placements),
            "output_dir": str(output_dir),
        },
        "files": [
            {"kind": "manifest", "path": str(manifest_file)},
            {"kind": "script", "path": str(js_file)},
            {"kind": "readme", "path": str(readme_file)},
        ],
        "next_actions": [
            "Load bridge-snippets.css first and then add the JS bundle.",
            "Verify that only CTA links are inserted and that no calculator iframe is created on .co.kr.",
            "Verify that the inserted CTAs move traffic to the correct .kr service pages.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# CO Listing Injection Bundle",
        "",
        f"- bundle_ready: {summary.get('bundle_ready')}",
        f"- placement_count: {summary.get('placement_count')}",
        f"- output_dir: {summary.get('output_dir') or '(none)'}",
        "",
        "## Files",
    ]
    for row in payload.get("files", []):
        lines.append(f"- {row.get('kind')}: {row.get('path')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a client-side injection bundle for .co.kr bridge CTA insertions.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_co_listing_injection_bundle(plan_path=args.plan, output_dir=args.output_dir)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("bundle_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
