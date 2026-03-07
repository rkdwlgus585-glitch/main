#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANNELS = ROOT / 'tenant_config' / 'channel_profiles.json'
DEFAULT_MANIFEST = ROOT / 'output' / 'widget' / 'bundles' / 'seoul_widget_internal' / 'manifest.json'
DEFAULT_OPERATIONS = ROOT / 'logs' / 'operations_packet_latest.json'
DEFAULT_ATTORNEY = ROOT / 'logs' / 'attorney_handoff_latest.json'
DEFAULT_FRONT_APP = ROOT / 'workspace_partitions' / 'site_session' / 'kr_platform_front'


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_tag(html: str, prefix: str) -> str:
    marker = str(prefix or '').strip()
    if not marker:
        return ''
    idx = html.find(marker)
    if idx < 0:
        return ''
    start = idx + len(marker)
    end = html.find('"', start)
    if end < 0:
        return ''
    return html[start:end].strip()


def _extract_meta_signals(html: str, headers: Dict[str, str], url: str) -> Dict[str, Any]:
    server = str(headers.get('server') or headers.get('Server') or '').strip()
    title = ''
    if '<title>' in html and '</title>' in html:
        title = html.split('<title>', 1)[1].split('</title>', 1)[0].strip()
    description = _extract_tag(html, '<meta name="description" content="')
    og_title = _extract_tag(html, '<meta property="og:title" content="')
    og_description = _extract_tag(html, '<meta property="og:description" content="')
    lower = html.lower()
    wordpress_markers = [
        token for token in ('/wp-content/', '/wp-admin/', '/wp-json/', 'generator" content="wordpress')
        if token in lower
    ]
    astra_markers = [
        token for token in ('astra-theme-css', 'wp-theme-astra', 'astra-4.', 'wpastra.com')
        if token in lower
    ]
    weaver_markers = [
        token for token in ('/plugin/weaver_plugin/', 'weaver.css', 'g5_url', 'gnuboard')
        if token in lower
    ]
    live_stack = 'unknown'
    if wordpress_markers and astra_markers:
        live_stack = 'wordpress_astra_live'
    elif wordpress_markers:
        live_stack = 'wordpress_live'
    elif weaver_markers:
        live_stack = 'gnuboard_weaver_like'
    elif '/_next/static/' in lower or '__next' in lower or 'vercel' in server.lower():
        live_stack = 'nextjs_like_live'
    return {
        'url': url,
        'server': server,
        'title': title,
        'description': description,
        'og_title': og_title,
        'og_description': og_description,
        'is_vercel': 'vercel' in server.lower(),
        'is_nextjs_like': '/_next/static/' in lower or '__next' in lower,
        'wordpress_markers': wordpress_markers,
        'astra_markers': astra_markers,
        'weaver_markers': weaver_markers,
        'live_stack': live_stack,
        'platform_keyword_count': sum(
            1
            for token in ('플랫폼', 'platform', 'ai', '서비스', 'solution', '통합')
            if token in f'{title} {description} {og_title} {og_description}'.lower()
        ),
    }


def fetch_site_signal(url: str, timeout_sec: int = 15) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        'url': url,
        'ok': False,
        'status_code': 0,
        'error': '',
    }
    try:
        res = requests.get(url, timeout=timeout_sec, headers={'User-Agent': 'Mozilla/5.0'})
        out['status_code'] = int(res.status_code)
        if res.status_code != 200:
            out['error'] = f'http_{res.status_code}'
            return out
        apparent = str(getattr(res, 'apparent_encoding', '') or '').strip()
        if apparent:
            try:
                res.encoding = apparent
            except Exception:
                pass
        out.update(_extract_meta_signals(res.text or '', dict(res.headers or {}), url))
        out['ok'] = True
        return out
    except Exception as exc:  # noqa: BLE001
        out['error'] = str(exc)
        return out


