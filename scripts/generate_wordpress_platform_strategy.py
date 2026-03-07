#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURFACE_AUDIT = ROOT / 'logs' / 'surface_stack_audit_latest.json'
DEFAULT_WP_LAB = ROOT / 'logs' / 'wp_surface_lab_latest.json'
DEFAULT_WP_ASSETS = ROOT / 'logs' / 'wp_platform_assets_latest.json'
BENCHMARK_URL = 'https://admini.kr'


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fetch_site_signal(url: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {'url': url, 'ok': False, 'status_code': 0, 'server': '', 'title': '', 'signals': []}
    try:
        res = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        out['status_code'] = int(res.status_code)
        out['server'] = str(res.headers.get('server') or res.headers.get('Server') or '').strip()
        html = res.text or ''
        lower = html.lower()
        if '<title>' in lower and '</title>' in lower:
            start = lower.index('<title>') + len('<title>')
            end = lower.index('</title>', start)
            out['title'] = html[start:end].strip()
        for marker in ('/_next/', 'vercel', 'next', 'platform'):
            if marker in lower and marker not in out['signals']:
                out['signals'].append(marker)
        out['ok'] = res.status_code == 200
    except Exception as exc:  # noqa: BLE001
        out['error'] = str(exc)
    return out


def build_wordpress_platform_strategy(*, surface_audit_path: Path, wp_lab_path: Path, wp_assets_path: Path) -> Dict[str, Any]:
    surface = _load_json(surface_audit_path)
    wp_lab = _load_json(wp_lab_path)
    wp_assets = _load_json(wp_assets_path)
    benchmark = _fetch_site_signal(BENCHMARK_URL)

    kr_host = str(surface.get('surfaces', {}).get('kr', {}).get('host') or 'seoulmna.kr')
    co_host = str(surface.get('surfaces', {}).get('co', {}).get('host') or 'seoulmna.co.kr')
    kr_stack = str(surface.get('surfaces', {}).get('kr', {}).get('stack') or '')

    strategy = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_live_stack': {
            'kr_host': kr_host,
            'kr_stack': kr_stack,
            'co_host': co_host,
            'co_role': 'listing_market_site',
        },
        'benchmark': {
            'url': benchmark.get('url'),
            'status_code': benchmark.get('status_code'),
            'server': benchmark.get('server'),
            'signals': benchmark.get('signals') or [],
            'interpretation': 'Use a platform front with a clear product split and dedicated service entry points, not a single long brochure page.',
        },
        'runtime_decision': {
            'primary_runtime': 'wordpress_astra_live',
            'support_runtime': 'private_engine_behind_kr_reverse_proxy',
            'next_cutover_status': 'keep_as_parallel_target_only',
            'reason': 'The live .kr surface is already WordPress/Astra. The shortest path to a real platform is to platformize that runtime first, keep .co.kr focused on listings, and hide the calculator engine behind a .kr reverse proxy instead of creating a third public site.',
        },
        'plugin_stack': {
            'keep_live': ['astra', 'rank-math'],
            'stage_first': ['seoulmna-platform-child', 'seoulmna-platform-bridge', 'astra-sites', 'ultimate-addons-for-gutenberg'],
            'avoid_live_duplication': ['wordpress-seo'],
            'notes': [
                'Do not run Yoast and Rank Math together on the live site.',
                'Use Starter Templates and Spectra only in staging until layout and performance are verified.',
                'Keep calculator runtime out of WordPress PHP requests; expose it only through the .kr /_calc reverse-proxied public mount and lazy iframe gates.',
                'Do not turn seoulmna.co.kr into a general calculator surface; it should remain the listing market site.',
            ],
        },
        'information_architecture': {
            'primary_nav': ['플랫폼 소개', '양도가', '인허가', '기업진단', '매물/양도양수', '지식베이스', '상담'],
            'secondary_nav': ['성공사례', '업종별 등록기준', 'FAQ', '공지'],
            'home_modules': [
                'platform_hero',
                'service_split_cards',
                'trust_metrics',
                'knowledge_strip',
                'consulting_cta_band',
            ],
        },
        'calculator_mount_decision': {
            'recommended_pattern': 'cta_on_home_lazy_gate_on_service_page_private_runtime_on_kr',
            'private_engine_public_mount': f'https://{kr_host}/_calc/<type>?embed=1',
            'matrix': [
                {
                    'pattern': 'auto_inline_iframe_everywhere',
                    'decision': 'reject',
                    'why': 'Creates traffic leakage, weak caching behavior, and lower editorial control.',
                },
                {
                    'pattern': 'cta_cards_only',
                    'decision': 'adopt_on_home_and_knowledge',
                    'why': 'Best for SEO pages and keeps WordPress rendering cheap.',
                },
                {
                    'pattern': 'lazy_gate_shortcode',
                    'decision': 'adopt_on_service_pages',
                    'why': 'Allows a strong platform UX while ensuring iframe creation only happens after intent is explicit.',
                },
                {
                    'pattern': 'full_session_on_listing_domain',
                    'decision': 'reject_for_public_surface',
                    'why': '.co.kr is the listing market site. Heavy runtime should sit behind .kr reverse-proxied service paths, not on the listing domain.',
                },
            ],
            'recommended_by_page': {
                'home': 'cta_cards_only',
                'yangdo_service': 'lazy_gate_shortcode',
                'permit_service': 'lazy_gate_shortcode',
                'knowledge_posts': 'cta_cards_only',
                'public_runtime': f'https://{kr_host}/_calc/<type>?embed=1',
                'listing_site_policy': f'https://{co_host}/ stays listing-focused and links back to {kr_host} service pages.',
            },
        },
        'brainstorm': [
            {
                'idea': '업종별 등록기준 백과',
                'impact': 'Improves SEO and makes the permit tool feel like part of a larger platform instead of a standalone calculator.',
            },
            {
                'idea': '양도양수 사례 데이터룸',
                'impact': 'Lets the range calculator feed directly into evidence-driven consult pages and increases trust without exposing raw source data.',
            },
            {
                'idea': '매물-플랫폼 양방향 라우팅',
                'impact': 'Keep listings on .co.kr, but send users who need valuation or permit precheck back to the .kr platform service pages instead of embedding tools on the listing domain.',
            },
            {
                'idea': '플랫폼형 상담 분기',
                'impact': 'Split inbound flows into yangdo, permit, and diagnostic consult lanes before the user reaches a human, reducing operator sorting cost.',
            },
            {
                'idea': '도구-문서-상담 3단 구조',
                'impact': 'Users who are not ready to use the calculator can still enter through guides or case studies, then move to gated tools later.',
            },
        ],
        'objective_inputs': {
            'wp_lab_package_count': int(wp_lab.get('summary', {}).get('package_count') or 0),
            'wp_assets_ready': bool(wp_assets.get('summary', {}).get('theme_ready')) and bool(wp_assets.get('summary', {}).get('plugin_ready')),
            'references': [
                'https://wpastra.com/docs/child-theme/',
                'https://wordpress.org/plugins/astra-sites/',
                'https://wordpress.org/plugins/ultimate-addons-for-gutenberg/',
                'https://wordpress.org/plugins/seo-by-rank-math/',
                'https://wordpress.org/plugins/wordpress-seo/',
                'https://admini.kr',
            ],
        },
        'next_actions': [
            'Stage the Astra child theme and the lazy calculator bridge inside the isolated WordPress lab first.',
            'Use CTA-only sections on the homepage and knowledge pages; keep iframes off the initial render path.',
            'Mount lazy calculator gates only on dedicated service pages for Yangdo and Permit.',
            'Keep .co.kr listing-focused and route calculator demand back to .kr service pages.',
            'Place the private engine behind seoulmna.kr reverse-proxied paths such as /_calc/* instead of exposing a third public brand.',
        ],
    }
    return strategy


