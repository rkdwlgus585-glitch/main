#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THEME_JSON = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab" / "staging" / "wp-content" / "themes" / "astra" / "theme.json"
DEFAULT_STYLE_CSS = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab" / "staging" / "wp-content" / "themes" / "astra" / "style.css"
DEFAULT_FRONT_CSS = ROOT / "workspace_partitions" / "site_session" / "kr_platform_front" / "app" / "globals.css"


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
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_css_vars(text: str) -> Dict[str, str]:
    matches = re.findall(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+);", text)
    out: Dict[str, str] = {}
    for key, value in matches:
        key = key.strip()
        value = value.strip()
        if key and key not in out:
            out[key] = value
    return out


def _extract_header_field(style_css: str, name: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(style_css)
    return match.group(1).strip() if match else ""


def build_astra_design_reference(*, theme_json_path: Path, style_css_path: Path, front_css_path: Path) -> Dict[str, Any]:
    theme_json = _load_json(theme_json_path)
    style_css = _read_text(style_css_path)
    front_css = _read_text(front_css_path)
    theme_settings = theme_json.get("settings") if isinstance(theme_json.get("settings"), dict) else {}
    typography = theme_settings.get("typography") if isinstance(theme_settings.get("typography"), dict) else {}
    layout = theme_settings.get("layout") if isinstance(theme_settings.get("layout"), dict) else {}
    color = theme_settings.get("color") if isinstance(theme_settings.get("color"), dict) else {}
    front_vars = _extract_css_vars(front_css)

    font_sizes = typography.get("fontSizes") if isinstance(typography.get("fontSizes"), list) else []
    palette = color.get("palette") if isinstance(color.get("palette"), list) else []
    astra_reference = {
        "theme_name": _extract_header_field(style_css, "Theme Name") or "Astra",
        "theme_version": _extract_header_field(style_css, "Version"),
        "font_sizes": [
            {
                "slug": str(row.get("slug") or ""),
                "name": str(row.get("name") or ""),
                "size": str(row.get("size") or ""),
            }
            for row in font_sizes
            if isinstance(row, dict)
        ],
        "palette": [
            {
                "slug": str(row.get("slug") or ""),
                "name": str(row.get("name") or ""),
                "color": str(row.get("color") or ""),
            }
            for row in palette
            if isinstance(row, dict)
        ],
        "layout": {
            "contentSize": str(layout.get("contentSize") or ""),
            "wideSize": str(layout.get("wideSize") or ""),
            "fullSize": str(layout.get("fullSize") or ""),
        },
    }
    current_front = {
        "css_var_count": len(front_vars),
        "sample_vars": {key: front_vars[key] for key in list(front_vars)[:8]},
        "content_width_style_present": "min(1200px" in front_css,
    }

    suggested_actions: List[str] = []
    if astra_reference["font_sizes"]:
        suggested_actions.append("Mirror Astra's small/medium/large/x-large typography scale into the kr front type tokens, but keep the existing brand palette.")
    if astra_reference["layout"]["contentSize"] or astra_reference["layout"]["wideSize"]:
        suggested_actions.append("Adopt explicit content/wide width tokens in the kr front CSS instead of implicit page-shell widths.")
    if astra_reference["palette"]:
        suggested_actions.append("Use Astra palette taxonomy as naming inspiration only; do not import WordPress theme variables directly into the public front.")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reference_source": "astra_theme_json",
        "astra": astra_reference,
        "kr_front": current_front,
        "decision": {
            "usable_for_next_front": [
                "typography_scale_reference",
                "layout_token_reference",
                "palette_naming_reference",
            ],
            "not_usable_directly": [
                "php_templates",
                "wordpress_hooks",
                "plugin_runtime",
                "wp_theme_variables_as_live_dependencies",
            ],
            "strategy": "reference_only_for_next_front",
        },
        "suggested_actions": suggested_actions,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    astra = payload.get("astra", {})
    layout = astra.get("layout", {}) if isinstance(astra.get("layout"), dict) else {}
    lines = [
        "# Astra Design Reference",
        "",
        f"- theme_name: {astra.get('theme_name') or '(none)'}",
        f"- theme_version: {astra.get('theme_version') or '(none)'}",
        f"- font_size_count: {len(astra.get('font_sizes') or [])}",
        f"- palette_count: {len(astra.get('palette') or [])}",
        f"- content_size: {layout.get('contentSize') or '(none)'}",
        f"- wide_size: {layout.get('wideSize') or '(none)'}",
        "",
        "## Decision",
        f"- strategy: {payload.get('decision', {}).get('strategy') or '(none)'}",
        f"- usable_for_next_front: {', '.join(payload.get('decision', {}).get('usable_for_next_front') or []) or '(none)'}",
        f"- not_usable_directly: {', '.join(payload.get('decision', {}).get('not_usable_directly') or []) or '(none)'}",
        "",
        "## Suggested Actions",
    ]
    for item in payload.get("suggested_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Astra design reference tokens for the kr front.")
    parser.add_argument("--theme-json", type=Path, default=DEFAULT_THEME_JSON)
    parser.add_argument("--style-css", type=Path, default=DEFAULT_STYLE_CSS)
    parser.add_argument("--front-css", type=Path, default=DEFAULT_FRONT_CSS)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "astra_design_reference_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "astra_design_reference_latest.md")
    args = parser.parse_args()

    payload = build_astra_design_reference(
        theme_json_path=args.theme_json,
        style_css_path=args.style_css,
        front_css_path=args.front_css,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