def _find_channel(channels: Dict[str, Any], channel_id: str) -> Dict[str, Any]:
    wanted = str(channel_id or '').strip().lower()
    for row in channels.get('channels') or []:
        if isinstance(row, dict) and str(row.get('channel_id') or '').strip().lower() == wanted:
            return row
    return {}


def _widget_map(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in manifest.get('widgets') or []:
        if isinstance(row, dict):
            key = str(row.get('widget') or '').strip().lower()
            if key:
                out[key] = row
    return out


def _track_by_id(attorney: Dict[str, Any], track_id: str) -> Dict[str, Any]:
    rows = attorney.get('tracks') if isinstance(attorney.get('tracks'), list) else []
    wanted = str(track_id or '').strip().upper()
    for row in rows or []:
        if isinstance(row, dict) and str(row.get('track_id') or '').strip().upper() == wanted:
            return row
    return {}


def _detect_front_app(front_app_path: Path) -> Dict[str, Any]:
    package_json = front_app_path / 'package.json'
    readme = front_app_path / 'README.md'
    env_example = front_app_path / '.env.example'
    vercel_json = front_app_path / 'vercel.json'
    next_build_manifest = front_app_path / '.next' / 'build-manifest.json'
    package_payload = _load_json(package_json)
    scripts = package_payload.get('scripts') if isinstance(package_payload.get('scripts'), dict) else {}
    deps = package_payload.get('dependencies') if isinstance(package_payload.get('dependencies'), dict) else {}
    routes = []
    app_dir = front_app_path / 'app'
    if app_dir.exists():
        for route in ('page.tsx', 'yangdo/page.tsx', 'permit/page.tsx', 'api/platform-status/route.ts'):
            routes.append({'route': route, 'exists': (app_dir / route).exists()})
    return {
        'path': str(front_app_path),
        'exists': front_app_path.exists(),
        'package_json_ready': package_json.exists(),
        'node_modules_ready': (front_app_path / 'node_modules').exists(),
        'build_artifacts_ready': next_build_manifest.exists(),
        'readme_ready': readme.exists(),
        'env_example_ready': env_example.exists(),
        'vercel_config_ready': vercel_json.exists(),
        'next_version': str(deps.get('next') or ''),
        'react_version': str(deps.get('react') or ''),
        'build_script_ready': str(scripts.get('build') or '') == 'next build',
        'dev_script_ready': str(scripts.get('dev') or '') == 'next dev',
        'routes': routes,
        'deployment_target': 'vercel_nextjs',
    }


def build_platform_front_audit(
    *,
    benchmark_url: str,
    public_urls: list[str],
    channel_id: str,
    channels_path: Path,
    manifest_path: Path,
    operations_path: Path,
    attorney_path: Path,
    front_app_path: Path,
) -> Dict[str, Any]:
    channels = _load_json(channels_path)
    manifest = _load_json(manifest_path)
    operations = _load_json(operations_path)
    attorney = _load_json(attorney_path)
    channel = _find_channel(channels, channel_id)
    widgets = _widget_map(manifest)
    benchmark = fetch_site_signal(benchmark_url)
    public_signals = [fetch_site_signal(url) for url in public_urls]
    signal_by_url = {str(row.get('url') or '').strip().lower(): row for row in public_signals if isinstance(row, dict)}
    host_policy = str(channel.get('public_host_policy') or 'dual_host').strip().lower() or 'dual_host'
    canonical_host = str(channel.get('canonical_public_host') or manifest.get('canonical_public_host') or manifest.get('host') or '').strip().lower()
    platform_front_host = str(channel.get('platform_front_host') or '').strip().lower()
    legacy_content_host = str(channel.get('legacy_content_host') or '').strip().lower()
    current_live_signal = signal_by_url.get(f'https://{canonical_host}', {})
    current_live_stack = str(current_live_signal.get('live_stack') or '')
    operations_go_live = operations.get('go_live') if isinstance(operations.get('go_live'), dict) else {}
    operations_decisions = operations.get('decisions') if isinstance(operations.get('decisions'), dict) else {}
    track_a = _track_by_id(attorney, 'A')
    track_b = _track_by_id(attorney, 'B')
    front_app = _detect_front_app(front_app_path)

    calculators = {
        'yangdo_widget_ready': bool(widgets.get('yangdo', {}).get('ok')),
        'permit_widget_ready': bool(widgets.get('permit', {}).get('ok')),
        'separated_systems': True,
        'live_confirmation_pending': str(operations_decisions.get('seoul_live_decision') or '') == 'awaiting_live_confirmation',
    }
    patent = {
        'track_a_claim_sentence_ready': bool(track_a.get('claim_sentence_draft')),
        'track_b_claim_sentence_ready': bool(track_b.get('claim_sentence_draft')),
        'final_attorney_adjustment_pending': True,
    }
    front = {
        'channel_id': str(channel.get('channel_id') or channel_id),
        'channel_role': str(channel.get('channel_role') or '').strip().lower(),
        'channel_hosts': list(channel.get('channel_hosts') or []),
        'canonical_public_host': canonical_host,
        'current_live_public_host': canonical_host,
        'current_live_public_stack': current_live_stack,
        'public_host_policy': host_policy,
        'target_platform_front_host': platform_front_host,
        'listing_market_host': legacy_content_host,
        'public_calculator_mount_base': str(channel.get('public_calculator_mount_base') or f'https://{canonical_host}/_calc').strip(),
        'private_engine_visibility': str(channel.get('private_engine_visibility') or 'hidden_origin').strip().lower(),
        'engine_origin': str(channel.get('engine_origin') or ''),
        'embed_base_url': str(channel.get('embed_base_url') or ''),
        'platform_front_ready': bool(canonical_host) and bool(channel.get('engine_origin')) and bool(widgets.get('yangdo')) and bool(widgets.get('permit')),
        'platform_front_gap': [],
    }
    if host_policy != 'kr_main_platform':
        front['platform_front_gap'].append('canonical_host_policy_not_explicit')
    if canonical_host != 'seoulmna.kr':
        front['platform_front_gap'].append('canonical_public_host_not_kr')
    if platform_front_host != 'seoulmna.kr':
        front['platform_front_gap'].append('platform_front_host_not_kr')
    if legacy_content_host != 'seoulmna.co.kr':
        front['platform_front_gap'].append('listing_market_host_not_cokr')
    if str(channel.get('public_calculator_mount_base') or '').strip().lower() not in {'https://seoulmna.kr/_calc', 'http://seoulmna.kr/_calc'}:
        front['platform_front_gap'].append('public_calculator_mount_not_kr')
    if canonical_host != platform_front_host:
        front['platform_front_gap'].append('kr_platform_front_transition_pending')
    if current_live_stack.startswith('wordpress'):
        front['platform_front_gap'].append('kr_live_wordpress_cutover_pending')
    if not benchmark.get('ok'):
        front['platform_front_gap'].append('benchmark_fetch_failed')
    if not front_app.get('exists'):
        front['platform_front_gap'].append('kr_front_app_missing')
    if not front_app.get('build_artifacts_ready'):
        front['platform_front_gap'].append('kr_front_build_artifacts_missing')
    if not front_app.get('env_example_ready'):
        front['platform_front_gap'].append('kr_front_env_example_missing')
    if not front_app.get('vercel_config_ready'):
        front['platform_front_gap'].append('kr_front_vercel_config_missing')

    recommended_direction = {
        'decision': 'kr_main_platform_with_internal_widget_consumer',
        'reason': [
            'admini benchmark is served from Vercel and exposes a platform-first front',
            'the current live seoulmna.kr surface is WordPress-based, so any Next.js platform front is a migration target, not the current live reality',
            'the current engine and widget layers are already reusable, so the remaining bottleneck is the public front/domain topology',
            'the user-facing brand and calculator mount should live on seoulmna.kr while seoulmna.co.kr remains the listing market site',
        ],
        'next_execution_focus': [
            'audit the current live WordPress/Astra kr surface separately from the Next.js migration target',
            'promote seoulmna.kr into the platform-style public front',
            'treat seoulmna.co.kr as the listing market site, not as a calculator runtime surface',
            'keep the engine host private and expose public calculator traffic only through seoulmna.kr/_calc/*',
            'switch canonical host only after kr front deployment and runtime verification succeed',
        ],
    }

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'benchmark': benchmark,
        'public_signals': public_signals,
        'front': front,
        'front_app': front_app,
        'calculators': calculators,
        'patent': patent,
        'local_truth': {
            'seoul_live_decision': str(operations_decisions.get('seoul_live_decision') or ''),
            'partner_activation_decision': str(operations_decisions.get('partner_activation_decision') or ''),
            'quality_green': bool(operations_go_live.get('quality_green')),
        },
        'completion_summary': {
            'front_platform_status': (
                'kr_wordpress_live_next_cutover_pending'
                if current_live_stack.startswith('wordpress') and front_app.get('build_artifacts_ready')
                else (
                    'kr_front_build_ready_transition_pending'
                    if front_app.get('build_artifacts_ready') and 'kr_platform_front_transition_pending' in front['platform_front_gap']
                else (
                    'policy_ready_live_confirmation_pending'
                    if not front['platform_front_gap'] and calculators['live_confirmation_pending']
                    else ('front_transition_pending' if 'kr_platform_front_transition_pending' in front['platform_front_gap'] else ('front_policy_and_live_pending' if front['platform_front_gap'] else 'ready'))
                ))
            ),
            'calculator_status': 'engine_complete_live_front_pending' if calculators['live_confirmation_pending'] else 'ready',
            'patent_status': (
                'claim_draft_ready_attorney_adjustment_pending'
                if patent['track_a_claim_sentence_ready'] and patent['track_b_claim_sentence_ready'] and patent['final_attorney_adjustment_pending']
                else ('attorney_adjustment_pending' if patent['final_attorney_adjustment_pending'] else 'ready')
            ),
        },
        'recommended_direction': recommended_direction,
    }


