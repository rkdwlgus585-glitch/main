#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_widget_snippet import build_launcher_snippet


def build_snippet(target_url: str, title: str) -> str:
    return build_launcher_snippet(
        widget_url=target_url,
        brand_name="서울건설정보",
        brand_label="서울건설정보 · SEOUL CONSTRUCTION INFO",
        title=title,
        subtitle="건설업 면허 양도 가격 범위를 빠르게 확인",
        cta_label="양도가 계산기 열기",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate embeddable SeoulMNA widget snippet')
    parser.add_argument('--target-url', default='https://seoulmna.kr/yangdo-ai-customer/')
    parser.add_argument('--title', default='AI 양도가 산정 계산기')
    parser.add_argument('--output', default='output/widget/seoulmna_yangdo_widget_snippet.html')
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_snippet(args.target_url, args.title), encoding='utf-8')
    print(f'[saved] {out.resolve()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
