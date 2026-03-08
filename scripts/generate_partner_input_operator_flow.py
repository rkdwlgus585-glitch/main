#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / 'logs' / 'partner_input_handoff_packet_latest.json'
DEFAULT_JSON = ROOT / 'logs' / 'partner_input_operator_flow_latest.json'
DEFAULT_MD = ROOT / 'logs' / 'partner_input_operator_flow_latest.md'


def _load_json(path: Path | None) -> Dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _quote(value: str) -> str:
    text = str(value or '').strip()
    if not text:
        return '""'
    return '"' + text.replace('"', '\\"') + '"'


def _extract_value(line: str, prefix: str) -> str:
    text = str(line or '').strip()
    return text.replace(prefix, '', 1) if text.startswith(prefix) else text


def _build_simulate_command(row: Dict[str, Any]) -> str:
    cp = row.get('copy_paste_packet') if isinstance(row.get('copy_paste_packet'), dict) else {}
    proof_url = _extract_value(str(cp.get('proof_url_field') or ''), 'proof_url=')
    return ' '.join([
        'py -3 scripts/simulate_partner_input_injection.py',
        f'--offering-id {_quote(str(row.get("offering_id") or ""))}',
        f'--tenant-id {_quote(str(row.get("tenant_id") or ""))}',
        f'--channel-id {_quote(str(row.get("channel_id") or ""))}',
        f'--host {_quote(str(row.get("host") or ""))}',
        f'--brand-name {_quote(str(row.get("brand_name") or ""))}',
        f'--proof-url {_quote(proof_url)}',
        '--api-key-value "<issued-secret>"',
        '--approve-source',
    ])


def _build_onboarding_command(row: Dict[str, Any], *, apply: bool) -> str:
    cp = row.get('copy_paste_packet') if isinstance(row.get('copy_paste_packet'), dict) else {}
    proof_url = _extract_value(str(cp.get('proof_url_field') or ''), 'proof_url=')
    api_env_line = str(cp.get('api_key_env_line') or '')
    api_env = api_env_line.split('=', 1)[0].strip() if '=' in api_env_line else api_env_line.strip()
    source_line = str(cp.get('source_id_line') or '')
    source_id = source_line.split('=', 1)[1].strip() if '=' in source_line else source_line.strip()
    parts = [
        'py -3 scripts/run_partner_onboarding_flow.py',
        f'--offering-id {_quote(str(row.get("offering_id") or ""))}',
        f'--tenant-id {_quote(str(row.get("tenant_id") or ""))}',
        f'--channel-id {_quote(str(row.get("channel_id") or ""))}',
        f'--host {_quote(str(row.get("host") or ""))}',
        f'--brand-name {_quote(str(row.get("brand_name") or ""))}',
        f'--proof-url {_quote(proof_url)}',
        f'--source-id {_quote(source_id or "partner_source_placeholder")}',
        '--approve-source',
        f'--api-key-env {_quote(api_env or "TENANT_API_KEY_PARTNER")}',
        '--api-key-value "<issued-secret>"',
        '--run-smoke-in-dry-run',
    ]
    if apply:
        parts.append('--apply')
    return ' '.join(parts)


def build_partner_input_operator_flow(*, handoff_path: Path) -> Dict[str, Any]:
    handoff = _load_json(handoff_path)
    handoff_summary = handoff.get('summary') if isinstance(handoff.get('summary'), dict) else {}
    partners = handoff.get('partners') if isinstance(handoff.get('partners'), list) else []

    rows: List[Dict[str, Any]] = []
    for row in partners:
        if not isinstance(row, dict):
            continue
        rows.append({
            'tenant_id': str(row.get('tenant_id') or ''),
            'channel_id': str(row.get('channel_id') or ''),
            'offering_id': str(row.get('offering_id') or ''),
            'host': str(row.get('host') or ''),
            'brand_name': str(row.get('brand_name') or ''),
            'required_inputs': list(row.get('required_inputs') or []),
            'copy_paste_packet': row.get('copy_paste_packet') if isinstance(row.get('copy_paste_packet'), dict) else {},
            'simulated_decision_after_injection': str(row.get('simulated_decision_after_injection') or ''),
            'simulate_command': _build_simulate_command(row),
            'dry_run_command': _build_onboarding_command(row, apply=False),
            'apply_command': _build_onboarding_command(row, apply=True),
        })

    packet_ready = bool(handoff_summary.get('partner_count')) and bool(handoff_summary.get('copy_paste_ready'))
    ready_after_recommended_injection = bool(handoff_summary.get('ready_after_recommended_injection'))
    payload = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'packet_ready': packet_ready,
            'operator_flow_ready': packet_ready,
            'partner_count': int(handoff_summary.get('partner_count', 0) or 0),
            'common_required_inputs': list(handoff_summary.get('common_required_inputs') or []),
            'copy_paste_ready': bool(handoff_summary.get('copy_paste_ready')),
            'ready_after_recommended_injection': ready_after_recommended_injection,
            'ready_after_recommended_injection_count': int(handoff_summary.get('ready_after_recommended_injection_count', 0) or 0),
            'partner_activation_decision': 'ready_for_operator_injection' if ready_after_recommended_injection else 'awaiting_partner_inputs',
            'recommended_sequence': [
                'simulate_partner_input_injection',
                'run_partner_onboarding_flow_dry_run',
                'run_partner_onboarding_flow_apply',
            ],
        },
        'partners': rows,
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    lines = [
        '# Partner Input Operator Flow',
        '',
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- operator_flow_ready: {summary.get('operator_flow_ready')}",
        f"- partner_count: {summary.get('partner_count')}",
        f"- common_required_inputs: {', '.join(summary.get('common_required_inputs') or []) or '(none)'}",
        f"- copy_paste_ready: {summary.get('copy_paste_ready')}",
        f"- ready_after_recommended_injection: {summary.get('ready_after_recommended_injection')}",
        f"- partner_activation_decision: {summary.get('partner_activation_decision')}",
        '',
        '## Recommended Sequence',
    ]
    for step in summary.get('recommended_sequence') or []:
        lines.append(f'- {step}')
    lines.extend(['', '## Partners'])
    for row in payload.get('partners') or []:
        if not isinstance(row, dict):
            continue
        lines.append(f"- {row.get('tenant_id')} / {row.get('offering_id')} / {row.get('host')}")
        lines.append(f"  - simulate: {row.get('simulate_command')}")
        lines.append(f"  - dry_run: {row.get('dry_run_command')}")
        lines.append(f"  - apply: {row.get('apply_command')}")
    return '\n'.join(lines).strip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate operator-ready partner input flow commands.')
    parser.add_argument('--handoff', type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument('--json', type=Path, default=DEFAULT_JSON)
    parser.add_argument('--md', type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    payload = build_partner_input_operator_flow(handoff_path=args.handoff)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    args.md.write_text(_to_markdown(payload), encoding='utf-8')
    print(json.dumps({'ok': True, 'json': str(args.json), 'md': str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
