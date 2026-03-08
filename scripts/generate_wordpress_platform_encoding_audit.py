#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]

SUSPICIOUS_SINGLE_QUESTION_HANGUL = re.compile(r'(?<!\?)\?(?!\?)[\u3131-\u318E\uAC00-\uD7A3]')
SUSPICIOUS_MOJIBAKE_TOKENS = (
    '\ufffd',
    '\\ufffd',
    '揶쎛野?',
    '?곕뗄荑?',
    '?臾먮즲',
    '?紐낅?',
    '?怨룸뼖',
    '嶺뚮씞',
    '嶺뚯솘',
    '筌',
)

REQUIRED_PHRASES_BY_NAME: Dict[str, List[str]] = {
    'wordpress_platform_ia_latest.json': [
        '플랫폼 소개',
        '서울건설정보 메인 플랫폼',
        'AI 양도가 산정',
        'AI 인허가 사전검토',
        '지식베이스',
    ],
    'wp_platform_blueprints_latest.json': [
        '서울건설정보 메인 플랫폼',
        'AI 양도가 산정',
        'AI 인허가 사전검토',
    ],
    'wp_surface_lab_apply_latest.json': [
        '서울건설정보 플랫폼',
        '서울건설정보 메인 플랫폼',
        'AI 양도가 산정',
        'AI 인허가 사전검토',
    ],
    'navigation.json': [
        '플랫폼 소개',
        '양도가',
        '인허가',
        '지식베이스',
        '상담',
    ],
    'home.html': [
        '서비스를 먼저 분기하고, 계산은 전용 페이지에서만 실행합니다.',
        'AI 양도가 산정 + 유사매물 추천',
        'AI 인허가 사전검토',
    ],
    'yangdo.html': [
        'AI 양도가 산정 시스템',
        '추천 결과는 가격표가 아니라 시장 적합도 해석입니다.',
        '추천 매물 흐름 보기',
        '상담형 상세 요청',
    ],
    'permit.html': [
        'AI 인허가 사전검토',
        '등록기준 부족 항목과 다음 조치를 단계별로 보여주는 인허가 플랫폼',
        '상세 체크리스트',
        '수동 검토 요청',
        '등록기준 안내 보기',
    ],
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return ''


def _missing_phrases(text: str, phrases: Iterable[str]) -> List[str]:
    return [phrase for phrase in phrases if phrase not in text]


def _scan_file(path: Path) -> Dict[str, Any]:
    text = _read_text(path)
    issues: List[Dict[str, Any]] = []
    if not text:
        return {
            'path': str(path.resolve()),
            'checked': False,
            'issue_count': 1,
            'issues': [{'kind': 'unreadable_or_empty'}],
        }

    suspicious_token_hits = [token for token in SUSPICIOUS_MOJIBAKE_TOKENS if token in text]
    if suspicious_token_hits:
        issues.append({'kind': 'known_mojibake_token_present', 'tokens': suspicious_token_hits})

    suspicious_matches = list(SUSPICIOUS_SINGLE_QUESTION_HANGUL.finditer(text))
    if suspicious_matches:
        samples = []
        for match in suspicious_matches[:5]:
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 40)
            samples.append(text[start:end].replace('\n', ' '))
        issues.append(
            {
                'kind': 'single_question_hangul_sequence',
                'count': len(suspicious_matches),
                'samples': samples,
            }
        )

    required_phrases = REQUIRED_PHRASES_BY_NAME.get(path.name, [])
    missing = _missing_phrases(text, required_phrases)
    if missing:
        issues.append({'kind': 'required_phrase_missing', 'missing': missing})

    return {
        'path': str(path.resolve()),
        'checked': True,
        'issue_count': len(issues),
        'issues': issues,
    }


def build_encoding_audit(paths: List[Path]) -> Dict[str, Any]:
    files = [_scan_file(path) for path in paths]
    issue_files = [row for row in files if int(row.get('issue_count', 0) or 0) > 0]
    return {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'checked_file_count': len(files),
            'issue_file_count': len(issue_files),
            'encoding_ok': len(issue_files) == 0,
        },
        'files': files,
        'next_actions': (
            ['Encoding audit is clean across current WordPress platform sources and latest artifacts.']
            if not issue_files
            else [
                'Fix the flagged source or generated artifact before using it as a live platform asset.',
                'Regenerate the affected artifact after correcting the source encoding or copy integrity.',
            ]
        ),
    }


def _default_paths() -> List[Path]:
    return [
        ROOT / 'scripts' / 'generate_wordpress_platform_ia.py',
        ROOT / 'scripts' / 'scaffold_wp_platform_blueprints.py',
        ROOT / 'scripts' / 'apply_wp_surface_lab_blueprints.py',
        ROOT / 'workspace_partitions' / 'site_session' / 'wp_surface_lab' / 'staging' / 'wp-content' / 'themes' / 'seoulmna-platform-child' / 'blueprints' / 'navigation.json',
        ROOT / 'workspace_partitions' / 'site_session' / 'wp_surface_lab' / 'staging' / 'wp-content' / 'themes' / 'seoulmna-platform-child' / 'blueprints' / 'home.html',
        ROOT / 'workspace_partitions' / 'site_session' / 'wp_surface_lab' / 'staging' / 'wp-content' / 'themes' / 'seoulmna-platform-child' / 'blueprints' / 'yangdo.html',
        ROOT / 'workspace_partitions' / 'site_session' / 'wp_surface_lab' / 'staging' / 'wp-content' / 'themes' / 'seoulmna-platform-child' / 'blueprints' / 'permit.html',
        ROOT / 'logs' / 'wordpress_platform_ia_latest.json',
        ROOT / 'logs' / 'wp_platform_blueprints_latest.json',
        ROOT / 'logs' / 'wp_surface_lab_apply_latest.json',
        ROOT / 'logs' / 'wp_surface_lab_page_verify_latest.json',
    ]


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    lines = [
        '# WordPress Platform Encoding Audit',
        '',
        f"- checked_file_count: {summary.get('checked_file_count')}",
        f"- issue_file_count: {summary.get('issue_file_count')}",
        f"- encoding_ok: {summary.get('encoding_ok')}",
        '',
        '## Files',
    ]
    for row in payload.get('files', []):
        issues = row.get('issues') if isinstance(row.get('issues'), list) else []
        labels = ', '.join(
            str(item.get('kind') or '')
            for item in issues
            if isinstance(item, dict) and str(item.get('kind') or '').strip()
        ) or '(none)'
        lines.append(f"- {row.get('path')}: issue_count={row.get('issue_count')} issues={labels}")
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit current WordPress platform sources/artifacts for encoding or Korean copy integrity issues.')
    parser.add_argument('--json', type=Path, default=ROOT / 'logs' / 'wordpress_platform_encoding_audit_latest.json')
    parser.add_argument('--md', type=Path, default=ROOT / 'logs' / 'wordpress_platform_encoding_audit_latest.md')
    args = parser.parse_args()

    payload = build_encoding_audit(_default_paths())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    args.md.write_text(_to_markdown(payload), encoding='utf-8')
    print(f'[ok] wrote {args.json}')
    print(f'[ok] wrote {args.md}')
    return 0 if bool((payload.get('summary') or {}).get('encoding_ok')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
