#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OBSERVABILITY_INPUT = ROOT / "logs" / "permit_partner_binding_observability_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_partner_gap_preview_digest_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_partner_gap_preview_digest_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def build_digest(*, observability_report: Dict[str, Any]) -> Dict[str, Any]:
    summary = _safe_dict(observability_report.get("summary"))
    rows = [_safe_dict(row) for row in _safe_list(observability_report.get("families")) if _safe_dict(row)]

    widget_missing_preview = [
        _safe_dict(row) for row in _safe_list(observability_report.get("widget_missing_preview")) if _safe_dict(row)
    ]
    api_missing_preview = [
        _safe_dict(row) for row in _safe_list(observability_report.get("api_missing_preview")) if _safe_dict(row)
    ]
    widget_extra_claim_ids = sorted(
        _safe_str(item) for item in _safe_list(observability_report.get("widget_extra_claim_ids")) if _safe_str(item)
    )
    api_extra_claim_ids = sorted(
        _safe_str(item) for item in _safe_list(observability_report.get("api_extra_claim_ids")) if _safe_str(item)
    )

    blank_binding_preset_rows: List[Dict[str, Any]] = []
    widget_preset_mismatch_rows: List[Dict[str, Any]] = []
    api_preset_mismatch_rows: List[Dict[str, Any]] = []
    manual_review_binding_total = 0

    for row in rows:
        expected_preset_id = _safe_str(row.get("binding_preset_id"))
        widget_preset_id = _safe_str(row.get("widget_binding_preset_id"))
        api_preset_id = _safe_str(row.get("api_binding_preset_id"))
        if bool(row.get("manual_review_expected")):
            manual_review_binding_total += 1
        if not expected_preset_id:
            blank_binding_preset_rows.append(
                {
                    "claim_id": _safe_str(row.get("claim_id")),
                    "family_key": _safe_str(row.get("family_key")),
                    "service_code": _safe_str(row.get("service_code")),
                    "review_reason": _safe_str(row.get("review_reason")),
                }
            )
        if expected_preset_id and widget_preset_id and widget_preset_id != expected_preset_id:
            widget_preset_mismatch_rows.append(
                {
                    "claim_id": _safe_str(row.get("claim_id")),
                    "family_key": _safe_str(row.get("family_key")),
                    "expected_binding_preset_id": expected_preset_id,
                    "actual_binding_preset_id": widget_preset_id,
                }
            )
        if expected_preset_id and api_preset_id and api_preset_id != expected_preset_id:
            api_preset_mismatch_rows.append(
                {
                    "claim_id": _safe_str(row.get("claim_id")),
                    "family_key": _safe_str(row.get("family_key")),
                    "expected_binding_preset_id": expected_preset_id,
                    "actual_binding_preset_id": api_preset_id,
                }
            )

    digest_ready = all(
        [
            bool(summary.get("observability_ready", False)),
            not blank_binding_preset_rows,
            not widget_preset_mismatch_rows,
            not api_preset_mismatch_rows,
            not widget_missing_preview,
            not api_missing_preview,
            not widget_extra_claim_ids,
            not api_extra_claim_ids,
        ]
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "digest_ready": digest_ready,
            "expected_family_total": int(summary.get("expected_family_total", 0) or 0),
            "manual_review_binding_total": manual_review_binding_total,
            "blank_binding_preset_total": len(blank_binding_preset_rows),
            "widget_missing_family_total": len(widget_missing_preview),
            "api_missing_family_total": len(api_missing_preview),
            "widget_extra_family_total": len(widget_extra_claim_ids),
            "api_extra_family_total": len(api_extra_claim_ids),
            "widget_preset_mismatch_total": len(widget_preset_mismatch_rows),
            "api_preset_mismatch_total": len(api_preset_mismatch_rows),
        },
        "blank_binding_preset_preview": blank_binding_preset_rows[:5],
        "widget_missing_preview": widget_missing_preview[:5],
        "api_missing_preview": api_missing_preview[:5],
        "widget_extra_claim_ids": widget_extra_claim_ids[:5],
        "api_extra_claim_ids": api_extra_claim_ids[:5],
        "widget_preset_mismatch_preview": widget_preset_mismatch_rows[:5],
        "api_preset_mismatch_preview": api_preset_mismatch_rows[:5],
        "source_paths": {
            "partner_binding_observability": str(DEFAULT_OBSERVABILITY_INPUT.resolve()),
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = _safe_dict(report.get("summary"))
    lines = [
        "# Permit Partner Gap Preview Digest",
        "",
        "## Summary",
        f"- digest_ready: `{summary.get('digest_ready', False)}`",
        f"- expected_family_total: `{summary.get('expected_family_total', 0)}`",
        f"- manual_review_binding_total: `{summary.get('manual_review_binding_total', 0)}`",
        f"- blank_binding_preset_total: `{summary.get('blank_binding_preset_total', 0)}`",
        f"- widget_missing_family_total: `{summary.get('widget_missing_family_total', 0)}`",
        f"- api_missing_family_total: `{summary.get('api_missing_family_total', 0)}`",
        f"- widget_extra_family_total: `{summary.get('widget_extra_family_total', 0)}`",
        f"- api_extra_family_total: `{summary.get('api_extra_family_total', 0)}`",
        f"- widget_preset_mismatch_total: `{summary.get('widget_preset_mismatch_total', 0)}`",
        f"- api_preset_mismatch_total: `{summary.get('api_preset_mismatch_total', 0)}`",
    ]
    for section, rows in (
        ("Blank Binding Preset Preview", _safe_list(report.get("blank_binding_preset_preview"))),
        ("Widget Missing Preview", _safe_list(report.get("widget_missing_preview"))),
        ("API Missing Preview", _safe_list(report.get("api_missing_preview"))),
        ("Widget Preset Mismatch Preview", _safe_list(report.get("widget_preset_mismatch_preview"))),
        ("API Preset Mismatch Preview", _safe_list(report.get("api_preset_mismatch_preview"))),
    ):
        clean_rows = [_safe_dict(row) for row in rows if _safe_dict(row)]
        if not clean_rows:
            continue
        lines.extend(["", f"## {section}"])
        for row in clean_rows:
            bits = [f"`{_safe_str(row.get('claim_id'))}`"]
            if _safe_str(row.get("family_key")):
                bits.append(_safe_str(row.get("family_key")))
            if _safe_str(row.get("service_code")):
                bits.append(f"service={_safe_str(row.get('service_code'))}")
            if _safe_str(row.get("expected_binding_preset_id")):
                bits.append(f"expected={_safe_str(row.get('expected_binding_preset_id'))}")
            if _safe_str(row.get("actual_binding_preset_id")):
                bits.append(f"actual={_safe_str(row.get('actual_binding_preset_id'))}")
            lines.append(f"- {' / '.join(bits)}")
    if _safe_list(report.get("widget_extra_claim_ids")):
        lines.extend(["", "## Widget Extra Claim IDs"])
        for item in _safe_list(report.get("widget_extra_claim_ids")):
            lines.append(f"- `{_safe_str(item)}`")
    if _safe_list(report.get("api_extra_claim_ids")):
        lines.extend(["", "## API Extra Claim IDs"])
        for item in _safe_list(report.get("api_extra_claim_ids")):
            lines.append(f"- `{_safe_str(item)}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact partner gap preview digest for permit bindings.")
    parser.add_argument("--observability-input", type=Path, default=DEFAULT_OBSERVABILITY_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_digest(observability_report=_load_json(args.observability_input.resolve()))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "json": str(args.json_output.resolve()), "md": str(args.md_output.resolve())},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bool(_safe_dict(report.get("summary")).get("digest_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
