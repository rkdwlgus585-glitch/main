#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANNELS = ROOT / 'tenant_config' / 'channel_profiles.json'
DEFAULT_FRONT_APP = ROOT / 'workspace_partitions' / 'site_session' / 'kr_platform_front'


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _find_channel(payload: Dict[str, Any], channel_id: str) -> Dict[str, Any]:
    wanted = str(channel_id or '').strip().lower()
    for row in payload.get('channels') or []:
        if isinstance(row, dict) and str(row.get('channel_id') or '').strip().lower() == wanted:
            return row
    return {}


def build_env_map(*, channel: Dict[str, Any]) -> Dict[str, str]:
    branding = channel.get('branding') if isinstance(channel.get('branding'), dict) else {}
    platform_front_host = str(channel.get('platform_front_host') or '').strip() or 'seoulmna.kr'
    legacy_content_host = str(channel.get('legacy_content_host') or '').strip() or 'seoulmna.co.kr'
    calculator_mount_base = str(channel.get('public_calculator_mount_base') or '').strip()
    if not calculator_mount_base:
        base_host = platform_front_host if '://' in platform_front_host else f'https://{platform_front_host}'
        calculator_mount_base = f"{base_host.rstrip('/')}/_calc"
    engine_origin = str(channel.get('engine_origin') or '').strip().rstrip('/')
    return {
        'NEXT_PUBLIC_PLATFORM_FRONT_HOST': f'https://{platform_front_host}' if '://' not in platform_front_host else platform_front_host,
        'NEXT_PUBLIC_LISTING_HOST': f'https://{legacy_content_host}' if '://' not in legacy_content_host else legacy_content_host,
        'NEXT_PUBLIC_CONTENT_HOST': f'https://{legacy_content_host}' if '://' not in legacy_content_host else legacy_content_host,
        'NEXT_PUBLIC_CALCULATOR_MOUNT_BASE': calculator_mount_base,
        'NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN': engine_origin,
        'NEXT_PUBLIC_CONTACT_PHONE': str(branding.get('contact_phone') or '1668-3548'),
        'NEXT_PUBLIC_CONTACT_EMAIL': str(branding.get('contact_email') or 'seoulmna@gmail.com'),
        'NEXT_PUBLIC_TENANT_ID': str(channel.get('default_tenant_id') or 'seoul_main'),
    }


def render_env(env_map: Dict[str, str]) -> str:
    ordered = [
        'NEXT_PUBLIC_PLATFORM_FRONT_HOST',
        'NEXT_PUBLIC_LISTING_HOST',
        'NEXT_PUBLIC_CONTENT_HOST',
        'NEXT_PUBLIC_CALCULATOR_MOUNT_BASE',
        'NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN',
        'NEXT_PUBLIC_CONTACT_PHONE',
        'NEXT_PUBLIC_CONTACT_EMAIL',
        'NEXT_PUBLIC_TENANT_ID',
    ]
    lines = [f'{key}={env_map[key]}' for key in ordered if key in env_map]
    return '\n'.join(lines).rstrip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Sync the seoulmna.kr platform front env file from channel config')
    parser.add_argument('--channel-id', default='seoul_web')
    parser.add_argument('--channels', default=str(DEFAULT_CHANNELS))
    parser.add_argument('--front-app', default=str(DEFAULT_FRONT_APP))
    parser.add_argument('--output', default='.env.local')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    payload = _load_json(Path(str(args.channels)).resolve())
    channel = _find_channel(payload, str(args.channel_id))
    if not channel:
        print(json.dumps({'ok': False, 'error': 'channel_not_found', 'channel_id': args.channel_id}, ensure_ascii=False, indent=2))
        return 1

    env_map = build_env_map(channel=channel)
    front_app = Path(str(args.front_app)).resolve()
    output_path = (front_app / str(args.output)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_env(env_map)
    if not args.dry_run:
        output_path.write_text(content, encoding='utf-8')

    print(
        json.dumps(
            {
                'ok': True,
                'channel_id': str(args.channel_id),
                'front_app': str(front_app),
                'output': str(output_path),
                'dry_run': bool(args.dry_run),
                'env': env_map,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
