#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_JSON = ROOT / "logs" / "patent_system_brief_latest.json"
DEFAULT_MD = ROOT / "logs" / "patent_system_brief_latest.md"

from scripts.attorney_handoff_core import OFFICIAL_SOURCES, build_summary, build_track_evidence


def build_brief() -> Dict[str, object]:
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(ROOT),
        "official_sources": OFFICIAL_SOURCES,
        "tracks": build_track_evidence(),
        "summary": build_summary(),
    }


def _to_markdown(data: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Patent System Brief")
    lines.append("")
    lines.append("## Official Sources")
    for src in data.get("official_sources", []):
        lines.append(f"- {src['label']}: {src['url']} ({src['why']})")
    lines.append("")
    lines.append("## System Split")
    lines.append("- Independent systems: `yangdo`, `permit`")
    lines.append("- Shared platform: `tenant_gateway`, `channel_router`, `response_envelope`, `usage_billing`, `activation_gate`")
    lines.append("")
    for track in data.get("tracks", []):
        lines.append(f"## Track {track['track_id']} - {track['title']}")
        lines.append(f"- Scope: {track['scope']}")
        lines.append(f"- System boundary / in: {', '.join(track.get('system_boundary', {}).get('in_scope', []))}")
        lines.append(f"- System boundary / out: {', '.join(track.get('system_boundary', {}).get('out_of_scope', []))}")
        lines.append("- Core steps:")
        for step in track.get("core_steps", []):
            lines.append(f"  - {step}")
        lines.append("- Claim focus:")
        for item in track.get("claim_focus", []):
            lines.append(f"  - {item}")
        lines.append("- Avoid in claims:")
        for item in track.get("avoid_in_claims", []):
            lines.append(f"  - {item}")
        lines.append("- Commercial positioning:")
        for item in track.get("commercial_positioning", []):
            lines.append(f"  - {item}")
        draft = track.get("claim_draft_outline") if isinstance(track.get("claim_draft_outline"), dict) else {}
        lines.append(f"- Claim draft / independent: {draft.get('independent', '')}")
        lines.append("- Claim draft / dependents:")
        for item in draft.get("dependents", []):
            lines.append(f"  - {item}")
        lines.append("- Evidence:")
        for ev in track.get("evidence", []):
            lines.append(f"  - {ev['label']}: {ev['ref']}")
        lines.append("")
    lines.append("## Claim Strategy")
    for item in data.get("summary", {}).get("claim_strategy", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Attorney Handoff")
    for item in data.get("summary", {}).get("attorney_handoff", []):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate legacy-compatible patent system brief from canonical attorney handoff core")
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--md", default=str(DEFAULT_MD))
    args = parser.parse_args()

    data = build_brief()
    json_path = Path(str(args.json)).resolve()
    md_path = Path(str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(data), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "json": str(json_path),
        "md": str(md_path),
        "track_count": len(data.get("tracks", [])),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