def _to_markdown(payload: Dict[str, Any]) -> str:
    runtime = payload.get('runtime_decision', {})
    calc = payload.get('calculator_mount_decision', {})
    plugin_stack = payload.get('plugin_stack', {})
    benchmark = payload.get('benchmark', {})
    lines = [
        '# WordPress Platform Strategy',
        '',
        '## Runtime Decision',
        f"- primary_runtime: {runtime.get('primary_runtime')}",
        f"- support_runtime: {runtime.get('support_runtime')}",
        f"- next_cutover_status: {runtime.get('next_cutover_status')}",
        f"- reason: {runtime.get('reason')}",
        '',
        '## Benchmark',
        f"- url: {benchmark.get('url')}",
        f"- status_code: {benchmark.get('status_code')}",
        f"- server: {benchmark.get('server') or '(none)'}",
        f"- signals: {', '.join(benchmark.get('signals') or []) or '(none)'}",
        f"- interpretation: {benchmark.get('interpretation')}",
        '',
        '## Calculator Mount',
        f"- recommended_pattern: {calc.get('recommended_pattern')}",
    ]
    for key, value in (calc.get('recommended_by_page') or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        '',
        '## Plugin Stack',
        f"- keep_live: {', '.join(plugin_stack.get('keep_live') or []) or '(none)'}",
        f"- stage_first: {', '.join(plugin_stack.get('stage_first') or []) or '(none)'}",
        f"- avoid_live_duplication: {', '.join(plugin_stack.get('avoid_live_duplication') or []) or '(none)'}",
        '',
        '## Brainstorm',
    ])
    for row in payload.get('brainstorm') or []:
        if isinstance(row, dict):
            lines.append(f"- {row.get('idea')}: {row.get('impact')}")
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate the WordPress-first platform strategy for seoulmna.kr.')
    parser.add_argument('--surface-audit', type=Path, default=DEFAULT_SURFACE_AUDIT)
    parser.add_argument('--wp-lab', type=Path, default=DEFAULT_WP_LAB)
    parser.add_argument('--wp-assets', type=Path, default=DEFAULT_WP_ASSETS)
    parser.add_argument('--json', type=Path, default=ROOT / 'logs' / 'wordpress_platform_strategy_latest.json')
    parser.add_argument('--md', type=Path, default=ROOT / 'logs' / 'wordpress_platform_strategy_latest.md')
    args = parser.parse_args()

    payload = build_wordpress_platform_strategy(
        surface_audit_path=args.surface_audit,
        wp_lab_path=args.wp_lab,
        wp_assets_path=args.wp_assets,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    args.md.write_text(_to_markdown(payload), encoding='utf-8')
    print(f'[ok] wrote {args.json}')
    print(f'[ok] wrote {args.md}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