def _to_markdown(data: Dict[str, Any]) -> str:
    benchmark = data.get('benchmark') if isinstance(data.get('benchmark'), dict) else {}
    front = data.get('front') if isinstance(data.get('front'), dict) else {}
    front_app = data.get('front_app') if isinstance(data.get('front_app'), dict) else {}
    calc = data.get('calculators') if isinstance(data.get('calculators'), dict) else {}
    patent = data.get('patent') if isinstance(data.get('patent'), dict) else {}
    local_truth = data.get('local_truth') if isinstance(data.get('local_truth'), dict) else {}
    summary = data.get('completion_summary') if isinstance(data.get('completion_summary'), dict) else {}
    public_signals = data.get('public_signals') if isinstance(data.get('public_signals'), list) else []
    lines = [
        '# Platform Front Audit',
        '',
        '## Benchmark',
        f"- benchmark_url: {benchmark.get('url', '')}",
        f"- server: {benchmark.get('server', '')}",
        f"- is_vercel: {benchmark.get('is_vercel', False)}",
        f"- is_nextjs_like: {benchmark.get('is_nextjs_like', False)}",
        f"- title: {benchmark.get('title', '')}",
        '',
        '## Public Front',
        f"- canonical_public_host: {front.get('canonical_public_host', '')}",
        f"- current_live_public_stack: {front.get('current_live_public_stack', '')}",
        f"- channel_role: {front.get('channel_role', '')}",
        f"- public_host_policy: {front.get('public_host_policy', '')}",
        f"- target_platform_front_host: {front.get('target_platform_front_host', '')}",
        f"- listing_market_host: {front.get('listing_market_host', '')}",
        f"- public_calculator_mount_base: {front.get('public_calculator_mount_base', '')}",
        f"- private_engine_visibility: {front.get('private_engine_visibility', '')}",
        f"- engine_origin: {front.get('engine_origin', '')}",
        f"- platform_front_ready: {front.get('platform_front_ready', False)}",
        f"- platform_front_gap: {', '.join(front.get('platform_front_gap', [])) or '(none)'}",
        '',
        '## KR Front App',
        f"- path: {front_app.get('path', '')}",
        f"- exists: {front_app.get('exists', False)}",
        f"- node_modules_ready: {front_app.get('node_modules_ready', False)}",
        f"- build_artifacts_ready: {front_app.get('build_artifacts_ready', False)}",
        f"- env_example_ready: {front_app.get('env_example_ready', False)}",
        f"- vercel_config_ready: {front_app.get('vercel_config_ready', False)}",
        f"- next_version: {front_app.get('next_version', '')}",
        f"- deployment_target: {front_app.get('deployment_target', '')}",
        '',
        '## Calculators',
        f"- yangdo_widget_ready: {calc.get('yangdo_widget_ready', False)}",
        f"- permit_widget_ready: {calc.get('permit_widget_ready', False)}",
        f"- live_confirmation_pending: {calc.get('live_confirmation_pending', False)}",
        '',
        '## Patent',
        f"- track_a_claim_sentence_ready: {patent.get('track_a_claim_sentence_ready', False)}",
        f"- track_b_claim_sentence_ready: {patent.get('track_b_claim_sentence_ready', False)}",
        f"- final_attorney_adjustment_pending: {patent.get('final_attorney_adjustment_pending', False)}",
        '',
        '## Completion Summary',
        f"- front_platform_status: {summary.get('front_platform_status', '')}",
        f"- calculator_status: {summary.get('calculator_status', '')}",
        f"- patent_status: {summary.get('patent_status', '')}",
        '',
        '## Local Truth',
        f"- seoul_live_decision: {local_truth.get('seoul_live_decision', '')}",
        f"- partner_activation_decision: {local_truth.get('partner_activation_decision', '')}",
        f"- quality_green: {local_truth.get('quality_green', False)}",
        '',
        '## Public Signals',
    ]
    for row in public_signals:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('url', '')} :: ok={row.get('ok', False)} server={row.get('server', '')} title={row.get('title', '')}"
        )
    return '\n'.join(lines).rstrip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Benchmark platform front posture against admini and local completion state')
    parser.add_argument('--benchmark-url', default='https://admini.kr')
    parser.add_argument('--public-url', action='append', default=['https://seoulmna.kr', 'https://seoulmna.co.kr'])
    parser.add_argument('--channel-id', default='seoul_web')
    parser.add_argument('--channels', default=str(DEFAULT_CHANNELS))
    parser.add_argument('--manifest', default=str(DEFAULT_MANIFEST))
    parser.add_argument('--operations', default=str(DEFAULT_OPERATIONS))
    parser.add_argument('--attorney', default=str(DEFAULT_ATTORNEY))
    parser.add_argument('--front-app', default=str(DEFAULT_FRONT_APP))
    parser.add_argument('--report-json', default='logs/platform_front_audit_latest.json')
    parser.add_argument('--report-md', default='logs/platform_front_audit_latest.md')
    args = parser.parse_args()

    payload = build_platform_front_audit(
        benchmark_url=str(args.benchmark_url),
        public_urls=list(args.public_url or []),
        channel_id=str(args.channel_id),
        channels_path=Path(str(args.channels)).resolve(),
        manifest_path=Path(str(args.manifest)).resolve(),
        operations_path=Path(str(args.operations)).resolve(),
        attorney_path=Path(str(args.attorney)).resolve(),
        front_app_path=Path(str(args.front_app)).resolve(),
    )
    json_path = (ROOT / str(args.report_json)).resolve()
    md_path = (ROOT / str(args.report_md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    md_path.write_text(_to_markdown(payload), encoding='utf-8')
    print(json.dumps({'ok': True, 'report_json': str(json_path), 'report_md': str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
