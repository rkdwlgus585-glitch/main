#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "logs" / "kr_proxy_server_matrix_latest.json"
DEFAULT_CHECKLIST = ROOT / "logs" / "kr_live_operator_checklist_latest.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "kr_proxy_server_bundle"
DEFAULT_JSON = ROOT / "logs" / "kr_proxy_server_bundle_latest.json"
DEFAULT_MD = ROOT / "logs" / "kr_proxy_server_bundle_latest.md"


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


def build_kr_proxy_server_bundle(*, matrix_path: Path, checklist_path: Path, output_dir: Path) -> Dict[str, Any]:
    matrix = _load_json(matrix_path)
    checklist = _load_json(checklist_path)
    summary = matrix.get("summary") if isinstance(matrix.get("summary"), dict) else {}
    nginx = matrix.get("nginx") if isinstance(matrix.get("nginx"), dict) else {}
    apache = matrix.get("apache") if isinstance(matrix.get("apache"), dict) else {}
    cloudflare = matrix.get("cloudflare") if isinstance(matrix.get("cloudflare"), dict) else {}
    wordpress_cache = matrix.get("wordpress_cache") if isinstance(matrix.get("wordpress_cache"), dict) else {}
    validation = checklist.get("validation") if isinstance(checklist.get("validation"), list) else []

    output_dir.mkdir(parents=True, exist_ok=True)

    nginx_file = output_dir / "nginx-calc-proxy.conf"
    apache_file = output_dir / "apache-calc-proxy.conf"
    cloudflare_file = output_dir / "cloudflare-cache-rules.json"
    readme_file = output_dir / "README.md"

    _write(nginx_file, str(nginx.get("snippet") or "").rstrip() + "\n")
    _write(apache_file, str(apache.get("snippet") or "").rstrip() + "\n")
    _write(cloudflare_file, json.dumps(cloudflare, ensure_ascii=False, indent=2) + "\n")

    readme_lines = [
        "# KR Proxy Server Bundle",
        "",
        f"- public_mount_path: {summary.get('public_mount_path') or '/_calc'}",
        f"- upstream_origin: {summary.get('upstream_origin') or '(none)'}",
        f"- cutover_ready: {summary.get('cutover_ready')}",
        "",
        "## Apply Order",
        "- 1. Back up the current web server and cache configuration.",
        "- 2. Apply only the nginx or apache file that matches the live server.",
        "- 3. Add a Cloudflare bypass rule for /_calc/* before traffic is sent to the upstream.",
        "- 4. Exclude /_calc/* from WordPress page-cache plugins or server-side HTML cache.",
        "- 5. Verify that the iframe is created only after a click on the .kr service pages.",
        "",
        "## Validation",
    ]
    for row in validation:
        if isinstance(row, dict):
            readme_lines.append(f"- {row.get('description')}")
    readme_lines.extend(
        [
            "",
            "## Files",
            f"- nginx: {nginx_file}",
            f"- apache: {apache_file}",
            f"- cloudflare: {cloudflare_file}",
            "",
            "## WordPress Cache Notes",
        ]
    )
    for note in wordpress_cache.get("notes") or []:
        readme_lines.append(f"- {note}")
    _write(readme_file, "\n".join(readme_lines) + "\n")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "bundle_ready": bool(summary.get("matrix_ready")),
            "public_mount_path": str(summary.get("public_mount_path") or ""),
            "upstream_origin": str(summary.get("upstream_origin") or ""),
            "output_dir": str(output_dir),
            "file_count": 4,
        },
        "files": [
            {"kind": "nginx", "path": str(nginx_file)},
            {"kind": "apache", "path": str(apache_file)},
            {"kind": "cloudflare", "path": str(cloudflare_file)},
            {"kind": "readme", "path": str(readme_file)},
        ],
        "next_actions": [
            "Apply only the nginx or apache variant that matches the production server.",
            "Create the Cloudflare bypass rule for /_calc/* before routing live requests.",
            "After deployment, verify that /yangdo and /permit only create iframe src values under .kr/_calc/*.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# KR Proxy Server Bundle",
        "",
        f"- bundle_ready: {summary.get('bundle_ready')}",
        f"- public_mount_path: {summary.get('public_mount_path') or '(none)'}",
        f"- upstream_origin: {summary.get('upstream_origin') or '(none)'}",
        f"- output_dir: {summary.get('output_dir') or '(none)'}",
        "",
        "## Files",
    ]
    for row in payload.get("files", []):
        lines.append(f"- {row.get('kind')}: {row.get('path')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate concrete .kr reverse proxy server config bundle files.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_kr_proxy_server_bundle(matrix_path=args.matrix, checklist_path=args.checklist, output_dir=args.output_dir)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("bundle_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
