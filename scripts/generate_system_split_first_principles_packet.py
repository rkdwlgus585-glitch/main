#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM = ROOT / 'logs' / 'ai_platform_first_principles_review_latest.json'
DEFAULT_YANGDO = ROOT / 'logs' / 'yangdo_next_action_brainstorm_latest.json'
DEFAULT_PERMIT = ROOT / 'logs' / 'permit_next_action_brainstorm_latest.json'
DEFAULT_YANGDO_COPY = ROOT / 'logs' / 'yangdo_service_copy_packet_latest.json'
DEFAULT_PERMIT_COPY = ROOT / 'logs' / 'permit_service_copy_packet_latest.json'
DEFAULT_JSON = ROOT / 'logs' / 'system_split_first_principles_packet_latest.json'
DEFAULT_MD = ROOT / 'logs' / 'system_split_first_principles_packet_latest.md'


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _question_stack(*items: str) -> List[str]:
    return [text for text in (str(item or '').strip() for item in items) if text]


def _execution_prompt(payload: Dict[str, Any]) -> str:
    prompt = payload.get('execution_prompt')
    if isinstance(prompt, list):
        return '\n'.join(str(x) for x in prompt if str(x or '').strip())
    return str(prompt or '')


def build_packet(*, platform_path: Path, yangdo_path: Path, permit_path: Path, yangdo_copy_path: Path, permit_copy_path: Path) -> Dict[str, Any]:
    platform = _load_json(platform_path)
    yangdo = _load_json(yangdo_path)
    permit = _load_json(permit_path)
    yangdo_copy = _load_json(yangdo_copy_path)
    permit_copy = _load_json(permit_copy_path)

    platform_summary = platform.get('summary') if isinstance(platform.get('summary'), dict) else {}
    yangdo_summary = yangdo.get('summary') if isinstance(yangdo.get('summary'), dict) else {}
    permit_summary = permit.get('summary') if isinstance(permit.get('summary'), dict) else {}
    yangdo_copy_summary = yangdo_copy.get('summary') if isinstance(yangdo_copy.get('summary'), dict) else {}
    permit_copy_summary = permit_copy.get('summary') if isinstance(permit_copy.get('summary'), dict) else {}

    platform_ready = bool(platform_summary.get('packet_ready'))
    yangdo_ready = bool(yangdo_summary.get('prompt_doc_ready')) and bool(yangdo_copy_summary.get('service_copy_ready'))
    permit_ready = bool(permit_summary.get('prompt_doc_ready')) and bool(permit_copy_summary.get('service_copy_ready'))

    payload = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'packet_ready': platform_ready and yangdo_ready and permit_ready,
            'platform_ready': platform_ready,
            'yangdo_ready': yangdo_ready,
            'permit_ready': permit_ready,
            'prompt_count': 3,
        },
        'tracks': {
            'platform': {
                'goal': '공개/비공개/파트너 경로를 하나의 운영 계약으로 정렬한다.',
                'current_bottleneck': str(platform_summary.get('current_bottleneck') or ''),
                'question_stack': _question_stack(
                    'public/private/partner가 정말 다른 경로를 써야 하는가.',
                    '운영자가 수동으로 판단하는 분기를 더 줄일 수 있는가.',
                    '배포 후 검증을 사람이 읽지 않아도 되는 수준까지 자동화됐는가.',
                ),
                'execution_prompt': str(platform.get('first_principles_prompt') or ''),
                'next_move': 'publish gate 단일화와 post-publish verifier를 먼저 고정한다.',
            },
            'yangdo': {
                'goal': '가격 계산을 시장 적합도 해석과 유사매물 추천 흐름으로 완성한다.',
                'current_bottleneck': str((yangdo.get('current_execution_lane') or {}).get('id') or 'yangdo_explainer_refinement'),
                'question_stack': _question_stack(
                    '추천 결과가 가격 계산을 넘어서 실제 시장 판단으로 이어지는가.',
                    'detail_explainable lane이 consult_assist와 충분히 구분되는가.',
                    '특수 업종 분할/합병 규칙이 추천과 설명 모두에서 일관되게 드러나는가.',
                ),
                'execution_prompt': _execution_prompt(yangdo),
                'next_move': '시장 적합도 해석 카피와 detail_explainable 단독 업셀 lane을 더 선명하게 만든다.',
                'service_copy_ready': bool(yangdo_copy_summary.get('service_copy_ready')),
            },
            'permit': {
                'goal': '요약 진단, 상세 체크리스트, 수동 검토 보조를 명확히 분리한다.',
                'current_bottleneck': str((permit.get('current_execution_lane') or {}).get('id') or 'permit_story_refinement'),
                'question_stack': _question_stack(
                    '사용자가 자가진단과 수동 검토 보조를 헷갈리지 않는가.',
                    '기준/증빙/예외 해석이 lane마다 다르게 드러나는가.',
                    '상세 체크리스트 lane이 실제 임대형 상품으로도 설명 가능한가.',
                ),
                'execution_prompt': _execution_prompt(permit),
                'next_move': 'detail_checklist와 manual_review_assist의 CTA와 증빙 문구를 더 분리한다.',
                'service_copy_ready': bool(permit_copy_summary.get('service_copy_ready')),
            },
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    lines = [
        '# System Split First-Principles Packet',
        '',
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- platform_ready: {summary.get('platform_ready')}",
        f"- yangdo_ready: {summary.get('yangdo_ready')}",
        f"- permit_ready: {summary.get('permit_ready')}",
        f"- prompt_count: {summary.get('prompt_count')}",
        '',
    ]
    for key, track in (payload.get('tracks') or {}).items():
        if not isinstance(track, dict):
            continue
        lines.append(f'## {key}')
        lines.append(f"- goal: {track.get('goal')}")
        lines.append(f"- current_bottleneck: {track.get('current_bottleneck')}")
        lines.append('- question_stack:')
        for item in track.get('question_stack') or []:
            lines.append(f'  - {item}')
        lines.append(f"- next_move: {track.get('next_move')}")
        lines.append('')
    return '\n'.join(lines).strip() + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate separated first-principles prompt packets for platform/yangdo/permit.')
    parser.add_argument('--platform', type=Path, default=DEFAULT_PLATFORM)
    parser.add_argument('--yangdo', type=Path, default=DEFAULT_YANGDO)
    parser.add_argument('--permit', type=Path, default=DEFAULT_PERMIT)
    parser.add_argument('--yangdo-copy', type=Path, default=DEFAULT_YANGDO_COPY)
    parser.add_argument('--permit-copy', type=Path, default=DEFAULT_PERMIT_COPY)
    parser.add_argument('--json', type=Path, default=DEFAULT_JSON)
    parser.add_argument('--md', type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    payload = build_packet(
        platform_path=args.platform,
        yangdo_path=args.yangdo,
        permit_path=args.permit,
        yangdo_copy_path=args.yangdo_copy,
        permit_copy_path=args.permit_copy,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    args.md.write_text(_to_markdown(payload), encoding='utf-8')
    print(json.dumps({'ok': True, 'json': str(args.json), 'md': str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
